"""Canonical/map/ingestion contracts; synthetic fixtures, no field accuracy evidence."""
import base64
import copy
import os
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from ml.operational.contracts import observation,prediction,schemas,canonical_bytes
from ml.operational.map_data import fixture,build
from ml.operational.map_view import write_html
from ml.operational.ingestion import Ingestor,sign,strict_json
from ml.operational.rules import resolution_allowed,evaluate,compare_legacy,catalog
from ml.operational import drivers


class Terrain:
    def sample(self,lat,lon):return 600.,{'source':'SYNTHETIC_TERRAIN','status':'fixture','ground_elevation_m':598.}


class ContractAndMapTests(unittest.TestCase):
    def test_units_raw_values_and_auth_is_derived(self):
        r=fixture()['observations'][2];r['value']=100000.;r['unit']='Pa';r['authenticated']=True
        o=observation(r);self.assertEqual(o['value'],1000.);self.assertEqual(o['raw_value'],100000.);self.assertFalse(o['authenticated'])
        r['value']=150000.;o=observation(r);self.assertIsNone(o['value']);self.assertEqual(o['raw_value'],150000.);self.assertEqual(o['quality_flag'],'rejected_out_of_range')
        r['pressure_reference']='sea_level';self.assertEqual(observation(r)['quality_flag'],'rejected_pressure_reference')
        r=fixture()['observations'][0];r['value']=float('inf');self.assertEqual(observation(r)['raw_value'],'inf')
        r['latitude']=91
        with self.assertRaises(ValueError):observation(r)

    def test_canonical_schema_and_null_uncertainty(self):
        import jsonschema
        o=observation(fixture()['observations'][0]);jsonschema.validate(o,schemas()['observation'])
        p=prediction('x','temperature_c',o['timestamp_utc'],20.,'physics',[],'fallback');jsonschema.validate(p,schemas()['prediction'])
        self.assertIsNone(p['lower']);self.assertFalse(p['uncertainty_available'])
        with self.assertRaises(ValueError):prediction('x','temperature_c',o['timestamp_utc'],20.,'m',[],'x',[21,22],'90')

    def test_two_node_corridor_channel_masks_and_bounds(self):
        payload=fixture();data=build(payload,Terrain(),grid_shape=(5,9))
        self.assertEqual(len(data['cells']),45)
        self.assertTrue(any(c['channels']['temperature_c']['estimate'] is not None for c in data['cells']))
        self.assertTrue(any(c['channels']['temperature_c']['estimate'] is None for c in data['cells']))
        self.assertTrue(all(not p['uncertainty_available'] for c in data['cells'] for p in c['channels'].values()))
        payload['observations']=[r for r in payload['observations'] if r['channel']!='pm25_ug_m3']
        data=build(payload,Terrain(),grid_shape=(3,5))
        self.assertTrue(all(c['channels']['pm25_ug_m3']['estimate'] is None for c in data['cells']))
        self.assertEqual(data['disaster_outputs'],'DISABLED')

    def test_three_node_hull_and_unsupported_cells(self):
        d=build(fixture(3),Terrain(),grid_shape=(7,7))
        self.assertTrue(any(c['geometry_supported'] for c in d['cells']))
        self.assertTrue(any(not c['geometry_supported'] for c in d['cells']))
        self.assertTrue(all(c['channels']['temperature_c']['estimate'] is None for c in d['cells'] if not c['geometry_supported']))

    def test_stale_unauthenticated_and_future_status(self):
        p=fixture();p['mode']='recorded'
        for r in p['observations']:r['authenticated']=True
        d=build(p,Terrain(),grid_shape=(3,3));self.assertTrue(all(n['health']=='degraded' for n in d['nodes']))
        self.assertTrue(all(c['channels']['temperature_c']['estimate'] is None for c in d['cells']))
        p['reference_time_utc']='2026-10-06T02:00:00Z';d=build(p,Terrain(),grid_shape=(3,3))
        self.assertEqual(d['nodes'][0]['channels']['temperature_c']['status'],'stale')
        p['mode']='live_verified'
        with self.assertRaises(ValueError):build(p,Terrain(),grid_shape=(3,3))

    def test_html_escape_and_channel_specific_legend(self):
        d=build(fixture(),Terrain(),grid_shape=(3,3));d['nodes'][0]['node_id']='</script><img onerror=alert(1)>'
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'index.html';write_html(d,p);s=p.read_text()
            self.assertNotIn('</script><img',s);self.assertIn('\\u003c/script',s)
            self.assertIn('No uncertainty available',s);self.assertIn('Station pressure',s);self.assertIn('µg/m³',s)


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.key=os.urandom(32);self.store=Ingestor(Path(self.tmp.name)/'data.sqlite',{'A':self.key})
        self.records=[r for r in fixture()['observations'] if r['node_id']=='A'];self.clock='2026-10-06T00:00:01Z'
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def packet(self,nonce='abcdefghijklmnop',rows=None):return sign('A',self.key,nonce,self.clock,rows or self.records)
    def test_verified_records_idempotent_retry_and_stale_health(self):
        wire=canonical_bytes(self.packet());result=self.store.ingest(wire,self.clock)
        self.assertTrue(result['accepted']);self.assertEqual(result['health'],'healthy')
        self.assertTrue(all(r['authenticated'] for r in self.store.latest()))
        self.assertEqual(self.store.ingest(wire,self.clock)['status'],'DUPLICATE_RETRY')
        self.assertEqual(len(self.store.latest()),6)
        self.assertEqual(self.store.health('2026-10-06T01:00:00Z')[0]['status'],'stale')
    def test_tampering_does_not_change_trusted_node_health(self):
        wire=canonical_bytes(self.packet());self.store.ingest(wire,self.clock)
        p=self.packet('another_nonce_xyz');p['signature_hex']='0'*64
        self.assertFalse(self.store.ingest(canonical_bytes(p),self.clock)['accepted'])
        self.assertEqual(self.store.health(self.clock)[0]['status'],'healthy')
        p=self.packet('third_nonce_123456');p['payload_base64']=base64.b64encode(b'{"bad":1}').decode()
        self.assertFalse(self.store.ingest(canonical_bytes(p),self.clock)['accepted'])
    def test_spoofed_identity_clock_schema_and_missing_core(self):
        rows=copy.deepcopy(self.records);rows[0]['node_id']='B'
        self.assertFalse(self.store.ingest(canonical_bytes(self.packet(rows=rows)),self.clock)['accepted'])
        p=sign('A',self.key,'next_nonce_123456','2026-10-07T00:00:00Z',self.records)
        self.assertFalse(self.store.ingest(canonical_bytes(p),self.clock)['accepted'])
        rows=copy.deepcopy(self.records);rows[5]['value']=None
        p=self.packet('missing_wind_123456',rows);result=self.store.ingest(canonical_bytes(p),self.clock)
        self.assertEqual(result['health'],'degraded')
        self.assertIsNone(self.store.latest()[-1]['value'])
    def test_malformed_and_older_timestamp(self):
        for wire in [b'{}',b'[]',b'{bad',b'{"x":NaN}',b'{}'*65000]:
            self.assertFalse(self.store.ingest(wire,self.clock)['accepted'])
        malformed=sign('A',self.key,'malformed_record_123',self.clock,[42])
        self.assertFalse(self.store.ingest(canonical_bytes(malformed),self.clock)['accepted'])
        invalid_base64=self.packet('invalid_base64_123')
        invalid_base64['payload_base64']='!'
        self.assertFalse(self.store.ingest(canonical_bytes(invalid_base64),self.clock)['accepted'])
        with self.assertRaises(ValueError):strict_json(b'{"x":1,"x":2}')
        self.store.ingest(canonical_bytes(self.packet()),self.clock)
        self.assertFalse(self.store.ingest(canonical_bytes(self.packet('new_nonce_123456789')),self.clock)['accepted'])


def history(cadence=3600):
    base=fixture()['observations'][:6];out=[]
    for i in range(21600//cadence+1):
        for r in base:
            new=dict(r);new['timestamp_utc']=(pd.Timestamp('2026-10-06T00:00:00Z')+pd.Timedelta(seconds=i*cadence)).isoformat()
            new['sample_interval_seconds']=cadence
            if r['channel']=='relative_humidity_pct':new['value']=90.
            if r['channel']=='pressure_hpa':new['value']=1000-i*(2/(21600//cadence))
            if r['channel'] in ['pm25_ug_m3','pm10_ug_m3']:new['value']=100-i
            out.append(new)
    return out


class RuleTests(unittest.TestCase):
    def test_resolution_gate_is_not_reversed(self):
        self.assertFalse(resolution_allowed(3600,900));self.assertTrue(resolution_allowed(60,900));self.assertFalse(resolution_allowed(600,900))
        r={r['event_id']:r for r in evaluate(history())}
        self.assertEqual(r['severe_rainstorm_squall']['status'],'insufficient_temporal_resolution')
        self.assertEqual(r['radiation_fog']['status'],'underspecified_rule')
        self.assertTrue(r['light_moderate_rain']['rule_output'])
        self.assertTrue(all(not r['training_label_admissible'] for r in r.values()))
        self.assertEqual(len(catalog()['rules']),12)
    def test_gaps_masks_causality_and_required_channels_only(self):
        rows=history();end='2026-10-06T06:00:00Z'
        before=evaluate(rows,issue_time_utc=end)
        future=copy.deepcopy(rows[-6:])
        for r in future:r['timestamp_utc']='2026-10-06T07:00:00Z';r['value']=999
        self.assertEqual(before,evaluate(rows+future,issue_time_utc=end))
        missing=[r for r in rows if not (r['channel']=='pressure_hpa' and r['timestamp_utc']=='2026-10-06T03:00:00+00:00')]
        result={r['event_id']:r for r in evaluate(missing)}
        self.assertIsNone(result['light_moderate_rain']['rule_output'])
        self.assertIsNotNone(result['wildfire_evaporative_risk']['rule_output'])
    def test_heat_duration_and_legacy_boundary_difference(self):
        rows=history()
        for r in rows:
            if r['channel']=='temperature_c':r['value']=35.
            if r['channel']=='relative_humidity_pct':r['value']=60.
        result={r['event_id']:r for r in compare_legacy(rows,{'terrain_class':'plains'})}
        self.assertTrue(result['extreme_heatwave']['legacy_output']);self.assertFalse(result['extreme_heatwave']['rule_output'])
        self.assertTrue(result['extreme_heatwave']['disagree'])


class DriverTests(unittest.TestCase):
    def test_pms_checksum_and_atmospheric_fields(self):
        frame=bytearray(32);frame[:4]=b'BM\x00\x1c';frame[6:8]=(900).to_bytes(2,'big');frame[12:14]=(25).to_bytes(2,'big');frame[14:16]=(40).to_bytes(2,'big');frame[30:]=sum(frame[:30]).to_bytes(2,'big')
        values=drivers.pms7003(bytes(frame));self.assertEqual(values['pm25_ug_m3'],25)
        frame[7]^=1
        with self.assertRaises(ValueError):drivers.pms7003(bytes(frame))
    def test_encoder_rollover_and_no_invented_wind(self):
        r=drivers.encoder(2**32-5,5,1);self.assertEqual(r['pulse_count'],10);self.assertIsNone(r['wind_speed_mps']);self.assertIsNone(r['wind_direction_deg'])
        self.assertEqual(drivers.encoder(0,600,1,wind_calibration=(3.,0.))['wind_speed_mps'],3.)
    def test_rtc_requires_explicit_utc_and_not_stopped(self):
        registers=bytes([0x00,0x30,0x12,0x02,0x06,0x10,0x26])
        self.assertIsNone(drivers.ds3231(registers)['timestamp_utc']);self.assertIsNone(drivers.ds3231(registers,True,True)['timestamp_utc'])
        self.assertIn('2026-10-06T12:30',drivers.ds3231(registers,False,True)['timestamp_utc'])
    def test_gps_fix_checksum_and_altitude_datum(self):
        body='GNRMC,120000.00,A,3142.0000,N,07654.0000,E,0.0,0.0,061026,,,A';v=0
        for c in body:v^=ord(c)
        r=drivers.nmea('$'+body+'*'+f'{v:02X}');self.assertAlmostEqual(r['latitude'],31.7);self.assertIsNone(r['elevation_m'])
        with self.assertRaises(ValueError):drivers.nmea('$'+body+'*00')
    def test_backend_retry_and_power_are_not_weather_proof(self):
        state={'calls':0}
        def reader():
            state['calls']+=1
            if state['calls']<2:raise TimeoutError()
            return {'temperature_c':20}
        r=drivers.RetryDriver(reader).poll('2026-10-06T00:00:00Z');self.assertEqual(r['attempts'],2)
        power=drivers.ina219({'bus_voltage_v':5,'current_ma':100,'power_mw':500});self.assertFalse(power['physical_meter_validation'])

class PairedDiagnosticsTests(unittest.TestCase):
    def test_pairing_test_only_and_uncalibrated_interval_label(self):
        from ml.operational.benchmark import paired
        import pandas as pd
        s=pd.DataFrame(dict(physical_site_id=['a','a','b'],valid_time_utc=['2024-12-01T00:00:00Z','2024-12-01T01:00:00Z','2024-12-01T02:00:00Z'],
                            channel='temperature_c',split=['train','test','test'],truth=[20.,20.,20.],prediction=[20.,22.,24.],unit='degC',country='IN',
                            elevation_m=[200.,1000.,2000.],wind_speed_mps=[1.,6.,11.],lower=[19.,21.,23.],upper=[21.,23.,25.]))
        sb=s.copy();sb.prediction=[20.,21.,23.]
        metadata={'dataset_sha256':'a'*64,'split_manifest_sha256':'b'*64,'forecast_horizon_seconds':21600,'nominal_interval_level':.9}
        report=paired(s,sb,metadata)
        self.assertEqual(report['paired_rows'],2);self.assertEqual(report['channels']['temperature_c']['S']['mae'],3.)
        self.assertEqual(report['channels']['temperature_c']['S']['intervals']['status'],'POORLY_CALIBRATED')
        self.assertEqual(s.valid_time_utc.iloc[0],'2024-12-01T00:00:00Z')
        sb.loc[1,'truth']=99
        with self.assertRaises(AssertionError):paired(s,sb,metadata)
    def test_client_retry_is_bounded_and_https_required(self):
        from ml.operational.client import send
        import urllib.error
        calls=[];sleeps=[]
        def failed(req,timeout):calls.append(req.data);raise urllib.error.URLError('fixture failure')
        result=send('http://127.0.0.1:8767/ingest','A',os.urandom(32),fixture()['observations'][:6],opener=failed,sleeper=sleeps.append)
        self.assertEqual(result['attempts'],3);self.assertEqual(len(sleeps),2);self.assertEqual(calls[0],calls[2])
        with self.assertRaises(ValueError):send('http://example.com/ingest','A',os.urandom(32),[])

class MoreProtocolAndHistoryTests(unittest.TestCase):
    def test_exact_mcu_z_header_and_changed_nonce_payload(self):
        import hashlib,hmac
        from ml.operational.ingestion import Ingestor
        key=os.urandom(32);rows=fixture()['observations'][:6];stamp='2026-10-06T00:00:00Z';nonce='mcu_nonce_123456789'
        raw=canonical_bytes({'schema_version':'indra_weather_records_v1','observations':rows})
        packet={'protocol':'indra_hmac_v1','node_id':'A','nonce':nonce,'sent_at_utc':stamp,'payload_base64':base64.b64encode(raw).decode(),
                'signature_hex':hmac.new(key,('A\n'+nonce+'\n'+stamp+'\n').encode()+raw,hashlib.sha256).hexdigest()}
        with tempfile.TemporaryDirectory() as tmp:
            store=Ingestor(Path(tmp)/'x.sqlite',{'A':key})
            self.assertTrue(store.ingest(canonical_bytes(packet),'2026-10-06T00:00:01Z')['accepted'])
            altered=copy.deepcopy(rows);altered[0]['value']=44
            changed=sign('A',key,nonce,stamp,altered)
            self.assertFalse(store.ingest(canonical_bytes(changed),'2026-10-06T00:00:01Z')['accepted'])
            store.close()
    def test_delayed_rules_and_undefined_inversion_baseline(self):
        rows=history()
        for r in rows:
            if r['channel']=='pressure_hpa' and r['timestamp_utc']=='2026-10-06T03:00:00+00:00':r['available_at_utc']='2026-10-06T07:00:00Z'
        result={r['event_id']:r for r in evaluate(rows,{'pressure_baseline_hpa':990.},issue_time_utc='2026-10-06T06:00:00Z')}
        self.assertIsNone(result['light_moderate_rain']['rule_output'])
        self.assertEqual(result['smog_inversion_trap']['status'],'baseline_availability_unverified')
    def test_archive_model_not_applied_to_instant_minute_readings(self):
        from unittest.mock import patch
        class Model:neighbor_count=2
        p=fixture()
        for r in p['observations']:r['sample_interval_seconds']=60
        with patch('ml.operational.map_data.load',return_value=(Model(),None)):
            d=build(p,Terrain(),model_path=__file__,grid_shape=(3,3))
        self.assertEqual(d['model_status'],'archive_model_aggregation_mismatch_physics_fallback')
        self.assertEqual(d['model_version'],'physics_elevation_v1')

class HiddenPointAndMissingNodeTests(unittest.TestCase):
    def test_hidden_sensor_values_do_not_enter_map(self):
        p=fixture();p['roles']['C']='hidden_test';hidden=copy.deepcopy(p['observations'][:6])
        for r in hidden:r['node_id']='C';r['value']=999999
        p['observations'].extend(hidden)
        d=build(p,Terrain(),grid_shape=(3,3))
        self.assertEqual([n['node_id'] for n in d['nodes']],['A','B']);self.assertEqual(d['hidden_test_nodes_excluded'],['C'])
        self.assertTrue(all(all(s['node_id']!='C' for s in q['channels']['temperature_c']['feature_sources']) for q in d['cells']))
    def test_offline_node_registry_is_not_a_fabricated_observation(self):
        p=fixture();old=p['observations'][6];p['observations']=p['observations'][:6]
        p['sites']=[{k:old[k] for k in ['node_id','latitude','longitude','elevation_m']}]
        d=build(p,Terrain(),grid_shape=(3,3))
        missing=next(n for n in d['nodes'] if n['node_id']=='B')
        self.assertIsNone(missing['channels']['temperature_c']['timestamp_utc'])
        self.assertEqual(missing['channels']['temperature_c']['status'],'missing')
        self.assertTrue(all(q['channels']['temperature_c']['estimate'] is None for q in d['cells']))

class AggregationTests(unittest.TestCase):
    def test_complete_hour_is_causal_and_gap_is_not_imputed(self):
        from ml.operational.aggregate import completed_windows
        rows=[]
        for minute in range(60):
            for raw in fixture()['observations'][:6]:
                r=copy.deepcopy(raw);r['timestamp_utc']=(pd.Timestamp('2026-10-06T00:00Z')+pd.Timedelta(minutes=minute)).isoformat();r['sample_interval_seconds']=60
                rows.append(observation(r,True))
        output=completed_windows(rows,as_of='2026-10-06T01:00Z')
        self.assertEqual(len(output),6);self.assertTrue(all(r['value'] is not None for r in output))
        self.assertTrue(all(r['timestamp_utc']=='2026-10-06T01:00:00+00:00' for r in output))
        self.assertEqual(completed_windows(rows,as_of='2026-10-06T00:30Z'),[])
        output=completed_windows(rows[1:],as_of='2026-10-06T01:00Z')
        self.assertIsNone(next(r for r in output if r['channel']=='temperature_c')['value'])
        with self.assertRaises(ValueError):completed_windows(rows,window_seconds=15)

class GovernanceTests(unittest.TestCase):
    def test_unresolved_nwic_cannot_be_exported_by_demo(self):
        p=fixture();p['observations'][0]['source']='nwic_himachal_weather'
        with self.assertRaises(ValueError):build(p,Terrain(),grid_shape=(3,3))

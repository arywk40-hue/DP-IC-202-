"""Synthetic contracts only; no independent hazard accuracy or ERA5 benefit evidence."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from ml.hazard_context.events import normalize,admit,schema
from ml.hazard_context.policy import purge_groups,training_gate
from ml.hazard_context.era5 import verify_requests,join_context,FEATURES
from tests.test_india_sensor import observations

OPTIONAL=all(importlib.util.find_spec(n) for n in ['xarray','geographiclib','shapely','netCDF4'])


def source():
    return dict(source_provider='fixture_gauges',source_dataset='synthetic_source',country='IN',targets=['cloudburst','extreme_rainfall'],
                status='admitted_for_training',independent_observed=True,rights_status='approved_open',provider_license='SYNTHETIC_TEST_ONLY',
                rights_evidence_uri='fixture://generated',reviewed_by='unit-test',event_identity_reviewed=True,evidence='SYNTHETIC_CONTRACT_ONLY')


def event(id='one',time='2024-07-10T00:00:00Z',latitude=31.):
    r=normalize(dict(event_group_id='fixture_'+id,source_provider='fixture_gauges',source_dataset='synthetic_source',source_record_id=id,
                     event_type='cloudburst',event_start_utc=time,event_end_utc=(pd.Timestamp(time)+pd.Timedelta(hours=1)).isoformat(),
                     country='IN',latitude=latitude,longitude=77.,spatial_uncertainty_km=.1,temporal_uncertainty_hours=.1,
                     measurement_value=120.,measurement_unit='mm/h',threshold_definition='fixture local hourly rain ≥100mm/h',
                     quality_flag='verified',label_provenance='SYNTHETIC_CONTRACT_ONLY',evidence_kind='observed_gauge',
                     provider_license='SYNTHETIC_TEST_ONLY',provider_rights_status='approved_open',source_version='fixture_v1',
                     retrieved_at='2026-10-06T00:00:00Z',source_hash='a'*64,cloudburst_evidence_verified=True))
    return admit(r,source(),allow_fixture=True)


def monitor():
    return dict(source_provider='fixture_gauges',source_version='fixture_v1',provider_license='SYNTHETIC_TEST_ONLY',rights_evidence_uri='fixture://generated',reviewed_by='unit-test',retrieved_at='2026-10-06T00:00:00Z',monitoring_admission_status='admitted_for_training',spatial_coverage_radius_km=20.,monitoring_id='m',physical_site_id='site_a',event_type='cloudburst',source_dataset='synthetic_source',
                country='IN',independent_observed=True,complete_coverage_verified=True,negative_category='monitored_no_event',
                rights_status='approved_open',definition='Synthetic complete fixture monitoring',source_hash='a'*64,
                start_utc='2024-07-01T00:00:00Z',end_utc='2024-08-01T00:00:00Z')


class EventContractTests(unittest.TestCase):
    def test_snowstorm_requires_independent_confirmation(self):
        r={**event(), 'event_type':'snowstorm', 'cloudburst_evidence_verified':None}
        s={**source(), 'targets':['snowstorm']}
        blocked=admit(r,s,allow_fixture=True)
        self.assertIn('SNOWSTORM_CONFIRMED_OCCURRENCE_REQUIRED',blocked['admission_reasons'])
        confirmed=admit({**r,'evidence_kind':'confirmed_occurrence',
                        'measurement_value':None,'measurement_unit':None,
                        'threshold_definition':'Synthetic independently confirmed snowstorm fixture'},
                       s,allow_fixture=True)
        self.assertEqual(confirmed['admission_status'],'admitted_for_training')
        # The unit-only override must never admit synthetic evidence in normal use.
        self.assertNotEqual(admit(confirmed,s)['admission_status'],'admitted_for_training')
        self.assertFalse(training_gate([],pd.DataFrame(),'snowstorm')['can_fit_research'])

    def test_unknowns_are_null_and_identity_deterministic(self):
        record=dict(source_provider='IMD',source_dataset='paper',source_record_id='row1',country='IN',event_type='cloudburst')
        a,b=normalize(record),normalize(record)
        self.assertEqual(a['event_id'],b['event_id']);self.assertIsNone(a['latitude']);self.assertIsNone(a['event_start_utc'])
        self.assertEqual(set(a),set(schema()['required']))
        self.assertEqual(normalize({**record,'admission_status':'admitted_for_training'})['admission_status'],'candidate')

    def test_bad_event_schema_and_time(self):
        r=event()
        for change in [dict(country='CN'),dict(latitude=91),dict(event_start_utc='2024-07-10'),dict(source_hash='bad'),dict(confidence=float('nan')),dict(cloudburst_evidence_verified=1),dict(undocumented=2),dict(state=['bad']),dict(event_type=['cloudburst'])]:
            with self.assertRaises(ValueError):normalize({**r,**change})

    def test_independence_rights_and_cloudburst_gate(self):
        self.assertEqual(event()['admission_status'],'admitted_for_training')
        self.assertIn('SYNTHETIC_NOT_INDEPENDENT',admit(event(),source())['admission_reasons'])
        for change in [dict(evidence_kind='satellite_precipitation'),dict(measurement_value=99),dict(cloudburst_evidence_verified=False)]:
            self.assertNotEqual(admit({**event(),**change},source(),allow_fixture=True)['admission_status'],'admitted_for_training')
        r=admit(event(),{**source(),'independent_observed':False});self.assertIn('LABELS_NOT_INDEPENDENT',r['admission_reasons'])
        s={**source(),'rights_status':'approved_restricted'};r={**event(),'provider_rights_status':'approved_restricted'}
        self.assertNotEqual(admit(r,s)['admission_status'],'admitted_for_training')
        self.assertEqual(admit(r,s,True,allow_fixture=True)['admission_status'],'admitted_for_training')
        r=admit(event(),{**source(),'status':'candidate'});self.assertEqual(r['admission_status'],'candidate')

    def test_whole_event_split_and_temporal_buffers(self):
        f=pd.DataFrame({'event_group_id':['same','same','other','background'],
                        'timestamp_utc':pd.to_datetime(['2024-07-01','2024-07-03','2024-07-04','2024-08-01'],utc=True)})
        masks={'train':np.array([1,0,0,0],bool),'validation':np.array([0,1,1,0],bool),'test':np.array([0,0,0,1],bool)}
        clean,report=purge_groups(f,masks)
        self.assertFalse(any(v[:2].any() for v in clean.values()));self.assertIn('same',report['dropped_groups'])
        with self.assertRaises(ValueError):purge_groups(f,{**masks,'test':np.ones(4,bool)})

    def test_unknowns_cannot_enable_hazard_head(self):
        empty=pd.DataFrame()
        r=training_gate([],empty,'cloudburst')
        self.assertFalse(r['can_fit_research']);self.assertEqual(r['cloudburst_detected'],'unavailable')
        self.assertEqual(r['disaster_outputs'],'DISABLED')

    def test_invalid_rows_quarantine_and_protected_outputs(self):
        from ml.hazard_context.events import read_events
        from ml.hazard_context.output import fresh_directory
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'events.jsonl';p.write_text(json.dumps(event())+'\n{bad json\n')
            bad=[];rows=read_events(p,quarantine=bad)
            self.assertEqual(len(rows),1);self.assertEqual(len(bad),1);self.assertEqual(bad[0]['line'],2)
            with self.assertRaises(ValueError):fresh_directory(tmp)
        with self.assertRaises(ValueError):fresh_directory('reports/offline_phase/new-models')

    def test_requests_exact_calendar(self):
        r=verify_requests();self.assertEqual(r['requests'],24)
        original=json.loads(Path('data/registry/cds_physics_requests.json').read_text())
        original['requests'][13]['request']['day'].remove('29')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'r.json';p.write_text(json.dumps(original))
            with self.assertRaises(ValueError):verify_requests(p)

    def test_causal_and_missing_background(self):
        obs=observations(3)
        b=pd.DataFrame({'physical_site_id':'site_a','timestamp_utc':obs.timestamp_utc,'era5_available_at_utc':None,
                        **{c:1. for c in FEATURES}})
        joined=join_context(obs,b)
        self.assertTrue(joined[FEATURES].iloc[0].isna().all())
        self.assertEqual(joined.era5_temperature_c.iloc[1],1.)
        b['era5_available_at_utc']=b.timestamp_utc+pd.Timedelta(hours=2)
        self.assertTrue(join_context(obs,b,'availability_verified_context')[FEATURES].isna().all().all())
        b['era5_available_at_utc']=b.timestamp_utc+pd.Timedelta(minutes=30)
        self.assertEqual(join_context(obs,b,'availability_verified_context').era5_temperature_c.iloc[1],1.)
        b['era5_available_at_utc']=b.timestamp_utc-pd.Timedelta(minutes=1)
        with self.assertRaises(ValueError):join_context(obs,b,'availability_verified_context')
        with self.assertRaises(ValueError):join_context(obs.assign(era5_x=1),b)


@unittest.skipUnless(OPTIONAL,'Install requirements-hazard-context.txt for all context contracts')
class GeospatialAndNetCDFTests(unittest.TestCase):
    def sites(self):return pd.DataFrame([dict(location_id='a',physical_site_id='site_a',latitude=31.,longitude=77.,elevation_m=1200.)])

    def test_geodesy_regions_dedup_and_grouping(self):
        from ml.hazard_context.matching import distance,geodesic_km,deduplicate,group_events
        self.assertAlmostEqual(geodesic_km(0,0,0,1),111.319490793,places=6)
        self.assertEqual(len(deduplicate([event(),event()])),1)
        with self.assertRaises(ValueError):deduplicate([event(),{**event(),'measurement_value':130}])
        a=event();b=event('two','2024-07-10T03:00:00Z',31.01)
        grouped=group_events([b,a]);self.assertEqual(grouped[0]['event_group_id'],grouped[1]['event_group_id'])
        self.assertEqual(grouped,group_events([a,b]))
        self.assertEqual(group_events([grouped[0]])[0]['event_group_id'],grouped[0]['event_group_id'])
        shared={**b,'event_id':a['event_id'],'event_group_id':a['event_id']}
        together=group_events([{**a,'event_group_id':a['event_id']},shared])
        self.assertEqual(together[0]['event_group_id'],together[1]['event_group_id'])
        self.assertTrue(all(r['reported_event_id']==a['event_id'] for r in together))
        polygon={**a,'geometry_type':'Polygon','geometry':{'type':'Polygon','coordinates':[[[76.9,30.9],[77.1,30.9],[77.1,31.1],[76.9,31.1],[76.9,30.9]]]}}
        self.assertEqual(distance(polygon,31,77),0);self.assertGreater(distance(polygon,31,77.2),9)
        with self.assertRaises(ValueError):normalize({**a,'geometry_type':'Point','geometry':{'type':'Point','coordinates':[88,33]}})

    def test_monitoring_negatives_exclusion_and_unknowns(self):
        from ml.hazard_context.matching import match
        f=observations(3);f.timestamp_utc=pd.to_datetime(['2024-07-05T01:00Z','2024-07-10T01:00Z','2024-07-11T01:00Z'])
        result=match([event()],self.sites(),f,[monitor()])
        self.assertEqual(result.label.iloc[0],0.);self.assertEqual(result.label.iloc[1],1.);self.assertTrue(pd.isna(result.label.iloc[2]))
        self.assertTrue(pd.isna(match([event()],self.sites(),f).label.iloc[0]))
        unknown={**event(),'event_start_utc':None,'event_end_utc':None,'admission_status':'candidate'}
        self.assertTrue(match([unknown],self.sites(),f,[monitor()]).label.isna().all())
        with self.assertRaises(ValueError):match([event()],self.sites(),f,[{**monitor(),'complete_coverage_verified':False}])
        m={**monitor(),'rights_status':'approved_restricted'}
        self.assertTrue(pd.isna(match([],self.sites(),f,[m]).label.iloc[0]))
        self.assertEqual(match([],self.sites(),f,[m],restricted=True).label.iloc[0],0.)

    def dataset(self):
        import xarray as xr
        times=pd.date_range('2024-01-01',periods=4,freq='h').to_numpy()
        v={'t2m':300.,'d2m':290.,'sp':90000.,'u10':3.,'v10':4.}
        return xr.Dataset({k:(('valid_time','latitude','longitude'),np.full((4,2,2),value),{'units':'K' if k in ['t2m','d2m'] else 'Pa' if k=='sp' else 'm s**-1'}) for k,value in v.items()},coords={'valid_time':times,'latitude':[32.,30.],'longitude':[76.,78.]})

    def metadata(self):return dict(provider='ECMWF/Copernicus',dataset='era5_land',country='IN',version='fixture',retrieved_at='2026-10-06T00:00:00Z',license='SYNTHETIC_TEST_ONLY',rights_status='approved_open',rights_evidence_uri='fixture://generated',evidence='SYNTHETIC_CONTRACT_ONLY')

    def test_netcdf_units_orientation_hashes_and_nan(self):
        from ml.hazard_context.era5 import normalize_files
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'f.nc';self.dataset().to_netcdf(p,engine='netcdf4')
            f,m=normalize_files([p],self.sites(),self.metadata(),Path(tmp)/'normalized.parquet')
            self.assertAlmostEqual(f.era5_temperature_c.iloc[0],26.85)
            self.assertAlmostEqual(f.era5_surface_pressure_hpa.iloc[0],900.)
            self.assertEqual(f.era5_wind_speed_mps.iloc[0],5.)
            self.assertEqual(len(m['normalized_sha256']),64);self.assertFalse(m['used_for_labels'])
            ds=self.dataset();ds['sp'].attrs['units']='hPa';ds.to_netcdf(p)
            with self.assertRaises(ValueError):normalize_files([p],self.sites(),self.metadata())
            ds=self.dataset();ds['t2m'].values[0,0,0]=np.nan;ds.to_netcdf(p)
            f,_=normalize_files([p],self.sites(),self.metadata());self.assertTrue(np.isnan(f.era5_temperature_c.iloc[0]))
            outside=self.sites().assign(latitude=45.)
            f,_=normalize_files([p],outside,self.metadata());self.assertTrue(f[FEATURES].isna().all().all())

    def test_partial_variable_files_and_duplicates(self):
        from ml.hazard_context.era5 import normalize_files,coordinate_contract
        ds=self.dataset()
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/'a.nc',Path(tmp)/'b.nc'
            ds[['t2m','d2m','sp']].to_netcdf(a);ds[['u10','v10']].to_netcdf(b)
            f,_=normalize_files([a,b],self.sites(),self.metadata());self.assertEqual(len(f),4)
            ds.to_netcdf(a);ds.to_netcdf(b)
            with self.assertRaises(ValueError):normalize_files([a,b],self.sites(),self.metadata())
        with self.assertRaises(ValueError):coordinate_contract(ds.expand_dims(number=[0,1]))
        with self.assertRaises(ValueError):coordinate_contract(ds.assign_coords(longitude=[0.,360.]))

    def test_download_is_explicit_and_preserves_non_netcdf(self):
        from ml.hazard_context.acquire import download
        class Client:
            def retrieve(self,dataset,request,path):Path(path).write_bytes(b'CDF\x01fixture')
        jobs=json.loads(Path('data/registry/cds_physics_requests.json').read_text())['requests'][:1]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):download(Client(),jobs,tmp)
            result=download(Client(),jobs,tmp,True);self.assertEqual(len(result),1)
            with self.assertRaises(ValueError):download(Client(),jobs,tmp,True)
            class BadClient:
                def retrieve(self,dataset,request,path):Path(path).write_bytes(b'PK\x03\x04zip')
            other=Path(tmp)/'zip-response'
            with self.assertRaises(ValueError):download(BadClient(),jobs,other,True)
            self.assertTrue((other/'era5_land_2023_01.nc.part').exists())
            self.assertFalse((other/'era5_land_2023_01.nc').exists())

    def test_episode_metrics_count_events_not_hours(self):
        from ml.hazard_context.episodes import evaluate
        f=pd.DataFrame(dict(physical_site_id=['a']*6,issue_time_utc=pd.date_range('2024-07-10',periods=6,freq='h',tz='UTC'),
                            target_time_utc=pd.date_range('2024-07-10T06:00Z',periods=6,freq='h'),
                            event_group_id=['e','e','e',None,None,None],event_start_utc=['2024-07-10T06:00Z']*3+[None]*3,
                            label=[1,1,1,0,np.nan,0],score=[.8,.9,.9,.1,.8,.8]))
        r=evaluate(f,.5);self.assertEqual(r['positive_event_groups'],1);self.assertEqual(r['detected_event_groups'],1)
        self.assertEqual(r['events'][0]['first_alert_lead_hours'],6.)
        self.assertEqual(r['unknown_alert_episodes'],1);self.assertEqual(r['false_alert_episodes'],0)

    def test_no_unqualified_hazard_training(self):
        from ml.hazard_context.train import run
        from ml.india_sensor.config import load
        with tempfile.TemporaryDirectory() as tmp,patch('ml.hazard_context.train.fit_head') as fit:
            r=run([event()],{'synthetic_source':source()},self.sites(),observations(),[],load(),tmp,['cloudburst'])
            fit.assert_not_called();self.assertFalse(r['targets']['cloudburst']['can_fit_research'])
            self.assertEqual(r['disaster_outputs'],'DISABLED')

    def test_matched_tracks_and_future_perturbation(self):
        from ml.hazard_context.compare import run
        from ml.india_sensor.config import load
        frames=[]
        for i in range(20):
            for start,count in [('2023-04-01',100),('2024-07-05',60),('2024-09-05',60),('2024-11-05',60)]:
                f=observations(count).assign(location_id=str(i),physical_site_id=str(i),latitude=10+i*.7,elevation_m=100.)
                f['timestamp_utc']=pd.date_range(start,periods=count,freq='h',tz='UTC');f['available_at_utc']=f.timestamp_utc
                f['temperature_c']=np.where(np.arange(count)%3==0,40.,20.)
                frames.append(f)
        obs=pd.concat(frames,ignore_index=True)
        b=obs[['physical_site_id','timestamp_utc']].copy();b.timestamp_utc-=pd.Timedelta(hours=1)
        b['era5_available_at_utc']=None
        for c in FEATURES:b[c]=1.
        metadata={**self.metadata(),'raw_file_sha256':{'fixture':'a'*64},'mode':'retrospective_background_context'}
        base=load()
        cfg={**base,'threshold_targets':{'hot_measurement_at_6h':base['threshold_targets']['hot_measurement_at_6h']},'rounds':2,'threads':1,'minimum_per_class':3,'candidate_weights':['unweighted'],'verify_reproducibility':True}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):run(obs,b,cfg,metadata,tmp)
            result=run(obs,b,cfg,metadata,tmp,allow_fixture=True)
            self.assertEqual(result['matched_rows'],len(obs))
            self.assertFalse(any(c.startswith('era5_') for c in result['feature_tracks']['S']))
            self.assertTrue(all(c.startswith('era5_') for c in result['feature_tracks']['SB'] if c not in result['feature_tracks']['S']))
            self.assertEqual(result['disaster_outputs'],'DISABLED')
            for target in result['targets'].values():
                self.assertEqual(target['S']['metrics']['rows'],target['SB']['metrics']['rows'])
        small=observations(4)
        b=small[['physical_site_id','timestamp_utc']].assign(era5_available_at_utc=None)
        for c in FEATURES:b[c]=1.
        before=join_context(small,b)
        b.loc[2:,FEATURES]=999.
        after=join_context(small,b)
        pd.testing.assert_frame_equal(before.iloc[:3],after.iloc[:3])

    def test_episode_buffer_and_cross_station_group(self):
        frame=pd.DataFrame(dict(event_group_id=['one','two','two'],physical_site_id=['a','b','c'],
                                 timestamp_utc=pd.to_datetime(['2024-07-01','2024-07-02','2024-07-02T01:00:00'],format='mixed',utc=True)))
        masks={'train':np.array([1,0,0],bool),'validation':np.array([0,1,1],bool),'test':np.zeros(3,bool)}
        clean,receipt=purge_groups(frame,masks)
        self.assertFalse(clean['validation'].any());self.assertIn('two',receipt['dropped_groups'])

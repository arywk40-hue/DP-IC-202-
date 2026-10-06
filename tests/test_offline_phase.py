"""Offline regression contracts; synthetic fixtures are not accuracy evidence."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from ml.india_sensor.config import load
from ml.india_sensor.features import build
from ml.india_sensor.pm import eligibility
from ml.india_sensor.preprocess_c import expression
from ml.india_sensor.replay import Stream
from ml.india_sensor.splits import row_roles, station_roles
from ml.india_sensor.thresholds import tune
from ml.india_sensor.train import fit_head
from tests.test_india_sensor import observations

POLICY = dict(beta=2., max_false_positive_hours_per_station_day=.25,
              minimum_positive_hours=2, minimum_positive_episodes=2, minimum_positive_sites=2)


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.cfg = load('configs/india_sensor_offline.json')

    def test_configuration_rejects_empty_weights_and_nonfinite_targets(self):
        base=json.loads(Path('configs/india_sensor_offline.json').read_text())
        for alter in [lambda c:c.update(candidate_weights=[]),
                      lambda c:c['threshold_targets']['hot_measurement_at_6h'].update(threshold=float('nan')),
                      lambda c:c['threshold_tuning'].update(beta=float('inf'))]:
            c=json.loads(json.dumps(base));alter(c)
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp)/'config.json';p.write_text(json.dumps(c))
                with self.assertRaises(ValueError):load(p)

    def test_threshold_ties_budget_and_support(self):
        y = np.array([1, 1]+[0]*198)
        scores = np.array([.9, .8]+[.1]*198)
        groups = np.arange(200)
        r = tune(y, scores, groups, groups, POLICY)
        self.assertEqual(r['raw_threshold'], .8)
        self.assertEqual(r['validation_decisions']['recall'], 1.)
        # All tied predictions must be treated together; cannot cherry-pick truth.
        r = tune(y, np.full(200, .8), groups, groups, POLICY)
        self.assertEqual(r['status'], 'NO_FEASIBLE_VALIDATION_CUTOFF')
        r = tune(y, scores, np.zeros(200), groups, POLICY)
        self.assertIsNone(r['raw_threshold'])
        with self.assertRaises(ValueError):
            tune(y, scores*2, groups, groups, POLICY)

    def test_test_labels_do_not_change_weight_or_cutoff(self):
        frame = build(observations(160), self.cfg)
        frame['label'] = (np.arange(160) % 3 == 0).astype(float)
        masks = {k: np.zeros(160, bool) for k in ['train', 'validation', 'calibration', 'test']}
        for k, (a, b) in zip(masks, [(0,80),(80,110),(110,135),(135,160)]):
            masks[k][a:b] = True
        cfg = {**self.cfg, 'rounds': 2, 'minimum_per_class': 3, 'threshold_tuning': POLICY}
        with tempfile.TemporaryDirectory() as tmp:
            _, first = fit_head(frame, 'label', masks, ['temperature_c'], cfg, Path(tmp)/'a.ubj')
            frame.loc[masks['test'], 'label'] = 1-frame.loc[masks['test'], 'label']
            _, second = fit_head(frame, 'label', masks, ['temperature_c'], cfg, Path(tmp)/'b.ubj')
            for k in ['sha256', 'threshold_selection', 'calibration', 'reproducibility']:
                self.assertEqual(first[k], second[k])
            self.assertTrue(first['reproducibility']['identical_model_bytes'])

    def test_pressure_reference_masks_all_reused_history(self):
        f = build(observations().assign(pressure_reference='sea_level'), self.cfg)
        pressure = [c for c in f if c.startswith('pressure_') and c != 'pressure_reference']
        self.assertTrue(f[pressure].isna().all().all())

    def test_replay_arrival_and_causality(self):
        frame = observations(60)
        stream = Stream(self.cfg, inference=False)
        for row in frame.iloc[:40].to_dict('records'):
            self.assertEqual(stream.push(row)['status'], 'ACCEPTED')
        self.assertEqual(stream.push(row)['status'], 'REJECTED_DUPLICATE_OR_OUT_OF_ORDER')
        self.assertEqual(stream.push(frame.iloc[10].to_dict())['status'], 'REJECTED_DUPLICATE_OR_OUT_OF_ORDER')
        bad = frame.iloc[40].to_dict()
        bad['available_at_utc'] += pd.Timedelta(hours=1)
        self.assertEqual(stream.push(bad)['status'], 'LATE_PACKET_OMITTED')
        bad = frame.iloc[40].to_dict(); bad['physical_site_id'] = 'other'
        self.assertEqual(stream.push(bad)['status'], 'REJECTED_SITE_SWITCH')
        self.assertEqual(stream.push({})['status'], 'REJECTED_SCHEMA')
        self.assertLessEqual(len(stream.rows), 26)
        entry = stream.push(frame.iloc[41].to_dict())
        # Independent full arrival prefix, including the omitted hour.
        batch = build(frame.iloc[:42].drop(index=40), self.cfg).iloc[-1]
        for c in ['temperature_c_lag_1h', 'temperature_c_mean_6h', 'pressure_anomaly_prior24h_hpa']:
            self.assertTrue(np.isnan(batch[c]) and np.isnan(entry['features'][c]))
        future = frame.copy(); future.loc[42:, 'temperature_c'] = -30
        pd.testing.assert_frame_equal(build(frame,self.cfg).iloc[:42], build(future,self.cfg).iloc[:42])

    def test_temporal_roles_and_himalaya_uncertainty(self):
        st = pd.DataFrame(dict(location_id=[str(i) for i in range(40)], physical_site_id=[str(i) for i in range(40)],
                               latitude=10+np.arange(40)*.65, longitude=77., elevation_m=100.))
        st.loc[35,'elevation_m'] = np.nan
        roles = station_roles(st,'temporal',self.cfg)
        self.assertEqual(roles['train'],roles['test'])
        roles = station_roles(st,'himalaya_holdout',self.cfg)
        self.assertNotIn('35',roles['train']+roles['validation'])
        f = observations(24)
        f['timestamp_utc'] = pd.date_range('2024-06-30',periods=24,freq='6h',tz='UTC')
        masks = row_roles(f,dict(train=['a'],validation=['a'],test=['a']),self.cfg)
        self.assertTrue((sum(m.astype(int) for m in masks.values())<=1).all())

    def test_pm_clock_and_restricted_gates(self):
        source = dict(timezone_verified=1, interval_semantics='hour_end',license_class='restricted')
        self.assertEqual(eligibility(source),'RESTRICTED_VIEW_REQUIRED')
        self.assertEqual(eligibility(source,True),'ELIGIBLE_RESTRICTED')
        for change in [dict(timezone_verified='false'),dict(interval_semantics=None),dict(interval_semantics='unknown')]:
            self.assertTrue(eligibility({**source,**change},True).startswith('BLOCKED'))
        self.assertEqual(eligibility({**source,'license_class':'unresolved'},True),'BLOCKED_RIGHTS_UNRESOLVED')

    def test_export_rejects_unknown_or_subhour_feature(self):
        for name in ['rainfall_mm', 'pressure_hpa_delta_10min']:
            with self.assertRaises(ValueError):
                expression(name)
        self.assertIn('indra_roll',expression('temperature_c_mean_6h'))
        json.dumps(self.cfg,allow_nan=False)

class PMMaskedTests(unittest.TestCase):
    def test_optional_head_and_country_gate(self):
        from ml.india_sensor.pm import train
        cfg=load('configs/india_sensor_offline.json')
        source=dict(source_id='test_approved_pm',country_code='IN',timezone_verified=1,
                    interval_semantics='hour_end',license_class='restricted')
        frame=[]; stations=[]
        for i in range(20):
            f=observations(120).assign(location_id=str(i),physical_site_id=str(i),
                                       latitude=10+i*.8,elevation_m=100.,source_id=source['source_id'])
            f['pm25_ug_m3']=20+np.arange(120)%20
            frame.append(f)
            stations.append(dict(location_id=str(i),physical_site_id=str(i),latitude=10+i*.8,longitude=77.,elevation_m=100.))
        frame=pd.concat(frame,ignore_index=True)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                train(frame,source,cfg,pd.DataFrame(stations),tmp)
            with self.assertRaises(ValueError):
                train(frame,{**source,'country_code':'CN'},cfg,pd.DataFrame(stations),tmp,True)
            report=train(frame,source,cfg,pd.DataFrame(stations),tmp,True)
            self.assertEqual(report['view'],'restricted')
            self.assertEqual(report['heads']['pm25_ug_m3']['status'],'RESEARCH_ONLY')
            self.assertEqual(report['heads']['pm10_ug_m3']['status'],'UNTRAINED_INSUFFICIENT_LABELS')
            self.assertFalse(report['hardware_validated'])

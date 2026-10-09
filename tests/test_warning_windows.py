"""Synthetic warning contracts only; no real event accuracy is asserted."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from ml.hazard_context.diagnostics import select_warning_threshold
from ml.hazard_context.episodes import evaluate
from ml.hazard_context.warning import complete_sensor_history, load_protocol, mask_incomplete_history, warning_targets
from tests.test_hazard_context import event, monitor, source
from tests.test_india_sensor import observations


def sites():
    return pd.DataFrame([dict(location_id='a',physical_site_id='site_a',latitude=31.,longitude=77.,elevation_m=1200.)])


def readings(times):
    f=observations(len(times)).assign(pm25_ug_m3=20.,pm10_ug_m3=40.)
    f['timestamp_utc']=pd.to_datetime(times,utc=True)
    f['available_at_utc']=f.timestamp_utc
    return f


def onset(time='2024-07-10T18:00:00Z',id='one',uncertainty=0.):
    return {**event(id,time),'event_end_utc':time,'temporal_uncertainty_hours':uncertainty}


class WarningHistoryTests(unittest.TestCase):
    def test_history_requires_every_measured_channel_and_exact_cadence(self):
        f=readings(pd.date_range('2024-07-09',periods=30,freq='h',tz='UTC'))
        ready=complete_sensor_history(f)
        self.assertFalse(ready[:24].any());self.assertTrue(ready[24:].all())
        f.loc[25,'pm10_ug_m3']=np.nan
        self.assertFalse(complete_sensor_history(f)[25:].any())
        # A missing hour cannot be hidden by counting the last 25 observed rows.
        g=readings(['2024-07-09T00:00Z','2024-07-09T01:00Z','2024-07-09T03:00Z','2024-07-09T04:00Z','2024-07-09T05:00Z'])
        self.assertEqual(complete_sensor_history(g,120).tolist(),[False,False,False,False,True])

    def test_delayed_pressure_reference_and_future_changes(self):
        f=readings(pd.date_range('2024-07-09',periods=30,freq='h',tz='UTC'))
        before=complete_sensor_history(f)
        f.loc[27:,'pm25_ug_m3']=np.nan
        np.testing.assert_array_equal(before[:27],complete_sensor_history(f)[:27])
        f.loc[24,'available_at_utc']+=pd.Timedelta(minutes=30)
        self.assertFalse(complete_sensor_history(f)[24:].any())
        f=readings(pd.date_range('2024-07-09',periods=30,freq='h',tz='UTC'))
        f.loc[24,'pressure_reference']='sea_level'
        self.assertFalse(complete_sensor_history(f)[24:].any())

    def test_protocol_rejects_sensor_or_deployment_contract_changes(self):
        p=json.loads(Path('configs/himalayan_warning_v1.json').read_text())
        self.assertEqual(load_protocol()['horizon_hours'],6)
        for change in [dict(sensor_columns=['temperature_c']),dict(deployment_approved=True),dict(horizon_hours=True),dict(targets=['unknown'])]:
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'bad.json';path.write_text(json.dumps({**p,**change}))
                with self.assertRaises(ValueError):load_protocol(path)

    def test_out_of_range_readings_are_not_complete_history(self):
        f=readings(pd.date_range('2024-07-09',periods=30,freq='h',tz='UTC'))
        f.loc[24,'temperature_c']=200
        self.assertFalse(complete_sensor_history(f)[24:].any())


@unittest.skipUnless(importlib.util.find_spec('geographiclib'),'Install pinned geographiclib for geodesic warning contracts')
class WarningWindowTests(unittest.TestCase):
    def test_six_hours_before_onset_positive_but_post_onset_unknown(self):
        f=readings(pd.date_range('2024-07-10T12:00Z',periods=8,freq='h'))
        labels=warning_targets(f,[onset()],sites(),[monitor()],'cloudburst')
        self.assertTrue(labels.label.iloc[:6].eq(1).all())
        self.assertTrue(labels.label.iloc[6:].isna().all())
        self.assertEqual(labels.event_start_utc.iloc[0],'2024-07-10T18:00:00+00:00')

    def test_exact_future_benchmark_remains_different(self):
        from ml.hazard_context.train import targets
        f=readings(pd.date_range('2024-07-10T12:00Z',periods=6,freq='h'))
        m=pd.DataFrame([dict(physical_site_id='site_a',timestamp_utc='2024-07-10T18:00:00Z',event_type='cloudburst',label=1.,event_group_id='one',event_start_utc='2024-07-10T18:00:00Z')])
        exact=targets(f,m,'cloudburst',6)
        self.assertEqual(int(exact.label.eq(1).sum()),1)
        self.assertEqual(int(warning_targets(f,[onset()],sites(),[],'cloudburst').label.eq(1).sum()),6)

    def test_uncertainty_crossing_a_boundary_stays_unknown(self):
        f=readings(['2024-07-10T12:00Z','2024-07-10T13:00Z','2024-07-10T17:00Z'])
        labels=warning_targets(f,[onset(uncertainty=1)],sites(),[monitor()],'cloudburst')
        self.assertTrue(pd.isna(labels.label.iloc[0]))
        self.assertEqual(labels.label.iloc[1],1)
        self.assertTrue(pd.isna(labels.label.iloc[2]))

    def test_negative_requires_full_window_not_only_the_endpoint(self):
        f=readings(['2024-07-10T12:00Z'])
        m={**monitor(),'start_utc':'2024-07-10T17:00:00Z','end_utc':'2024-07-10T18:00:00Z'}
        self.assertTrue(warning_targets(f,[],sites(),[m],'cloudburst').label.isna().all())
        left={**m,'monitoring_id':'left','start_utc':'2024-07-10T12:00:00Z','end_utc':'2024-07-10T15:00:00Z'}
        right={**m,'monitoring_id':'right','start_utc':'2024-07-10T15:00:00Z'}
        labels=warning_targets(f,[],sites(),[left,right],'cloudburst')
        self.assertEqual(labels.label.iloc[0],0)
        self.assertEqual(labels.monitoring_ids.iloc[0],'left|right')
        left['end_utc']='2024-07-10T14:59:59Z'
        self.assertTrue(warning_targets(f,[],sites(),[left,right],'cloudburst').label.isna().all())
        left['end_utc']='2024-07-10T15:00:00Z';right['definition']='different outcome definition'
        self.assertTrue(warning_targets(f,[],sites(),[left,right],'cloudburst').label.isna().all())

    def test_candidates_and_unknown_clock_or_location_block_negatives(self):
        f=readings(['2024-07-10T12:00Z'])
        for change in [dict(admission_status='candidate'),dict(event_start_utc=None,event_end_utc=None),dict(latitude=None,longitude=None)]:
            r={**onset('2024-07-10T15:00:00Z'),**change}
            self.assertTrue(warning_targets(f,[r],sites(),[monitor()],'cloudburst').label.isna().all())

    def test_far_event_does_not_block_but_point_coverage_is_insufficient(self):
        f=readings(['2024-07-10T12:00Z'])
        r={**onset('2024-07-10T15:00:00Z'),'latitude':34.,'spatial_uncertainty_km':0.1}
        self.assertEqual(warning_targets(f,[r],sites(),[monitor()],'cloudburst').label.iloc[0],0)
        self.assertTrue(warning_targets(f,[],sites(),[{**monitor(),'spatial_coverage_radius_km':0.}],'cloudburst').label.isna().all())

    def test_reactivation_group_does_not_supply_post_onset_positives(self):
        f=readings(['2024-07-10T19:00Z'])
        a=onset('2024-07-10T15:00:00Z')
        b={**onset('2024-07-10T20:00:00Z','two'),'event_group_id':a['event_group_id']}
        self.assertTrue(warning_targets(f,[a,b],sites(),[monitor()],'cloudburst').label.isna().all())

    def test_missing_particulates_mask_otherwise_valid_labels(self):
        f=readings(pd.date_range('2024-07-09T12:00Z',periods=30,freq='h'))
        labels=warning_targets(f,[onset()],sites(),[monitor()],'cloudburst')
        masked=mask_incomplete_history(labels,f,1440,3600)
        self.assertTrue(masked.label.iloc[24:30].eq(1).all())
        f['pm25_ug_m3']=np.nan
        self.assertTrue(mask_incomplete_history(labels,f,1440,3600).label.isna().all())

    def test_synthetic_source_cannot_trigger_warning_training(self):
        from ml.hazard_context.train import run
        from ml.india_sensor.config import load
        f=readings(pd.date_range('2024-07-09T12:00Z',periods=30,freq='h'))
        with tempfile.TemporaryDirectory() as tmp,patch('ml.hazard_context.train.fit_head') as fit:
            r=run([onset()],{'synthetic_source':source()},sites(),f,[],load('configs/india_sensor_offline.json'),tmp,['cloudburst'],label_mode='next_h_hours')
            fit.assert_not_called()
            self.assertFalse(r['targets']['cloudburst']['can_fit_research'])
            self.assertEqual(r['label_mode'],'next_h_hours')
            self.assertEqual(r['disaster_outputs'],'DISABLED')


class WarningEpisodeTests(unittest.TestCase):
    def test_negative_only_run_has_no_invented_event_recall(self):
        f=pd.DataFrame(dict(physical_site_id=['a']*2,issue_time_utc=pd.date_range('2024-07-10T12:00Z',periods=2,freq='h'),
                            target_time_utc=pd.date_range('2024-07-10T18:00Z',periods=2,freq='h'),
                            event_group_id=['bg','bg'],event_start_utc=[None,None],label=[0,0],score=[.8,.8]))
        r=evaluate(f,.5,warning_only=True)
        self.assertIsNone(r['event_recall'])
        self.assertEqual(r['false_alert_episodes'],1)
        self.assertAlmostEqual(r['false_alert_episodes_per_100_monitored_site_days'],1200.)

    def test_lead_uncertainty_and_false_alert_episode_rate(self):
        f=pd.DataFrame(dict(physical_site_id=['a']*6,
                            issue_time_utc=pd.date_range('2024-07-10T13:00Z',periods=6,freq='h'),
                            target_time_utc=pd.date_range('2024-07-10T19:00Z',periods=6,freq='h'),
                            event_group_id=['one','one','bg','bg','bg','bg'],
                            event_start_utc=['2024-07-10T18:00Z']*2+[None]*4,
                            event_onset_min_utc=['2024-07-10T17:30Z']*2+[None]*4,
                            event_onset_max_utc=['2024-07-10T18:30Z']*2+[None]*4,
                            label=[1,1,0,0,np.nan,0],score=[.8,.9,.8,.8,.8,.1]))
        r=evaluate(f,.5,warning_only=True)
        self.assertEqual(r['events'][0]['first_alert_lead_min_hours'],4.5)
        self.assertEqual(r['events'][0]['first_alert_lead_max_hours'],5.5)
        self.assertEqual(r['true_alert_episodes'],1)
        self.assertEqual(r['false_alert_episodes'],0)
        self.assertEqual(r['eligible_monitored_negative_site_days'],3/24)
        f.loc[0,'event_start_utc']='2024-07-10T13:00Z'
        with self.assertRaises(ValueError):evaluate(f,.5,warning_only=True)

    def test_threshold_uses_validation_episode_budget_and_support(self):
        p=load_protocol()['alert_selection']
        def row(cutoff,recall,false_rate,days=100):
            return dict(raw_cutoff=cutoff,episodes=dict(positive_event_groups=10,
                        eligible_monitored_negative_site_days=days,
                        false_alert_episodes_per_100_monitored_site_days=false_rate,event_recall=recall))
        curve=[row(.1,1.,20),row(.5,.8,1),row(.8,.6,0)]
        selected=select_warning_threshold(curve,p)
        self.assertEqual(selected['raw_threshold'],.5)
        self.assertFalse(selected['test_retuning'])
        self.assertIsNone(select_warning_threshold([row(.1,1.,20)],p)['raw_threshold'])
        self.assertIsNone(select_warning_threshold([row(.5,1.,0,days=1)],p)['raw_threshold'])

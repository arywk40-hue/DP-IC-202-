"""India/Mandi workflow contracts; synthetic fixtures are not field accuracy evidence."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from ml.india_mandi.benchmark import evaluate
from ml.india_mandi.data import load_config,month_windows,response_frame,WEATHER
from ml.six_sensor_forecast.data import SCHEMA,sha256
from ml.six_sensor_forecast.features import split_masks
from ml.six_sensor_forecast.predict import predict
from ml.six_sensor_forecast.train import train
from ml.tests.test_six_sensor_forecast import fixture


class IndiaMandiTests(unittest.TestCase):
    def test_configuration_cannot_select_china_or_promote_modeled_disasters(self):
        original=json.loads(Path('ml/configs/mandi_modeled_forecast_v1.json').read_text())
        for change in [dict(country_code='CN'),dict(latitude=40.0),dict(deployment_approved=True),dict(hazard_training_allowed=True),dict(evidence_kind='OBSERVED')]:
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'config.json';path.write_text(json.dumps({**original,**change}))
                with self.assertRaises(ValueError):load_config(path)

    def test_monthly_download_boundaries_include_leap_day_without_duplicates(self):
        windows=list(month_windows('2024-01-30','2024-03-02'))
        self.assertEqual([(a.isoformat(),b.isoformat()) for a,b in windows],
                         [('2024-01-30','2024-01-31'),('2024-02-01','2024-02-29'),('2024-03-01','2024-03-02')])

    def test_wrong_wind_units_and_duplicate_api_times_are_rejected(self):
        d={'hourly_units':dict(temperature_2m='°C',relative_humidity_2m='%',surface_pressure='hPa',wind_speed_10m='km/h'),
           'hourly':dict(time=['2024-01-01T00:00'],temperature_2m=[20],relative_humidity_2m=[60],surface_pressure=[900],wind_speed_10m=[3])}
        with self.assertRaises(ValueError):response_frame(d,WEATHER)
        d['hourly_units']['wind_speed_10m']='m/s'
        self.assertEqual(response_frame(d,WEATHER).temperature_c.iloc[0],20)
        d['hourly']={k:v*2 for k,v in d['hourly'].items()}
        with self.assertRaises(ValueError):response_frame(d,WEATHER)

    def test_temporal_only_split_does_not_fabricate_geographic_validation(self):
        frame=fixture().query("location_id == 'a'").reset_index(drop=True)
        masks=split_masks(frame,6,'2025-01-03T00:00Z','2025-01-04T00:00Z',[],temporal_only=True)
        self.assertEqual(set(masks),{'train','validation','future_test'})
        self.assertTrue(((frame.loc[masks['train'],'timestamp_utc']+pd.Timedelta(hours=6))<pd.Timestamp('2025-01-03T00:00Z')).all())
        with self.assertRaises(ValueError):split_masks(frame,6,'2025-01-03T00:00Z','2025-01-04T00:00Z',[],temporal_only=False)
        with self.assertRaises(ValueError):split_masks(frame,6,'2025-01-03T00:00Z','2025-01-04T00:00Z',['a'],temporal_only=True)

    def test_complete_history_training_and_inference_are_explicit(self):
        f=fixture().query("location_id == 'a'").reset_index(drop=True)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);f.to_csv(root/'observations.csv',index=False)
            (root/'dataset_manifest.json').write_text(json.dumps(dict(schema_version=SCHEMA,observations_sha256=sha256(root/'observations.csv'),
                 source_name='Synthetic contract fixture only',country_code='IN',evidence_kind='SYNTHETIC_CONTRACT_ONLY')))
            with contextlib.redirect_stdout(io.StringIO()):
                report=train(root,root/'models',6,'2025-01-03T00:00Z','2025-01-04T00:00Z',[],rounds=3,threads=1,
                             temporal_only=True,require_complete_history=True)
            self.assertEqual(report['split']['geographic_validation'],'NOT_EVALUATED')
            self.assertNotIn('geographic_test',report['models']['temperature_c']['metrics'])
            teacher=predict(f,root/'models','teacher');student=predict(f,root/'models','student')
            self.assertTrue(teacher.status.iloc[:24].eq('INCOMPLETE_HISTORY').all())
            self.assertTrue(teacher.status.iloc[24:].eq('OFFLINE_RESEARCH_ONLY').all())
            self.assertTrue(student.status.eq('OFFLINE_RESEARCH_ONLY').all())

    def test_evaluator_refuses_foreign_weights_before_loading_booster(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'training_report.json').write_text(json.dumps({'model_country':'CN'}))
            with patch('ml.india_mandi.benchmark.arrays',return_value=(None,None,None,None,{})),patch('ml.india_mandi.benchmark.xgb.Booster') as loader:
                with self.assertRaises(ValueError):evaluate({'models':str(root),'data':str(root)})
                loader.assert_not_called()

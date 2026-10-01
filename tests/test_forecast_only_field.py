import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from ml.deployment.evaluate_forecast import evaluate, validate_model
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS


class ForecastOnlyFieldTests(unittest.TestCase):
    def setUp(self):
        self.model_dir = Path(__file__).resolve().parents[1] / "ml/models/uci_beijing_6h"
        def fake_predict(frame, _model_dir, kind):
            self.assertEqual(kind, "student")
            result = frame[["location_id", "timestamp_utc"]].copy()
            result["forecast_timestamp_utc"] = result.timestamp_utc + pd.Timedelta(hours=6)
            result["status"] = "OFFLINE_RESEARCH_ONLY"
            for name in RAW_SENSOR_COLUMNS:
                result["forecast_" + name] = frame[name].to_numpy()
            return result
        self.predict_patch = patch("ml.deployment.evaluate_forecast.predict", side_effect=fake_predict)
        self.hash_patch = patch("ml.deployment.evaluate_forecast.sha256", return_value="test-hash")
        self.predict_mock = self.predict_patch.start()
        self.hash_patch.start()
        self.addCleanup(self.predict_patch.stop)
        self.addCleanup(self.hash_patch.stop)
        self.provenance = {
            "observation_source": "synthetic test fixture",
            "timezone_verified": True,
            "units_verified": True,
            "pressure_reference": "station",
        }
        self.frame = pd.DataFrame(
            np.tile([20.0, 50.0, 1013.0, 35.0, 60.0, 2.0], (13, 1)),
            columns=RAW_SENSOR_COLUMNS,
        )
        self.frame["timestamp_utc"] = pd.date_range(
            "2026-01-01", periods=13, freq="h", tz="UTC"
        )
        self.frame["location_id"] = "synthetic"

    def test_exact_future_pair_without_event_labels(self):
        report = evaluate(
            self.frame, self.provenance, "2026-01-01T06:00:00Z", self.model_dir
        )
        self.assertEqual(report["six_hour_test_pairs"], 1)
        self.assertEqual(report["metrics"]["ALL"]["temperature_c"]["pairs"], 1)
        self.assertFalse(report["field_deployment_approved"])

    def test_incompatible_model_rejected_before_inference(self):
        reduced = self.model_dir.parent / 'india_cpcb_5sensor_6h'
        with self.assertRaisesRegex(ValueError, 'Incompatible forecast model'):
            evaluate(self.frame, self.provenance, '2026-01-01T00:00Z', reduced)
        self.predict_mock.assert_not_called()
        metadata = json.loads((self.model_dir / 'training_report.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            metadata['horizon_hours'] = 12
            (path / 'training_report.json').write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, 'six-hour student'):
                validate_model(path)

    def test_missing_pm_and_unverified_provenance_are_rejected(self):
        frame = self.frame.drop(columns=["pm10_ug_m3"])
        with self.assertRaises(ValueError):
            evaluate(frame, self.provenance, "2026-01-01T06:00:00Z", self.model_dir)
        frame = self.frame.copy()
        frame.loc[0, "pm25_ug_m3"] = np.nan
        with self.assertRaises(ValueError):
            evaluate(frame, self.provenance, "2026-01-01T06:00:00Z", self.model_dir)
        provenance = dict(self.provenance, timezone_verified=False)
        with self.assertRaises(ValueError):
            evaluate(self.frame, provenance, "2026-01-01T06:00:00Z", self.model_dir)

    def test_naive_time_and_nonmatching_future_are_rejected_or_counted(self):
        frame = self.frame.copy()
        frame["timestamp_utc"] = frame.timestamp_utc.dt.tz_localize(None)
        with self.assertRaises(ValueError):
            evaluate(frame, self.provenance, "2026-01-01T06:00:00Z", self.model_dir)
        frame = self.frame.iloc[::7].copy()
        report = evaluate(frame, self.provenance, "2026-01-01T00:00:00Z", self.model_dir)
        self.assertEqual(report["status"], "NO_EXACT_SIX_HOUR_TEST_PAIRS")


if __name__ == "__main__":
    unittest.main()

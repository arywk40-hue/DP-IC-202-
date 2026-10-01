from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS, sensor_profile
from ml.six_sensor_forecast.data import SCHEMA, sha256
from ml.six_sensor_forecast.export import export
from ml.six_sensor_forecast.features import build_features, future_targets
from ml.six_sensor_forecast.predict import predict
from ml.six_sensor_forecast.train import train
from tests.test_six_sensor_forecast import fixture


class SensorProfilesTest(unittest.TestCase):
    def test_ist_hourly_grid_and_future_alignment(self):
        frame = fixture()
        frame["timestamp_utc"] += pd.Timedelta(minutes=30)
        ordered, _ = build_features(frame)
        targets = future_targets(ordered, 6)
        self.assertAlmostEqual(
            targets.loc[0, "temperature_c"], ordered.loc[6, "temperature_c"], places=5
        )
        frame.loc[1, "timestamp_utc"] += pd.Timedelta(minutes=5)
        with self.assertRaisesRegex(ValueError, "hourly grid"):
            build_features(frame)

    def test_rejects_fabricated_duplicate_or_reordered_sensor_profile(self):
        for columns in (
            [],
            ["co2"],
            ["pm25_ug_m3", "pm25_ug_m3"],
            ["pm10_ug_m3", "pm25_ug_m3"],
        ):
            with self.assertRaises(ValueError):
                sensor_profile(columns)

    def test_five_and_two_sensor_models_export_without_missing_inputs(self):
        for sensors in (
            [c for c in RAW_SENSOR_COLUMNS if c != "pressure_hpa"],
            ["pm25_ug_m3", "pm10_ug_m3"],
        ):
            with (
                self.subTest(sensors=sensors),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                frame = fixture()
                frame["timestamp_utc"] += pd.Timedelta(minutes=30)
                for column in set(RAW_SENSOR_COLUMNS) - set(sensors):
                    frame[column] = np.nan
                frame.to_csv(root / "observations.csv", index=False)
                (root / "dataset_manifest.json").write_text(
                    json.dumps(
                        {
                            "schema_version": SCHEMA,
                            "observations_sha256": sha256(root / "observations.csv"),
                            "source_name": "synthetic test only",
                        }
                    )
                )
                with contextlib.redirect_stdout(io.StringIO()):
                    report = train(
                        root,
                        root / "model",
                        6,
                        "2025-01-03T00:00:00Z",
                        "2025-01-04T00:00:00Z",
                        ["c"],
                        rounds=3,
                        threads=1,
                        sensors=sensors,
                    )
                self.assertEqual(report["sensor_profile"], sensors)
                self.assertNotIn("pressure_hpa", report["models"])
                for kind in ["teacher", "student"]:
                    predictions = predict(frame, root / "model", kind)
                    self.assertTrue(
                        predictions.status.eq("OFFLINE_RESEARCH_ONLY").all()
                    )
                    self.assertNotIn("forecast_pressure_hpa", predictions)
                exported = export(
                    root / "model", root / "observations.csv", root / "export"
                )
                self.assertEqual(exported["heads"], len(sensors))
                self.assertEqual(exported["parity"]["invalid_rows"], 3 * len(sensors))
                self.assertTrue(exported["parity"]["passed"])


if __name__ == "__main__":
    unittest.main()

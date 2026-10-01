from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from ml.event_classifier.features import (
    ALL_EVENT_FEATURE_COLS,
    EVENT_NAMES,
    apply_event_labels,
    build_features,
)
from ml.event_classifier.heatmap import HeatmapBuilder
from ml.six_sensor_forecast.data import sha256


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "ml/models/uci_beijing_event_rules_6sensor"


class EventClassifierTest(unittest.TestCase):
    def test_report_and_header_are_separate_from_forecast(self):
        report = json.loads((MODEL / "event_training_report.json").read_text())
        export = MODEL / "esp32_student/export"
        metadata = json.loads((export / "event_c_export_report.json").read_text())
        self.assertEqual(report["event_names"], EVENT_NAMES)
        self.assertEqual(report["input_features"], ALL_EVENT_FEATURE_COLS)
        self.assertEqual(len(ALL_EVENT_FEATURE_COLS), 17)
        self.assertEqual(
            metadata["model_report_sha256"], sha256(MODEL / "event_training_report.json")
        )
        self.assertEqual(
            metadata["header_sha256"], sha256(export / "indra_event_classifier.h")
        )
        self.assertTrue(metadata["parity"]["passed"])
        self.assertTrue(report["models"]["severe_rainstorm_squall"]["skipped"])
        self.assertTrue(report["models"]["snowstorm_blizzard"]["skipped"])
        forecast = json.loads(
            (ROOT / "ml/models/uci_beijing_6h/training_report.json").read_text()
        )
        self.assertEqual(forecast["task"], "six-sensor exact-future measurement regression")

    def test_missing_inputs_are_not_negative_rule_labels(self):
        frame = pd.DataFrame(
            {
                "timestamp_utc": pd.date_range("2025-01-01", periods=9, freq="h", tz="UTC"),
                "location_id": ["station"] * 9,
                "temperature_c": [20.0] * 9,
                "relative_humidity_pct": [60.0] * 9,
                "pressure_hpa": [1010.0] * 9,
                "pm25_ug_m3": [30.0] * 9,
                "pm10_ug_m3": [50.0] * 9,
                "wind_speed_mps": [2.0] * 9,
            }
        )
        frame.loc[7, "pm10_ug_m3"] = np.nan
        _, features = build_features(frame)
        labels = apply_event_labels(features)
        self.assertTrue(labels.loc[7, EVENT_NAMES].isna().all())
        self.assertTrue(labels.loc[8, EVENT_NAMES].isna().all())
        self.assertTrue(labels.loc[6, EVENT_NAMES].notna().all())

    def test_heatmap_loads_published_event_models(self):
        node = {
            "timestamp_utc": "2026-01-01T06:00:00Z",
            "x": 0.0,
            "y": 0.0,
            "temperature_c": 20.0,
            "relative_humidity_pct": 55.0,
            "pressure_hpa": 1010.0,
            "pm25_ug_m3": 35.0,
            "pm10_ug_m3": 60.0,
            "wind_speed_mps": 2.0,
        }
        builder = HeatmapBuilder(grid_shape=(3, 3), model_dir=MODEL, prefer_kriging=False)
        result = builder.run([node, dict(node, x=1.0, y=1.0, temperature_c=22.0)])
        self.assertEqual(result["feature_maps"].shape, (6, 3, 3))
        self.assertEqual(result["event_maps"].shape, (12, 3, 3))
        self.assertTrue(np.isnan(result["event_maps"]).all())


if __name__ == "__main__":
    unittest.main()

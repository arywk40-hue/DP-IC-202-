import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from ml.sensor_only.prepare_dataset import FEATURE_NAMES, build_sensor_only_dataset


class SensorOnlyDatasetTest(unittest.TestCase):
    def test_builds_ordered_sensor_only_features_without_future_pressure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepared = root / "prepared"
            output = root / "output"
            prepared.mkdir()

            pd.DataFrame(
                {
                    "temp_current": [20.0, 21.0, 22.0],
                    "humidity_current": [0.50, 0.55, 0.60],
                    "pressure_current": [1000.0, 1001.0, 1003.0],
                    "wind_speed_current": [3.6, 7.2, 10.8],
                    "pm25_current": [10.0, 20.0, 30.0],
                    "co2_current": [900.0, 900.0, 900.0],
                    "lightning_dist_current": [1.0, 1.0, 1.0],
                }
            ).to_csv(prepared / "features.csv", index=False)
            pd.DataFrame(
                {
                    "wildfire": [0, 0, 1],
                    "flood": [0, 0, 0],
                    "storm": [1, 1, 1],
                    "air_quality": [0, 0, 1],
                }
            ).to_csv(prepared / "labels.csv", index=False)
            pd.DataFrame(
                {
                    "location_name": ["Mandi", "Mandi", "Mandi"],
                    "last_updated": [
                        "2026-01-01T00:00:00Z",
                        "2026-01-01T01:00:00Z",
                        "2026-01-01T02:00:00Z",
                    ],
                    "latitude": [31.5892, 31.5892, 31.5892],
                    "longitude": [76.9182, 76.9182, 76.9182],
                }
            ).to_csv(prepared / "identifiers.csv", index=False)

            metadata = build_sensor_only_dataset(prepared, output, pressure_window=3)
            result = pd.read_csv(output / "features.csv")

            self.assertEqual(result.columns.tolist(), FEATURE_NAMES)
            self.assertEqual(len(result), 2)
            self.assertAlmostEqual(result.iloc[0]["wind_speed_mps"], 2.0)
            self.assertAlmostEqual(result.iloc[0]["pressure_trend_hpa_per_hour"], 1.0)
            self.assertAlmostEqual(result.iloc[1]["pressure_trend_hpa_per_hour"], 1.5)
            self.assertFalse(any("co2" in name or "lightning" in name for name in result.columns))
            self.assertEqual(metadata["metric_scope"], "integration_baseline_only_not_valid_indra_metrics")
            stored = json.loads((output / "metadata.json").read_text())
            self.assertEqual(stored["schema_version"], "indra_sensor_only_v1")
            self.assertTrue(np.isfinite(result.to_numpy()).all())


if __name__ == "__main__":
    unittest.main()


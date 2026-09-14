from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.data import SCHEMA, sha256
from ml.six_sensor_forecast.export import export
from ml.six_sensor_forecast.features import build_features, future_targets, split_masks
from ml.six_sensor_forecast.predict import predict
from ml.six_sensor_forecast.train import train


def fixture() -> pd.DataFrame:
    frames = []
    for station, offset in (("a", 0), ("b", 2), ("c", 4)):
        hours = np.arange(120)
        wave = np.sin(hours / 4)
        frames.append(
            pd.DataFrame(
                {
                    "location_id": station,
                    "timestamp_utc": pd.date_range(
                        "2025-01-01", periods=120, freq="h", tz="UTC"
                    ),
                    "temperature_c": 20 + wave + offset,
                    "relative_humidity_pct": 50 + 10 * wave,
                    "pressure_hpa": 1010 + 3 * wave,
                    "pm25_ug_m3": 30 + 20 * wave,
                    "pm10_ug_m3": 50 + 20 * wave,
                    "wind_speed_mps": 3 + wave,
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


class ForecastContractTest(unittest.TestCase):
    def test_saved_models_and_export_provenance(self):
        model_dir = Path(__file__).resolve().parents[1] / "ml/models/uci_beijing_6h"
        for kind in ("teacher", "student"):
            result = predict(fixture().iloc[:25], model_dir, kind)
            self.assertTrue(result.forecast_temperature_c.notna().all())
            self.assertTrue(result.status.eq("OFFLINE_RESEARCH_ONLY").all())
        export_dir = model_dir / "esp32_student/export"
        report = json.loads((export_dir / "c_export_report.json").read_text())
        self.assertEqual(
            report["model_report_sha256"],
            sha256(model_dir / "training_report.json"),
        )
        self.assertEqual(
            report["header_sha256"],
            sha256(export_dir / "indra_six_sensor_forecast.h"),
        )

    def test_features_use_only_six_sensors_and_past(self):
        frame = fixture()
        _, original = build_features(frame)
        changed = frame.copy()
        cutoff = pd.Timestamp("2025-01-03", tz="UTC")
        changed.loc[changed.timestamp_utc >= cutoff, "temperature_c"] = 70
        sorted_frame, perturbed = build_features(changed)
        pd.testing.assert_frame_equal(
            original.loc[sorted_frame.timestamp_utc < cutoff],
            perturbed.loc[sorted_frame.timestamp_utc < cutoff],
        )
        self.assertEqual(len(original.columns), 66)
        self.assertTrue(
            all(
                any(
                    name == sensor or name.startswith(sensor + "_")
                    for sensor in RAW_SENSOR_COLUMNS
                )
                for name in original
            )
        )
        self.assertTrue(
            original.loc[120, "temperature_c_lag_1h"]
            != original.loc[120, "temperature_c_lag_1h"]
        )

    def test_missing_hour_does_not_shift_lags_or_labels(self):
        frame = fixture().drop(index=1)
        ordered, features = build_features(frame)
        self.assertTrue(np.isnan(features.loc[1, "temperature_c_lag_1h"]))
        labels = future_targets(ordered, 1)
        self.assertTrue(np.isnan(labels.loc[0, "temperature_c"]))
        self.assertAlmostEqual(
            labels.loc[1, "temperature_c"], ordered.loc[2, "temperature_c"], places=5
        )

    def test_split_purges_future_labels_and_holds_out_station(self):
        frame = fixture()
        validation = "2025-01-03T00:00:00Z"
        test = "2025-01-04T00:00:00Z"
        masks = split_masks(frame, 6, validation, test, ["c"])
        self.assertTrue(
            (
                (frame.loc[masks["train"], "timestamp_utc"] + pd.Timedelta(hours=6))
                < pd.Timestamp(validation)
            ).all()
        )
        self.assertTrue(
            (
                (
                    frame.loc[masks["validation"], "timestamp_utc"]
                    + pd.Timedelta(hours=6)
                )
                < pd.Timestamp(test)
            ).all()
        )
        self.assertFalse(
            frame.loc[masks["train"] | masks["validation"], "location_id"].eq("c").any()
        )
        self.assertTrue(
            frame.loc[masks["geographic_test"], "location_id"].eq("c").all()
        )
        self.assertTrue((np.sum(list(masks.values()), axis=0) <= 1).all())

    def test_rejects_extra_sensors_and_duplicate_keys(self):
        frame = fixture()
        with self.assertRaisesRegex(ValueError, "exactly"):
            build_features(frame.assign(co2=400))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            build_features(pd.concat([frame, frame.iloc[[0]]]))

    def test_train_predict_export_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frame = fixture()
            frame.to_csv(root / "observations.csv", index=False)
            (root / "dataset_manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": SCHEMA,
                        "observations_sha256": sha256(root / "observations.csv"),
                        "source_name": "synthetic unit-test fixture; not benchmark evidence",
                    }
                )
            )
            with contextlib.redirect_stdout(io.StringIO()):
                report = train(
                    root,
                    root / "models",
                    6,
                    "2025-01-03T00:00:00Z",
                    "2025-01-04T00:00:00Z",
                    ["c"],
                    rounds=3,
                    threads=1,
                )
            self.assertEqual(set(report["models"]), set(RAW_SENSOR_COLUMNS))
            self.assertEqual(report["deployment_status"], "OFFLINE_RESEARCH_ONLY")
            for kind in ("teacher", "student"):
                prediction = predict(frame, root / "models", kind)
                self.assertTrue(
                    prediction.filter(like="forecast_")
                    .drop(columns="forecast_timestamp_utc")
                    .notna()
                    .all()
                    .all()
                )
                self.assertTrue(
                    (prediction.forecast_timestamp_utc - prediction.timestamp_utc)
                    .eq(pd.Timedelta(hours=6))
                    .all()
                )
            missing = frame.iloc[:3].copy()
            missing["pm25_ug_m3"] = np.nan
            prediction = predict(missing, root / "models", "student")
            self.assertTrue(prediction.status.eq("MISSING_CURRENT_SENSOR").all())
            self.assertTrue(prediction.forecast_temperature_c.isna().all())
            exported = export(
                root / "models", root / "observations.csv", root / "generated"
            )
            self.assertTrue(exported["parity"]["passed"])
            self.assertEqual(exported["parity"]["invalid_rows"], 18)
            model_path = (
                root
                / "models"
                / report["models"][RAW_SENSOR_COLUMNS[0]]["student_file"]
            )
            with model_path.open("ab") as stream:
                stream.write(b"tampered")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                predict(frame, root / "models", "student")


if __name__ == "__main__":
    unittest.main()

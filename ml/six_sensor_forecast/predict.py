"""Batch inference using the same six-sensor feature contract as training."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from ml.six_sensor_forecast.contract import sensor_profile
from ml.six_sensor_forecast.data import SCHEMA, sha256
from ml.six_sensor_forecast.features import build_features
from ml.six_sensor_forecast.train import bounded


def predict(
    observations: pd.DataFrame, model_dir: Path, kind: str = "teacher"
) -> pd.DataFrame:
    if kind not in ("teacher", "student"):
        raise ValueError("kind must be teacher or student")
    report = json.loads((model_dir / "training_report.json").read_text())
    sensors = sensor_profile(report.get("sensor_profile"))
    if report["schema_version"] != SCHEMA or set(report["models"]) != set(sensors):
        raise ValueError("Incomplete or incompatible forecast model")
    frame, temporal = build_features(observations)
    features = (
        temporal[report["architecture"]["teacher_features"]]
        if kind == "teacher"
        else frame[sensors].astype(np.float32)
    )
    if features.columns.tolist() != report["architecture"][f"{kind}_features"]:
        raise ValueError("Model feature schema mismatch")
    valid = np.isfinite(frame[sensors].to_numpy()).all(axis=1)
    result = frame[["location_id", "timestamp_utc"]].copy()
    result["forecast_timestamp_utc"] = frame.timestamp_utc + pd.Timedelta(
        hours=report["horizon_hours"]
    )
    result["status"] = np.where(
        valid, "OFFLINE_RESEARCH_ONLY", "MISSING_CURRENT_SENSOR"
    )
    matrix = (
        xgb.DMatrix(features.loc[valid], feature_names=features.columns.tolist())
        if valid.any()
        else None
    )
    for target in sensors:
        entry = report["models"][target]
        path = model_dir / entry[f"{kind}_file"]
        if sha256(path) != entry[f"{kind}_sha256"]:
            raise ValueError(f"Model checksum mismatch: {target}")
        model = xgb.Booster()
        model.load_model(path)
        values = np.full(len(frame), np.nan)
        if matrix is not None:
            values[valid] = bounded(
                frame.loc[valid, target].to_numpy()
                + entry[f"{kind}_weight"] * model.predict(matrix),
                target,
            )
        result[f"forecast_{target}"] = values
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=Path("ml/models/uci_beijing_6h"))
    parser.add_argument("--kind", choices=["teacher", "student"], default="teacher")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = predict(pd.read_csv(args.input), args.model, args.kind)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)


if __name__ == "__main__":
    main()

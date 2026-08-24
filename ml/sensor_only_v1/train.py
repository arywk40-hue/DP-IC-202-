"""Prepare a strict sensor-only dataset; no model is trained without real labels."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from feature_contract import FEATURE_NAMES, MODEL_CHECKSUM, MODEL_STATUS, SCHEMA_VERSION

REQUIRED_COLUMNS = set(FEATURE_NAMES[:5]) | {"timestamp", "latitude_deg", "longitude_deg", "label"}

def chronological_geographic_split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = frame.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    if frame["timestamp"].isna().any(): raise ValueError("invalid timestamp")
    frame["geo_cell"] = frame.latitude_deg.round(2).astype(str) + "," + frame.longitude_deg.round(2).astype(str)
    cutoff = frame.timestamp.quantile(.80)
    cells = sorted(frame.geo_cell.unique())
    heldout_cells = set(cells[::5] or cells[:1])
    test = frame[(frame.timestamp >= cutoff) | frame.geo_cell.isin(heldout_cells)]
    train = frame.drop(test.index)
    if train.empty or test.empty: raise ValueError("insufficient coverage for chronological/geographic split")
    return train, test

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("ml/model_sensor_only_v1"))
    args = parser.parse_args()
    frame = pd.read_csv(args.input)
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing: raise ValueError(f"missing required columns: {sorted(missing)}")
    if frame.label.isna().any(): raise ValueError("labels are required; refusing synthetic labels")
    train, test = chronological_geographic_split(frame)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "manifest.json").write_text(json.dumps({
        "schema_version": SCHEMA_VERSION, "model_status": MODEL_STATUS,
        "model_checksum": MODEL_CHECKSUM, "feature_names": FEATURE_NAMES,
        "train_rows": len(train), "test_rows": len(test),
        "reason": "No independently validated sensor-only model is bundled by this repository."
    }, indent=2) + "\n")
    print(f"{MODEL_STATUS}: split prepared, training intentionally not performed")

if __name__ == "__main__": main()

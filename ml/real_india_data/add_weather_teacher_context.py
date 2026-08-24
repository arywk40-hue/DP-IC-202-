"""Attach next-day weather-teacher predictions to labeled India rows."""

import argparse
import json
import os

import numpy as np
import pandas as pd
import xgboost as xgb


TARGETS = [
    "temperature_celsius", "humidity", "pressure_mb", "wind_kph",
    "precipitation_mm",
]


def add_context(raw_path, teacher_dir, output_path):
    raw = pd.read_csv(raw_path)
    required = {"location_name", "last_updated", "temperature_celsius", "humidity",
                "pressure_mb", "wind_kph", "precipitation_mm"}
    if missing := required - set(raw.columns):
        raise ValueError(f"Raw input missing columns: {sorted(missing)}")
    with open(os.path.join(teacher_dir, "normalization.json")) as handle:
        stats = json.load(handle)
    features = stats["features"]
    timestamps = pd.to_datetime(raw["last_updated"], utc=True, errors="raise")
    day = timestamps.dt.dayofyear
    values = pd.DataFrame({
        "temperature_celsius": raw["temperature_celsius"],
        "humidity": raw["humidity"],
        "pressure_mb": raw["pressure_mb"],
        "wind_kph": raw["wind_kph"],
        "precipitation_mm": raw["precipitation_mm"],
        "day_sin": np.sin(2 * np.pi * day / 365.25),
        "day_cos": np.cos(2 * np.pi * day / 365.25),
    })[features]
    X = values.to_numpy(dtype=np.float32)
    mean = np.asarray(stats["mean"], dtype=np.float32)
    std = np.asarray(stats["std"], dtype=np.float32)
    X = (X - mean) / np.where(std == 0, 1.0, std)
    result = raw.copy()
    for target in TARGETS:
        model = xgb.Booster()
        model.load_model(os.path.join(teacher_dir, f"next_day_{target}.json"))
        result[f"teacher_next_day_{target}"] = model.predict(xgb.DMatrix(X))
    result.to_csv(output_path, index=False)
    print(f"Added {len(TARGETS)} teacher context features to {len(result):,} rows")
    print(f"Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True)
    parser.add_argument("--teacher", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    add_context(args.raw, args.teacher, args.output)


if __name__ == "__main__":
    main()

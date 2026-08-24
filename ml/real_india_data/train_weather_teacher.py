"""Train an offline next-day weather-context teacher.

This is deliberately a weather forecasting task, not a hazard-label shortcut.
It can be run on the current 26-city weather table and later on an extracted
IndiaWeatherBench slice with the same canonical columns.
"""

import argparse
import json
import os

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error


FEATURES = [
    "temperature_celsius", "humidity", "pressure_mb", "wind_kph",
    "precipitation_mm", "day_sin", "day_cos",
]
TARGETS = [
    "temperature_celsius", "humidity", "pressure_mb", "wind_kph",
    "precipitation_mm",
]
PARAMS = {
    "objective": "reg:squarederror",
    "eval_metric": "rmse",
    "max_depth": 6,
    "min_child_weight": 4,
    "subsample": 0.8,
    "colsample_bytree": 0.9,
    "learning_rate": 0.08,
    "reg_lambda": 1.0,
    "tree_method": "hist",
    "seed": 42,
}


def build_examples(path):
    frame = pd.read_csv(path)
    required = {"location_name", "date_utc", *TARGETS}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Weather input missing columns: {sorted(missing)}")
    frame["timestamp"] = pd.to_datetime(frame["date_utc"], utc=True, errors="raise")
    frame = frame.sort_values(["location_name", "timestamp"]).copy()
    frame["day_of_year"] = frame["timestamp"].dt.dayofyear
    frame["day_sin"] = np.sin(2 * np.pi * frame["day_of_year"] / 365.25)
    frame["day_cos"] = np.cos(2 * np.pi * frame["day_of_year"] / 365.25)
    next_frame = frame.groupby("location_name", sort=False)[TARGETS].shift(-1)
    next_time = frame.groupby("location_name", sort=False)["timestamp"].shift(-1)
    consecutive = (next_time - frame["timestamp"]) == pd.Timedelta(days=1)
    valid = consecutive & next_frame.notna().all(axis=1)
    X = frame.loc[valid, FEATURES].to_numpy(dtype=np.float32)
    y = next_frame.loc[valid, TARGETS].to_numpy(dtype=np.float32)
    timestamps = frame.loc[valid, "timestamp"].reset_index(drop=True)
    locations = frame.loc[valid, "location_name"].reset_index(drop=True)
    return X, y, timestamps, locations


def train(input_path, output_dir, cutoff, split_strategy, holdout_fraction):
    X, y, timestamps, locations = build_examples(input_path)
    cutoff = pd.Timestamp(cutoff, tz="UTC")
    location_values = sorted(locations.unique())
    holdout_count = max(1, int(np.ceil(len(location_values) * holdout_fraction)))
    holdout_locations = location_values[-holdout_count:]
    location_mask = locations.isin(holdout_locations).to_numpy()
    if split_strategy == "temporal":
        train_mask = timestamps < cutoff
    elif split_strategy == "geo-temporal":
        train_mask = (~location_mask) & (timestamps < cutoff).to_numpy()
    else:
        raise ValueError(f"Unknown split strategy: {split_strategy}")
    test_mask = ~train_mask
    if not train_mask.any() or not test_mask.any():
        raise ValueError("Weather teacher split produced an empty train or test set")
    mean = X[train_mask].mean(axis=0)
    std = X[train_mask].std(axis=0)
    std[std == 0] = 1.0
    X_norm = (X - mean) / std
    os.makedirs(output_dir, exist_ok=True)
    metrics = {}
    for index, target in enumerate(TARGETS):
        model = xgb.train(
            PARAMS,
            xgb.DMatrix(X_norm[train_mask], label=y[train_mask, index]),
            num_boost_round=64,
            verbose_eval=False,
        )
        prediction = model.predict(xgb.DMatrix(X_norm[test_mask]))
        metrics[target] = {
            "mae": float(mean_absolute_error(y[test_mask, index], prediction)),
            "rmse": float(mean_squared_error(y[test_mask, index], prediction) ** 0.5),
        }
        model.save_model(os.path.join(output_dir, f"next_day_{target}.json"))
    with open(os.path.join(output_dir, "normalization.json"), "w") as handle:
        json.dump({"mean": mean.tolist(), "std": std.tolist(), "features": FEATURES}, handle, indent=2)
    with open(os.path.join(output_dir, "metrics.json"), "w") as handle:
        json.dump({
            "task": "next_day_weather_context",
            "targets": TARGETS,
            "input_rows": int(len(X)),
            "train_rows": int(train_mask.sum()),
            "test_rows": int(test_mask.sum()),
            "locations": int(locations.nunique()),
            "train_locations": sorted(locations[train_mask].unique().tolist()),
            "holdout_locations": holdout_locations,
            "split_strategy": split_strategy,
            "holdout_fraction": holdout_fraction,
            "cutoff_utc": cutoff.isoformat(),
            "metrics": metrics,
        }, handle, indent=2)
    print(json.dumps(metrics, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--cutoff", default="2019-01-01")
    parser.add_argument("--split-strategy", choices=["temporal", "geo-temporal"], default="temporal")
    parser.add_argument("--holdout-fraction", type=float, default=0.2)
    args = parser.parse_args()
    train(args.input, args.output, args.cutoff, args.split_strategy, args.holdout_fraction)


if __name__ == "__main__":
    main()

"""Train a weather-only next-day PM2.5 teacher from OpenAQ observations."""

import argparse
import json
import os

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error


FEATURES = ["temperature_celsius", "humidity", "pressure_mb", "wind_kph",
            "precipitation_mm", "day_sin", "day_cos"]


def train(input_path, output_dir, test_fraction, split_strategy, holdout_fraction):
    data = pd.read_csv(input_path)
    required = set(FEATURES[:5] + ["last_updated", "pm25_target_next_day"])
    if missing := required - set(data.columns):
        raise ValueError(f"AQ/weather input missing columns: {sorted(missing)}")
    timestamps = pd.to_datetime(data["last_updated"], utc=True, errors="raise")
    data["last_updated"] = timestamps
    day = timestamps.dt.dayofyear
    data["day_sin"] = np.sin(2 * np.pi * day / 365.25)
    data["day_cos"] = np.cos(2 * np.pi * day / 365.25)
    data = data.dropna(subset=FEATURES + ["pm25_target_next_day"]).sort_values("last_updated")
    cutoff = data["last_updated"].quantile(1.0 - test_fraction)
    if split_strategy == "temporal":
        train_mask = (data["last_updated"] < cutoff).to_numpy()
        holdout_locations = []
    elif split_strategy == "geo-temporal":
        locations = sorted(data["location_name"].unique())
        holdout_count = max(1, int(np.ceil(len(locations) * holdout_fraction)))
        holdout_locations = locations[-holdout_count:]
        train_mask = (
            ~data["location_name"].isin(holdout_locations)
            & (data["last_updated"] < cutoff)
        ).to_numpy()
    else:
        raise ValueError(f"Unknown split strategy: {split_strategy}")
    test_mask = ~train_mask
    X = data[FEATURES].to_numpy(dtype=np.float32)
    y = data["pm25_target_next_day"].to_numpy(dtype=np.float32)
    mean = X[train_mask].mean(axis=0)
    std = np.where(X[train_mask].std(axis=0) == 0, 1.0, X[train_mask].std(axis=0))
    X_norm = (X - mean) / std
    model = xgb.train(
        {"objective": "reg:squarederror", "eval_metric": "rmse", "max_depth": 4,
         "learning_rate": 0.05, "subsample": 0.8, "colsample_bytree": 0.9,
         "reg_lambda": 2.0, "tree_method": "hist", "seed": 42},
        xgb.DMatrix(X_norm[train_mask], label=y[train_mask]),
        num_boost_round=64,
        verbose_eval=False,
    )
    prediction = model.predict(xgb.DMatrix(X_norm[test_mask]))
    metrics = {
        "rows": int(len(data)), "train_rows": int(train_mask.sum()),
        "test_rows": int(test_mask.sum()), "cutoff_utc": cutoff.isoformat(),
        "split_strategy": split_strategy, "holdout_locations": holdout_locations,
        "mae": float(mean_absolute_error(y[test_mask], prediction)),
        "rmse": float(mean_squared_error(y[test_mask], prediction) ** 0.5),
        "target_min": float(y.min()), "target_max": float(y.max()),
    }
    os.makedirs(output_dir, exist_ok=True)
    model.save_model(os.path.join(output_dir, "next_day_pm25.json"))
    with open(os.path.join(output_dir, "normalization.json"), "w") as handle:
        json.dump({"mean": mean.tolist(), "std": std.tolist(), "feature_names": FEATURES}, handle, indent=2)
    with open(os.path.join(output_dir, "metrics.json"), "w") as handle:
        json.dump(metrics, handle, indent=2)
    print(json.dumps(metrics, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--split-strategy", choices=["temporal", "geo-temporal"], default="temporal")
    parser.add_argument("--holdout-fraction", type=float, default=0.2)
    args = parser.parse_args()
    train(args.input, args.output, args.test_fraction, args.split_strategy, args.holdout_fraction)


if __name__ == "__main__":
    main()

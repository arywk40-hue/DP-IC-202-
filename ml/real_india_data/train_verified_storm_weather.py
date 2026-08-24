"""Train an offline storm teacher from long-window weather + IMD events."""

import argparse
import json
import os

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import classification_report


FEATURES = ["temperature_celsius", "humidity", "pressure_mb", "wind_kph",
            "precipitation_mm", "day_sin", "day_cos"]
PARAMS = {
    "objective": "binary:logistic", "eval_metric": "logloss", "max_depth": 5,
    "min_child_weight": 4, "subsample": 0.8, "colsample_bytree": 0.9,
    "learning_rate": 0.08, "reg_lambda": 1.0, "tree_method": "hist", "seed": 42,
}


def train(weather_path, labeled_path, output_dir, holdout_fraction, hazard="storm"):
    weather = pd.read_csv(weather_path)
    labels = pd.read_csv(labeled_path)
    weather["timestamp_utc"] = pd.to_datetime(weather["date_utc"], utc=True, errors="raise")
    labels["timestamp_utc"] = pd.to_datetime(labels["last_updated"], utc=True, errors="raise")
    labels = labels[["location_name", "timestamp_utc", hazard]].drop_duplicates(
        ["location_name", "timestamp_utc"]
    )
    data = weather.merge(labels, on=["location_name", "timestamp_utc"], how="left", validate="one_to_one")
    day = data["timestamp_utc"].dt.dayofyear
    data["day_sin"] = np.sin(2 * np.pi * day / 365.25)
    data["day_cos"] = np.cos(2 * np.pi * day / 365.25)
    known = data[hazard].notna().to_numpy()
    if data.loc[known, hazard].sum() < 10:
        raise ValueError(f"Fewer than 10 positive {hazard} rows are available")

    locations = sorted(data["location_name"].unique())
    holdout_count = max(1, int(np.ceil(len(locations) * holdout_fraction)))
    holdout = locations[-holdout_count:]
    location_mask = data["location_name"].isin(holdout).to_numpy()
    cutoff = data["timestamp_utc"].quantile(1.0 - holdout_fraction)
    train_mask = known & (~location_mask) & (data["timestamp_utc"] < cutoff).to_numpy()
    test_mask = known & ~train_mask
    y = data[hazard].fillna(0).to_numpy(dtype=np.float32)
    if y[train_mask].sum() == 0 or y[test_mask].sum() == 0:
        raise ValueError("Geo-temporal storm split has no positive train or test rows")
    X = data[FEATURES].to_numpy(dtype=np.float32)
    mean = X[train_mask].mean(axis=0)
    std = np.where(X[train_mask].std(axis=0) == 0, 1.0, X[train_mask].std(axis=0))
    X_norm = (X - mean) / std
    positives = y[train_mask].sum()
    negatives = train_mask.sum() - positives
    model = xgb.train(
        dict(PARAMS, scale_pos_weight=float(negatives / positives)),
        xgb.DMatrix(X_norm[train_mask], label=y[train_mask]),
        num_boost_round=64,
        verbose_eval=False,
    )
    probability = model.predict(xgb.DMatrix(X_norm[test_mask]))
    prediction = (probability >= 0.5).astype(int)
    report = classification_report(y[test_mask], prediction, output_dict=True, zero_division=0)
    positive = report.get("1", report.get("1.0", {}))
    metrics = {"accuracy": report["accuracy"], "precision": positive.get("precision", 0.0),
               "recall": positive.get("recall", 0.0), "f1": positive.get("f1-score", 0.0),
               "threshold": 0.5, "known_rows": int(known.sum()),
               "positive_rows": int(y[known].sum()), "train_positive": int(positives),
               "test_positive": int(y[test_mask].sum())}
    os.makedirs(output_dir, exist_ok=True)
    model.save_model(os.path.join(output_dir, f"xgboost_{hazard}.json"))
    with open(os.path.join(output_dir, "normalization.json"), "w") as handle:
        json.dump({"mean": mean.tolist(), "std": std.tolist(), "feature_names": FEATURES}, handle, indent=2)
    with open(os.path.join(output_dir, "metrics.json"), "w") as handle:
        json.dump(metrics, handle, indent=2)
    with open(os.path.join(output_dir, "split.json"), "w") as handle:
        json.dump({"strategy": "geo-temporal", "cutoff_utc": cutoff.isoformat(),
                   "train_locations": sorted(set(locations) - set(holdout)),
                   "holdout_locations": holdout, "train_rows": int(train_mask.sum()),
                   "test_rows": int(test_mask.sum())}, handle, indent=2)
    print(json.dumps(metrics, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weather", required=True)
    parser.add_argument("--labeled-weather", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--holdout-fraction", type=float, default=0.2)
    parser.add_argument("--hazard", choices=["storm", "flood"], default="storm")
    args = parser.parse_args()
    train(args.weather, args.labeled_weather, args.output, args.holdout_fraction, args.hazard)


if __name__ == "__main__":
    main()

"""Train the 14-feature edge model with a geographic India holdout.

The test set is made of complete locations, not randomly selected rows. This
is the first meaningful India transfer check for the pilot.
"""

import argparse
import json
import os

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import classification_report


HAZARDS = ["wildfire", "flood", "storm", "air_quality"]
THRESHOLDS = {"wildfire": 0.70, "flood": 0.70, "storm": 0.75, "air_quality": 0.65}
PARAMS = {
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "max_depth": 4,
    "min_child_weight": 2,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "learning_rate": 0.1,
    "gamma": 0.1,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "tree_method": "hist",
    "seed": 42,
}


def train(data_dir: str, output_dir: str, holdout_fraction: float = 0.2,
          split_strategy: str = "geographic"):
    X_df = pd.read_csv(os.path.join(data_dir, "features.csv"))
    y_df = pd.read_csv(os.path.join(data_dir, "labels.csv"))
    ids = pd.read_csv(os.path.join(data_dir, "identifiers.csv"))
    if not (len(X_df) == len(y_df) == len(ids)):
        raise ValueError("features.csv, labels.csv, and identifiers.csv are not aligned")
    if "location_name" not in ids:
        raise ValueError("identifiers.csv must contain location_name")

    locations = sorted(ids["location_name"].dropna().unique())
    n_holdout = max(1, int(np.ceil(len(locations) * holdout_fraction)))
    holdout_locations = locations[-n_holdout:]
    location_mask = ids["location_name"].isin(holdout_locations).to_numpy()

    cutoff = None
    if split_strategy == "geographic":
        test_mask = location_mask
        train_mask = ~test_mask
    elif split_strategy == "geo-temporal":
        if "last_updated" not in ids.columns:
            raise ValueError("geo-temporal split requires last_updated in identifiers.csv")
        timestamps = pd.to_datetime(ids["last_updated"], utc=True, errors="coerce")
        if timestamps.isna().any():
            raise ValueError("identifiers.csv contains invalid last_updated values")
        cutoff = timestamps.quantile(1.0 - holdout_fraction)
        future_mask = timestamps >= cutoff
        # Train only on earlier data from non-held-out locations. The test set
        # contains all dates for held-out locations plus the future period for
        # locations seen during training.
        train_mask = (~location_mask) & (~future_mask.to_numpy())
        test_mask = ~train_mask
    else:
        raise ValueError(f"Unknown split strategy: {split_strategy}")
    if train_mask.sum() == 0 or test_mask.sum() == 0:
        raise ValueError("Geographic split produced an empty train or test set")

    X = X_df.to_numpy(dtype=np.float32)
    y = y_df.to_numpy(dtype=np.float32)
    mean = X[train_mask].mean(axis=0)
    std = X[train_mask].std(axis=0)
    std[std == 0] = 1.0
    X_norm = (X - mean) / std

    os.makedirs(output_dir, exist_ok=True)
    metrics = {}
    for idx, hazard in enumerate(HAZARDS):
        y_train = y[train_mask, idx]
        y_test = y[test_mask, idx]
        positives = y_train.sum()
        negatives = len(y_train) - positives
        params = dict(PARAMS, scale_pos_weight=float(negatives / positives) if positives else 1.0)
        model = xgb.train(
            params,
            xgb.DMatrix(X_norm[train_mask], label=y_train),
            num_boost_round=16,
            verbose_eval=False,
        )
        probabilities = model.predict(xgb.DMatrix(X_norm[test_mask]))
        predictions = (probabilities >= THRESHOLDS[hazard]).astype(int)
        report = classification_report(y_test, predictions, output_dict=True, zero_division=0)
        positive_report = report.get("1", report.get("1.0", {}))
        metrics[hazard] = {
            "accuracy": report["accuracy"],
            "precision": positive_report.get("precision", 0.0),
            "recall": positive_report.get("recall", 0.0),
            "f1": positive_report.get("f1-score", 0.0),
            "threshold": THRESHOLDS[hazard],
            "train_positive": int(positives),
            "test_positive": int(y_test.sum()),
        }
        model.save_model(os.path.join(output_dir, f"xgboost_{hazard}.json"))

    with open(os.path.join(output_dir, "normalization.json"), "w") as f:
        json.dump({"mean": mean.tolist(), "std": std.tolist(), "feature_names": X_df.columns.tolist()}, f, indent=2)
    with open(os.path.join(output_dir, "feature_names.json"), "w") as f:
        json.dump(X_df.columns.tolist(), f, indent=2)
    with open(os.path.join(output_dir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    with open(os.path.join(output_dir, "split.json"), "w") as f:
        json.dump({
            "strategy": split_strategy,
            "holdout_fraction": holdout_fraction,
            "train_locations": sorted(set(locations) - set(holdout_locations)),
            "holdout_locations": holdout_locations,
            "train_rows": int(train_mask.sum()),
            "test_rows": int(test_mask.sum()),
            "future_cutoff_utc": str(cutoff) if cutoff is not None else None,
        }, f, indent=2)

    print(f"Split:       {split_strategy}")
    print(f"Train rows:  {train_mask.sum():,} across {len(locations) - len(holdout_locations)} locations")
    print(f"Test rows:   {test_mask.sum():,} across {len(holdout_locations)} held-out locations: {holdout_locations}")
    if cutoff is not None:
        print(f"Future cut:  {cutoff}")
    for hazard, result in metrics.items():
        print(f"{hazard:12s} accuracy={result['accuracy']:.4f} precision={result['precision']:.4f} "
              f"recall={result['recall']:.4f} f1={result['f1']:.4f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--holdout-fraction", type=float, default=0.2)
    parser.add_argument("--split-strategy", choices=["geographic", "geo-temporal"], default="geographic")
    args = parser.parse_args()
    train(args.data, args.output, args.holdout_fraction, args.split_strategy)


if __name__ == "__main__":
    main()

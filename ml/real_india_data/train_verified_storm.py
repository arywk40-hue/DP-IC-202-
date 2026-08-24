"""Train the storm head using IMD best-track labels only."""

import argparse
import json
import os

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import classification_report


PARAMS = {
    "objective": "binary:logistic", "eval_metric": "logloss", "max_depth": 4,
    "min_child_weight": 2, "subsample": 0.8, "colsample_bytree": 0.8,
    "learning_rate": 0.1, "gamma": 0.1, "reg_alpha": 0.1,
    "reg_lambda": 1.0, "tree_method": "hist", "seed": 42,
}


def train(data_dir, labeled_weather, output_dir, holdout_fraction, normalization_from=None):
    X_df = pd.read_csv(os.path.join(data_dir, "features.csv"))
    ids = pd.read_csv(os.path.join(data_dir, "identifiers.csv"))
    labels = pd.read_csv(labeled_weather)
    if not (len(X_df) == len(ids)):
        raise ValueError("features.csv and identifiers.csv are not aligned")
    labels["timestamp_utc"] = pd.to_datetime(labels["last_updated"], utc=True, errors="raise")
    ids["timestamp_utc"] = pd.to_datetime(ids["last_updated"], utc=True, errors="raise")
    key = ["location_name", "timestamp_utc"]
    verified = labels[key + ["storm"]].drop_duplicates(key)
    merged = ids[key].merge(verified, on=key, how="left", validate="one_to_one")
    known = merged["storm"].notna().to_numpy()
    if known.sum() == 0 or merged.loc[known, "storm"].sum() == 0:
        raise ValueError("No positive verified storm labels found")

    locations = sorted(ids["location_name"].unique())
    n_holdout = max(1, int(np.ceil(len(locations) * holdout_fraction)))
    holdout_locations = locations[-n_holdout:]
    location_mask = ids["location_name"].isin(holdout_locations).to_numpy()
    timestamps = ids["timestamp_utc"]
    cutoff = timestamps.quantile(1.0 - holdout_fraction)
    train_mask = known & (~location_mask) & (timestamps < cutoff).to_numpy()
    test_mask = known & ~train_mask
    if train_mask.sum() == 0 or test_mask.sum() == 0:
        raise ValueError("Verified storm split produced an empty train or test set")
    if merged.loc[train_mask, "storm"].sum() == 0:
        raise ValueError("Verified storm train split contains no positive labels")

    X = X_df.to_numpy(dtype=np.float32)
    y = merged["storm"].fillna(0).to_numpy(dtype=np.float32)
    if normalization_from:
        with open(os.path.join(normalization_from, "normalization.json")) as handle:
            normalization = json.load(handle)
        if normalization.get("feature_names") != X_df.columns.tolist():
            raise ValueError("Shared normalization feature schema does not match storm data")
        mean = np.asarray(normalization["mean"], dtype=np.float32)
        std = np.asarray(normalization["std"], dtype=np.float32)
    else:
        mean = X[train_mask].mean(axis=0)
        std = X[train_mask].std(axis=0)
    std = np.where(std == 0, 1.0, std)
    X_norm = (X - mean) / std
    positives = y[train_mask].sum()
    negatives = train_mask.sum() - positives
    model = xgb.train(
        dict(PARAMS, scale_pos_weight=float(negatives / positives)),
        xgb.DMatrix(X_norm[train_mask], label=y[train_mask]),
        num_boost_round=16,
        verbose_eval=False,
    )
    probability = model.predict(xgb.DMatrix(X_norm[test_mask]))
    prediction = (probability >= 0.5).astype(int)
    report = classification_report(y[test_mask], prediction, output_dict=True, zero_division=0)
    positive = report.get("1", report.get("1.0", {}))
    metrics = {
        "accuracy": report["accuracy"], "precision": positive.get("precision", 0.0),
        "recall": positive.get("recall", 0.0), "f1": positive.get("f1-score", 0.0),
        "threshold": 0.5, "train_positive": int(positives),
        "test_positive": int(y[test_mask].sum()), "known_rows": int(known.sum()),
    }
    os.makedirs(output_dir, exist_ok=True)
    model.save_model(os.path.join(output_dir, "xgboost_storm.json"))
    with open(os.path.join(output_dir, "normalization.json"), "w") as handle:
        json.dump({"mean": mean.tolist(), "std": std.tolist(),
                   "feature_names": X_df.columns.tolist()}, handle, indent=2)
    with open(os.path.join(output_dir, "feature_names.json"), "w") as handle:
        json.dump(X_df.columns.tolist(), handle, indent=2)
    with open(os.path.join(output_dir, "metrics.json"), "w") as handle:
        json.dump(metrics, handle, indent=2)
    with open(os.path.join(output_dir, "split.json"), "w") as handle:
        json.dump({"strategy": "geo-temporal", "cutoff_utc": cutoff.isoformat(),
                   "train_locations": sorted(set(locations) - set(holdout_locations)),
                   "holdout_locations": holdout_locations,
                   "train_rows": int(train_mask.sum()), "test_rows": int(test_mask.sum()),
                   "known_rows": int(known.sum())}, handle, indent=2)
    print(json.dumps(metrics, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True)
    parser.add_argument("--labeled-weather", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--holdout-fraction", type=float, default=0.2)
    parser.add_argument("--normalization-from", default=None,
                        help="Existing edge model directory for shared C-compatible normalization")
    args = parser.parse_args()
    train(args.data, args.labeled_weather, args.output, args.holdout_fraction,
          args.normalization_from)


if __name__ == "__main__":
    main()

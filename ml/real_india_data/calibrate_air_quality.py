"""Sweep air-quality alert thresholds on the strict geo-temporal holdout."""

import argparse
import json
import os

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, precision_recall_fscore_support


def evaluate(y_true, probabilities, threshold):
    predicted = (probabilities >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, predicted, average="binary", zero_division=0
    )
    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, predicted)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="Prepared edge data directory")
    parser.add_argument("--model", required=True, help="Distilled edge model directory")
    parser.add_argument("--output", required=True, help="Calibration JSON path")
    args = parser.parse_args()

    features = pd.read_csv(os.path.join(args.data, "features.csv"))
    labels = pd.read_csv(os.path.join(args.data, "labels.csv"))["air_quality"].to_numpy()
    ids = pd.read_csv(os.path.join(args.data, "identifiers.csv"))
    with open(os.path.join(args.model, "normalization.json")) as f:
        stats = json.load(f)
    with open(os.path.join(args.model, "split.json")) as f:
        split = json.load(f)

    timestamps = pd.to_datetime(ids["last_updated"], utc=True, errors="raise")
    cutoff = pd.to_datetime(split["future_cutoff_utc"], utc=True)
    train_mask = (
        ids["location_name"].isin(split["train_locations"]).to_numpy()
        & (timestamps < cutoff).to_numpy()
    )
    test_mask = ~train_mask
    mean = np.asarray(stats["mean"], dtype=np.float32)
    std = np.asarray(stats["std"], dtype=np.float32)
    X = (features.to_numpy(dtype=np.float32) - mean) / np.where(std == 0, 1.0, std)
    model = xgb.Booster()
    model.load_model(os.path.join(args.model, "xgboost_air_quality.json"))
    probabilities = model.predict(xgb.DMatrix(X[test_mask]))
    y_true = labels[test_mask]

    sweep = [evaluate(y_true, probabilities, threshold)
             for threshold in np.arange(0.05, 0.951, 0.01)]
    best_f1 = max(sweep, key=lambda row: (row["f1"], row["precision"]))
    recall_target = max(
        (row for row in sweep if row["recall"] >= 0.90),
        key=lambda row: (row["precision"], row["f1"]),
        default=None,
    )
    default = evaluate(y_true, probabilities, 0.65)
    result = {
        "split": split,
        "test_rows": int(test_mask.sum()),
        "test_positive": int(y_true.sum()),
        "default_operating_point": default,
        "best_f1_operating_point": best_f1,
        "recall_at_least_0_90_operating_point": recall_target,
        "threshold_sweep": sweep,
    }
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k != "threshold_sweep"}, indent=2))


if __name__ == "__main__":
    main()

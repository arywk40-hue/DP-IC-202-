"""Distill a masked offline teacher into the fixed 14-feature edge contract."""

import argparse
import json
import os

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import classification_report


HAZARDS = ["wildfire", "flood", "storm", "air_quality"]
PARAMS = {
    "objective": "binary:logistic", "eval_metric": "logloss", "max_depth": 4,
    "min_child_weight": 2, "subsample": 0.8, "colsample_bytree": 0.8,
    "learning_rate": 0.1, "reg_lambda": 1.0, "tree_method": "hist", "seed": 42,
}


def normalize(values, stats):
    mean = np.asarray(stats["mean"], dtype=np.float32)
    std = np.asarray(stats["std"], dtype=np.float32)
    return (values - mean) / np.where(std == 0, 1.0, std)


def positive_metrics(y_true, probability, threshold=0.5):
    prediction = (probability >= threshold).astype(int)
    report = classification_report(y_true, prediction, output_dict=True, zero_division=0)
    positive = report.get("1", report.get("1.0", {}))
    return {
        "precision": positive.get("precision", 0.0),
        "recall": positive.get("recall", 0.0),
        "f1": positive.get("f1-score", 0.0),
        "threshold": threshold,
    }


def distill(edge_data, teacher_data, teacher_dir, edge_model_dir, output_dir, alpha):
    edge_features = pd.read_csv(os.path.join(edge_data, "features.csv"))
    labels = pd.read_csv(os.path.join(edge_data, "labels.csv"))
    ids = pd.read_csv(os.path.join(edge_data, "identifiers.csv"))
    rich_features = pd.read_csv(os.path.join(teacher_data, "features.csv"))
    if not (len(edge_features) == len(labels) == len(ids) == len(rich_features)):
        raise ValueError("edge, teacher, labels, and identifiers must be row-aligned")

    with open(os.path.join(teacher_dir, "normalization.json")) as handle:
        teacher_norm = json.load(handle)
    with open(os.path.join(edge_model_dir, "normalization.json")) as handle:
        edge_norm = json.load(handle)
    teacher_metrics = json.load(open(os.path.join(teacher_dir, "metrics.json")))
    cutoff = pd.to_datetime(teacher_metrics["cutoff_utc"], utc=True)
    holdout = set(teacher_metrics["holdout_locations"])
    timestamps = pd.to_datetime(ids["last_updated"], utc=True, errors="raise")
    train_mask = (~ids["location_name"].isin(holdout) & (timestamps < cutoff)).to_numpy()
    test_mask = ~train_mask

    rich_norm = normalize(rich_features.to_numpy(dtype=np.float32), teacher_norm)
    edge_normed = normalize(edge_features.to_numpy(dtype=np.float32), edge_norm)
    os.makedirs(output_dir, exist_ok=True)
    metrics = {"alpha_hard_label": alpha, "train_rows": int(train_mask.sum()),
               "test_rows": int(test_mask.sum()), "heads": {}}

    for hazard in HAZARDS:
        teacher = xgb.Booster()
        teacher.load_model(os.path.join(teacher_dir, f"xgboost_{hazard}.json"))
        teacher_probability = teacher.predict(xgb.DMatrix(rich_norm))
        hard = labels[hazard].to_numpy(dtype=np.float32)
        soft = alpha * hard + (1.0 - alpha) * teacher_probability
        positives = hard[train_mask].sum()
        negatives = train_mask.sum() - positives
        student = xgb.train(
            dict(PARAMS, scale_pos_weight=float(negatives / positives) if positives else 1.0),
            xgb.DMatrix(edge_normed[train_mask], label=soft[train_mask]),
            # Match the firmware export ceiling; the exporter must never
            # truncate a larger student silently.
            num_boost_round=16, verbose_eval=False,
        )
        student_probability = student.predict(xgb.DMatrix(edge_normed[test_mask]))
        student.save_model(os.path.join(output_dir, f"xgboost_{hazard}.json"))
        metrics["heads"][hazard] = {
            "teacher": positive_metrics(hard[test_mask], teacher_probability[test_mask]),
            "student": positive_metrics(hard[test_mask], student_probability),
        }

    with open(os.path.join(output_dir, "normalization.json"), "w") as handle:
        json.dump(edge_norm, handle, indent=2)
    with open(os.path.join(output_dir, "feature_names.json"), "w") as handle:
        json.dump(edge_features.columns.tolist(), handle, indent=2)
    with open(os.path.join(output_dir, "metrics.json"), "w") as handle:
        json.dump(metrics, handle, indent=2)
    with open(os.path.join(output_dir, "split.json"), "w") as handle:
        json.dump({"strategy": "geo-temporal", "cutoff_utc": cutoff.isoformat(),
                   "holdout_locations": sorted(holdout), "train_rows": int(train_mask.sum()),
                   "test_rows": int(test_mask.sum())}, handle, indent=2)
    print(json.dumps(metrics, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edge-data", required=True)
    parser.add_argument("--teacher-data", required=True)
    parser.add_argument("--teacher", required=True)
    parser.add_argument("--edge-model", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--alpha", type=float, default=0.2)
    args = parser.parse_args()
    distill(args.edge_data, args.teacher_data, args.teacher, args.edge_model, args.output, args.alpha)


if __name__ == "__main__":
    main()

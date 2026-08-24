"""Distill the rich India air-quality teacher into the 14-feature edge student."""

import argparse
import json
import os

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import classification_report


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


def normalize(X, stats):
    mean = np.asarray(stats["mean"], dtype=np.float32)
    std = np.asarray(stats["std"], dtype=np.float32)
    return (X - mean) / np.where(std == 0, 1.0, std)


def positive_metrics(y_true, probabilities, threshold=0.65):
    predictions = (probabilities >= threshold).astype(int)
    report = classification_report(y_true, predictions, output_dict=True, zero_division=0)
    positive = report.get("1", report.get("1.0", {}))
    return {
        "accuracy": report["accuracy"],
        "precision": positive.get("precision", 0.0),
        "recall": positive.get("recall", 0.0),
        "f1": positive.get("f1-score", 0.0),
        "threshold": threshold,
    }


def distill(edge_data: str, teacher_dir: str, edge_model_dir: str,
            output_dir: str, alpha: float, teacher_data: str = None):
    X_edge_df = pd.read_csv(os.path.join(edge_data, "features.csv"))
    y_df = pd.read_csv(os.path.join(edge_data, "labels.csv"))
    ids = pd.read_csv(os.path.join(edge_data, "identifiers.csv"))
    teacher_data = teacher_data or os.path.join(
        os.path.dirname(edge_data), "offline_prepared_26"
    )
    X_teacher_df = pd.read_csv(os.path.join(teacher_data, "features.csv"))
    if not (len(X_edge_df) == len(X_teacher_df) == len(y_df) == len(ids)):
        raise ValueError("Edge, teacher, labels, and identifiers are not aligned")

    with open(os.path.join(teacher_dir, "normalization.json")) as f:
        teacher_norm = json.load(f)
    with open(os.path.join(teacher_dir, "split.json")) as f:
        split = json.load(f)
    timestamps = pd.to_datetime(ids["last_updated"], utc=True, errors="coerce")
    cutoff = pd.to_datetime(split["future_cutoff_utc"], utc=True)
    train_locations = set(split["train_locations"])
    train_mask = (
        ids["location_name"].isin(train_locations).to_numpy()
        & (timestamps < cutoff).to_numpy()
    )
    test_mask = ~train_mask

    X_teacher = normalize(X_teacher_df.to_numpy(dtype=np.float32), teacher_norm)
    teacher = xgb.Booster()
    teacher.load_model(os.path.join(teacher_dir, "xgboost_air_quality.json"))
    teacher_probabilities = teacher.predict(xgb.DMatrix(X_teacher))

    y_true = y_df["air_quality"].to_numpy(dtype=np.float32)
    soft_targets = alpha * y_true + (1.0 - alpha) * teacher_probabilities
    X_edge = X_edge_df.to_numpy(dtype=np.float32)
    with open(os.path.join(edge_model_dir, "normalization.json")) as f:
        edge_norm = json.load(f)
    X_edge_norm = normalize(X_edge, edge_norm)

    positives = y_true[train_mask].sum()
    negatives = train_mask.sum() - positives
    model = xgb.train(
        dict(PARAMS, scale_pos_weight=float(negatives / positives) if positives else 1.0),
        xgb.DMatrix(X_edge_norm[train_mask], label=soft_targets[train_mask]),
        num_boost_round=16,
        verbose_eval=False,
    )
    student_prob = model.predict(xgb.DMatrix(X_edge_norm[test_mask]))

    hard = xgb.Booster()
    hard.load_model(os.path.join(edge_model_dir, "xgboost_air_quality.json"))
    hard_prob = hard.predict(xgb.DMatrix(X_edge_norm[test_mask]))

    os.makedirs(output_dir, exist_ok=True)
    model.save_model(os.path.join(output_dir, "xgboost_air_quality.json"))
    with open(os.path.join(output_dir, "normalization.json"), "w") as f:
        json.dump(edge_norm, f, indent=2)
    with open(os.path.join(output_dir, "feature_names.json"), "w") as f:
        json.dump(X_edge_df.columns.tolist(), f, indent=2)
    metrics = {
        "alpha_hard_label": alpha,
        "teacher_f1": positive_metrics(y_true[test_mask], teacher_probabilities[test_mask])["f1"],
        "hard_edge_student": positive_metrics(y_true[test_mask], hard_prob),
        "distilled_edge_student": positive_metrics(y_true[test_mask], student_prob),
        "train_rows": int(train_mask.sum()),
        "test_rows": int(test_mask.sum()),
    }
    with open(os.path.join(output_dir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    with open(os.path.join(output_dir, "split.json"), "w") as f:
        json.dump(split, f, indent=2)
    print(json.dumps(metrics, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edge-data", required=True)
    parser.add_argument("--teacher", required=True)
    parser.add_argument("--edge-model", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--alpha", type=float, default=0.5,
                        help="Weight of hard labels; remaining weight uses teacher probabilities")
    parser.add_argument("--teacher-data", default=None,
                        help="Prepared rich teacher data directory; defaults to offline_prepared_26")
    args = parser.parse_args()
    distill(args.edge_data, args.teacher, args.edge_model, args.output, args.alpha, args.teacher_data)


if __name__ == "__main__":
    main()

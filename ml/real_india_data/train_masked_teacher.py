"""Train an offline multi-head teacher without converting unknown labels to 0.

The feature table can be shared by all heads, while each head may have a
different label source and coverage.  Verified labels supplied with
``--verified-labels`` replace the corresponding weak-label column and are
used only where their value is observed.
"""

import argparse
import json
import os

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import average_precision_score, brier_score_loss, classification_report


HAZARDS = ["wildfire", "flood", "storm", "air_quality"]
PARAMS = {
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "max_depth": 5,
    "min_child_weight": 2,
    "subsample": 0.8,
    "colsample_bytree": 0.9,
    "learning_rate": 0.05,
    "reg_lambda": 2.0,
    "tree_method": "hist",
    "seed": 42,
}


def _positive_report(y_true, prediction):
    report = classification_report(y_true, prediction, output_dict=True, zero_division=0)
    return report, report.get("1", report.get("1.0", {}))


def _timestamp_key(frame):
    column = "timestamp_utc" if "timestamp_utc" in frame else "last_updated"
    return pd.to_datetime(frame[column], utc=True, errors="raise").dt.strftime("%Y-%m-%d")


def train(features_path, labels_path, identifiers_path, output_dir,
          verified_labels_path=None, verified_hazard=None,
          holdout_fraction=0.2, test_fraction=0.2):
    features = pd.read_csv(features_path)
    labels = pd.read_csv(labels_path)
    ids = pd.read_csv(identifiers_path)
    if not (len(features) == len(labels) == len(ids)):
        raise ValueError("features, labels, and identifiers must have equal row counts")
    if set(HAZARDS) - set(labels.columns):
        raise ValueError("base labels must contain all four hazard columns")
    if "location_name" not in ids or "last_updated" not in ids:
        raise ValueError("identifiers require location_name and last_updated")

    timestamps = pd.to_datetime(ids["last_updated"], utc=True, errors="raise")
    locations = sorted(ids["location_name"].dropna().unique())
    holdout_count = max(1, int(np.ceil(len(locations) * holdout_fraction)))
    holdout_locations = locations[-holdout_count:]
    cutoff = timestamps.quantile(1.0 - test_fraction)
    location_mask = ids["location_name"].isin(holdout_locations).to_numpy()
    train_rows = (~location_mask) & (timestamps < cutoff).to_numpy()
    test_rows = ~train_rows
    if not train_rows.any() or not test_rows.any():
        raise ValueError("geo-temporal split produced an empty partition")

    label_frame = labels[HAZARDS].copy()
    label_sources = {hazard: "weak" for hazard in HAZARDS}
    if verified_labels_path:
        if not verified_hazard or verified_hazard not in HAZARDS:
            raise ValueError("verified_hazard must name one of the four hazards")
        verified = pd.read_csv(verified_labels_path)
        if not {"location_name", verified_hazard}.issubset(verified.columns):
            raise ValueError("verified labels need location_name and the hazard column")
        verified = verified.copy()
        verified["date_key"] = _timestamp_key(verified)
        lookup = verified[["location_name", "date_key", verified_hazard]].copy()
        lookup = lookup.drop_duplicates(["location_name", "date_key"])
        keys = pd.DataFrame({"location_name": ids["location_name"], "date_key": timestamps.dt.strftime("%Y-%m-%d")})
        merged = keys.merge(lookup, on=["location_name", "date_key"], how="left")[verified_hazard]
        label_frame[verified_hazard] = pd.to_numeric(merged, errors="coerce")
        label_sources[verified_hazard] = os.path.basename(verified_labels_path)

    X = features.to_numpy(dtype=np.float32)
    feature_names = features.columns.tolist()
    mean = X[train_rows].mean(axis=0)
    std = X[train_rows].std(axis=0)
    std[std == 0] = 1.0
    X_norm = (X - mean) / std

    os.makedirs(output_dir, exist_ok=True)
    metrics = {}
    for hazard in HAZARDS:
        observed = label_frame[hazard].notna().to_numpy()
        train_mask = train_rows & observed
        test_mask = test_rows & observed
        if not train_mask.any() or not test_mask.any():
            metrics[hazard] = {
                "status": "NOT_READY",
                "label_source": label_sources[hazard],
                "train_labeled_rows": int(train_mask.sum()),
                "test_labeled_rows": int(test_mask.sum()),
            }
            continue
        y_train = label_frame.loc[train_mask, hazard].to_numpy(dtype=np.float32)
        y_test = label_frame.loc[test_mask, hazard].to_numpy(dtype=np.float32)
        positive_count = float(y_train.sum())
        negative_count = float(len(y_train) - positive_count)
        params = dict(PARAMS, scale_pos_weight=(negative_count / positive_count if positive_count else 1.0))
        # Reserve the latest part of the training partition for threshold
        # selection. The final test partition remains untouched.
        train_times = timestamps[train_mask]
        calibration_cutoff = train_times.quantile(0.8)
        fit_mask = train_mask & (timestamps < calibration_cutoff).to_numpy()
        calibration_mask = train_mask & (timestamps >= calibration_cutoff).to_numpy()
        fit_model = xgb.train(
            params, xgb.DMatrix(X_norm[fit_mask], label=label_frame.loc[fit_mask, hazard]),
            num_boost_round=96, verbose_eval=False,
        )
        threshold = 0.5
        if calibration_mask.sum() and label_frame.loc[calibration_mask, hazard].sum() > 0:
            calibration_probability = fit_model.predict(xgb.DMatrix(X_norm[calibration_mask]))
            calibration_y = label_frame.loc[calibration_mask, hazard].to_numpy(dtype=np.float32)
            candidates = np.linspace(0.05, 0.95, 181)
            scores = [
                _positive_report(
                    calibration_y, (calibration_probability >= candidate).astype(int)
                )[1].get("f1-score", 0.0)
                for candidate in candidates
            ]
            threshold = float(candidates[int(np.argmax(scores))])
        model = xgb.train(params, xgb.DMatrix(X_norm[train_mask], label=y_train),
                          num_boost_round=96, verbose_eval=False)
        probability = model.predict(xgb.DMatrix(X_norm[test_mask]))
        prediction = (probability >= threshold).astype(int)
        report, positive_report = _positive_report(y_test, prediction)
        metrics[hazard] = {
            "status": "TRAINED",
            "label_source": label_sources[hazard],
            "train_labeled_rows": int(train_mask.sum()),
            "test_labeled_rows": int(test_mask.sum()),
            "train_positive": int(y_train.sum()),
            "test_positive": int(y_test.sum()),
            "precision": float(positive_report.get("precision", 0.0)),
            "recall": float(positive_report.get("recall", 0.0)),
            "f1": float(positive_report.get("f1-score", 0.0)),
            "pr_auc": float(average_precision_score(y_test, probability)),
            "brier": float(brier_score_loss(y_test, probability)),
            "threshold": threshold,
            "threshold_source": "latest_20_percent_of_training_partition",
        }
        model.save_model(os.path.join(output_dir, f"xgboost_{hazard}.json"))

    with open(os.path.join(output_dir, "normalization.json"), "w") as handle:
        json.dump({"mean": mean.tolist(), "std": std.tolist(), "feature_names": feature_names}, handle, indent=2)
    with open(os.path.join(output_dir, "metrics.json"), "w") as handle:
        json.dump({
            "feature_rows": int(len(features)), "feature_count": len(feature_names),
            "split_strategy": "geo-temporal", "cutoff_utc": cutoff.isoformat(),
            "train_rows": int(train_rows.sum()), "test_rows": int(test_rows.sum()),
            "train_locations": sorted(set(locations) - set(holdout_locations)),
            "holdout_locations": holdout_locations, "hazards": metrics,
            "unknown_labels_excluded": True,
        }, handle, indent=2)
    print(json.dumps(metrics, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--identifiers", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--verified-labels")
    parser.add_argument("--verified-hazard", choices=HAZARDS)
    parser.add_argument("--holdout-fraction", type=float, default=0.2)
    parser.add_argument("--test-fraction", type=float, default=0.2)
    args = parser.parse_args()
    train(
        features_path=args.features, labels_path=args.labels,
        identifiers_path=args.identifiers, output_dir=args.output,
        verified_labels_path=args.verified_labels,
        verified_hazard=args.verified_hazard,
        holdout_fraction=args.holdout_fraction,
        test_fraction=args.test_fraction,
    )


if __name__ == "__main__":
    main()

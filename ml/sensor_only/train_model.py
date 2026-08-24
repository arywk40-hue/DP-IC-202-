"""Train a compact INDRA sensor-only XGBoost integration baseline.

The trainer uses earlier rows from non-held-out locations for fitting, later
rows from those locations for threshold calibration, and complete held-out
locations for testing. Weak inherited labels require an explicit opt-in and
can never produce deployment-ready INDRA metrics.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
)

from ml.sensor_only.prepare_dataset import FEATURE_NAMES, HAZARDS, SCHEMA_VERSION


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


def build_split(
    identifiers: pd.DataFrame,
    holdout_fraction: float,
    validation_fraction: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    required = {"location_name", "last_updated"}
    missing = required - set(identifiers.columns)
    if missing:
        raise ValueError(f"identifiers.csv is missing: {sorted(missing)}")
    if not 0.0 < holdout_fraction < 1.0 or not 0.0 < validation_fraction < 1.0:
        raise ValueError("split fractions must be between 0 and 1")

    timestamps = pd.to_datetime(identifiers["last_updated"], utc=True, errors="coerce")
    if timestamps.isna().any():
        raise ValueError("identifiers.csv contains invalid last_updated values")
    locations = sorted(identifiers["location_name"].dropna().unique())
    if len(locations) < 3:
        raise ValueError("at least three locations are required for a geographic holdout")

    n_holdout = max(1, int(np.ceil(len(locations) * holdout_fraction)))
    if n_holdout >= len(locations):
        raise ValueError("holdout_fraction leaves no development locations")
    holdout_locations = locations[-n_holdout:]
    test_mask = identifiers["location_name"].isin(holdout_locations).to_numpy()
    development_mask = ~test_mask
    cutoff = timestamps[development_mask].quantile(1.0 - validation_fraction)
    train_mask = development_mask & (timestamps < cutoff).to_numpy()
    validation_mask = development_mask & (timestamps >= cutoff).to_numpy()
    if not train_mask.any() or not validation_mask.any() or not test_mask.any():
        raise ValueError("split produced an empty train, validation, or test set")

    manifest = {
        "strategy": "temporal-validation-and-complete-location-test",
        "holdout_fraction": holdout_fraction,
        "validation_fraction": validation_fraction,
        "validation_cutoff_utc": str(cutoff),
        "development_locations": sorted(set(locations) - set(holdout_locations)),
        "holdout_locations": holdout_locations,
        "train_rows": int(train_mask.sum()),
        "validation_rows": int(validation_mask.sum()),
        "test_rows": int(test_mask.sum()),
    }
    return train_mask, validation_mask, test_mask, manifest


def _choose_threshold(labels: np.ndarray, probabilities: np.ndarray) -> float:
    candidates = np.linspace(0.05, 0.95, 91)
    scores = [
        f1_score(labels, probabilities >= threshold, zero_division=0)
        for threshold in candidates
    ]
    return float(candidates[int(np.argmax(scores))])


def _metrics(labels: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict:
    predictions = probabilities >= threshold
    result = {
        "threshold": threshold,
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "brier_score": float(brier_score_loss(labels, probabilities)),
        "positive_count": int(labels.sum()),
        "row_count": int(len(labels)),
    }
    result["pr_auc"] = (
        float(average_precision_score(labels, probabilities))
        if np.unique(labels).size == 2
        else None
    )
    return result


def train(
    data_dir: Path,
    output_dir: Path,
    allow_weak_labels: bool = False,
    holdout_fraction: float = 0.2,
    validation_fraction: float = 0.2,
    num_boost_round: int = 16,
) -> dict:
    metadata = json.loads((data_dir / "metadata.json").read_text())
    if metadata.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Expected schema {SCHEMA_VERSION}, got {metadata.get('schema_version')}")
    weak_labels = metadata.get("label_provenance", "").startswith("legacy_weak")
    if weak_labels and not allow_weak_labels:
        raise ValueError(
            "Dataset uses weak labels with synthetic dependencies. Pass "
            "--allow-weak-labels only to create an integration baseline."
        )
    if num_boost_round < 1 or num_boost_round > 16:
        raise ValueError("num_boost_round must be between 1 and the ESP limit of 16")

    features = pd.read_csv(data_dir / "features.csv")
    labels = pd.read_csv(data_dir / "labels.csv")
    identifiers = pd.read_csv(data_dir / "identifiers.csv")
    if features.columns.tolist() != FEATURE_NAMES:
        raise ValueError("features.csv does not exactly match indra_sensor_only_v1 ordering")
    if labels.columns.tolist() != HAZARDS:
        raise ValueError(f"labels.csv must contain exactly {HAZARDS}")
    if not (len(features) == len(labels) == len(identifiers)):
        raise ValueError("features, labels, and identifiers are not aligned")
    if not labels.isin([0, 1]).all().all():
        raise ValueError("all labels must be binary 0/1 values")

    train_mask, validation_mask, test_mask, split_manifest = build_split(
        identifiers, holdout_fraction, validation_fraction
    )
    matrix = features.to_numpy(dtype=np.float32)
    targets = labels.to_numpy(dtype=np.int8)
    mean = matrix[train_mask].mean(axis=0)
    std = matrix[train_mask].std(axis=0)
    std[std == 0] = 1.0
    normalized = (matrix - mean) / std

    import xgboost as xgb

    output_dir.mkdir(parents=True, exist_ok=True)
    all_metrics = {}
    thresholds = {}
    ready_heads = []
    blocked_heads = []
    for index, hazard in enumerate(HAZARDS):
        y_train = targets[train_mask, index]
        y_validation = targets[validation_mask, index]
        y_test = targets[test_mask, index]
        if any(np.unique(values).size < 2 for values in (y_train, y_validation, y_test)):
            blocked_heads.append(hazard)
            all_metrics[hazard] = {
                "status": "NOT_READY",
                "reason": "train, validation, and test must each contain both classes",
                "train_positive": int(y_train.sum()),
                "validation_positive": int(y_validation.sum()),
                "test_positive": int(y_test.sum()),
            }
            continue

        positives = y_train.sum()
        negatives = len(y_train) - positives
        params = dict(PARAMS, scale_pos_weight=float(negatives / positives))
        model = xgb.train(
            params,
            xgb.DMatrix(normalized[train_mask], label=y_train, feature_names=FEATURE_NAMES),
            num_boost_round=num_boost_round,
            verbose_eval=False,
        )
        validation_probabilities = model.predict(
            xgb.DMatrix(normalized[validation_mask], feature_names=FEATURE_NAMES)
        )
        threshold = _choose_threshold(y_validation, validation_probabilities)
        test_probabilities = model.predict(
            xgb.DMatrix(normalized[test_mask], feature_names=FEATURE_NAMES)
        )
        all_metrics[hazard] = {
            "status": "INTEGRATION_BASELINE_ONLY" if weak_labels else "RESEARCH_CANDIDATE",
            "validation": _metrics(y_validation, validation_probabilities, threshold),
            "geographic_test": _metrics(y_test, test_probabilities, threshold),
            "train_positive": int(y_train.sum()),
            "num_trees": num_boost_round,
        }
        thresholds[hazard] = threshold
        ready_heads.append(hazard)
        model.save_model(output_dir / f"xgboost_{hazard}.json")

    normalization = {
        "mean": mean.tolist(),
        "std": std.tolist(),
        "feature_names": FEATURE_NAMES,
        "schema_version": SCHEMA_VERSION,
        "schema_sha256": metadata["schema_sha256"],
    }
    (output_dir / "normalization.json").write_text(json.dumps(normalization, indent=2) + "\n")
    (output_dir / "feature_names.json").write_text(json.dumps(FEATURE_NAMES, indent=2) + "\n")
    (output_dir / "thresholds.json").write_text(json.dumps(thresholds, indent=2) + "\n")
    (output_dir / "metrics.json").write_text(json.dumps(all_metrics, indent=2) + "\n")
    (output_dir / "split.json").write_text(json.dumps(split_manifest, indent=2) + "\n")

    deployment_status = (
        "NOT_READY"
        if weak_labels or blocked_heads or len(ready_heads) != len(HAZARDS)
        else "RESEARCH_CANDIDATE"
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "schema_sha256": metadata["schema_sha256"],
        "label_provenance": metadata.get("label_provenance"),
        "metric_scope": metadata.get("metric_scope"),
        "deployment_status": deployment_status,
        "ready_heads": ready_heads,
        "blocked_heads": blocked_heads,
        "num_trees_per_ready_head": num_boost_round,
        "warning": "Weak-label results are not valid INDRA sensor-only metrics"
        if weak_labels
        else None,
    }
    (output_dir / "model_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-weak-labels", action="store_true")
    parser.add_argument("--holdout-fraction", type=float, default=0.2)
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--num-boost-round", type=int, default=16)
    args = parser.parse_args()
    manifest = train(
        args.data,
        args.output,
        args.allow_weak_labels,
        args.holdout_fraction,
        args.validation_fraction,
        args.num_boost_round,
    )
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["ready_heads"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


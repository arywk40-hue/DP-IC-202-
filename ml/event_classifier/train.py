"""Distill twelve sensor-derived event rules into compact classifiers."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
import xgboost as xgb
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

from ml.six_sensor_forecast.data import SCHEMA as SOURCE_SCHEMA, sha256
from ml.event_classifier.features import (
    ALL_EVENT_FEATURE_COLS,
    EVENT_NAMES,
    apply_event_labels,
    build_features,
    split_masks,
)

EVENT_SCHEMA = "indra_event_rules_v1"


def _class_weight(y: np.ndarray) -> float:
    pos = y.sum()
    neg = len(y) - pos
    return float(neg / max(pos, 1))


def _binary_metrics(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    y_pred = (y_prob >= 0.5).astype(int)
    try:
        auc = float(roc_auc_score(y_true, y_prob))
        if not np.isfinite(auc):
            auc = None
    except ValueError:
        auc = None
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())
    return {
        "auc_roc": auc,
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "positives_in_split": int(y_true.sum()),
    }


def train(
    data: Path,
    output: Path,
    validation_start: str = "2016-01-01T00:00:00Z",
    test_start: str = "2016-07-01T00:00:00Z",
    holdout_locations: list[str] | None = None,
    rounds: int = 16,
    threads: int = 4,
    seed: int = 42,
) -> dict:
    if rounds < 1 or threads < 1:
        raise ValueError("rounds and threads must be positive")

    holdout_locations = holdout_locations or ["Changping", "Dingling", "Huairou"]
    source = json.loads((data / "dataset_manifest.json").read_text())
    if source.get("schema_version") != SOURCE_SCHEMA:
        raise ValueError("Wrong source schema")
    if sha256(data / "observations.csv") != source["observations_sha256"]:
        raise ValueError("Observation checksum does not match source manifest")

    frame, features_df = build_features(pd.read_csv(data / "observations.csv"))
    frame_labeled = apply_event_labels(features_df)

    partitions = split_masks(
        frame, validation_start, test_start, holdout_locations
    )

    output.mkdir(parents=True, exist_ok=True)
    (output / "esp32_student").mkdir(exist_ok=True)

    report = {
        "schema_version": EVENT_SCHEMA,
        "task": "multi-label classification of deterministic sensor-derived rules",
        "label_provenance": "Rules computed from six sensor channels; no independent observed hazard labels",
        "source": source,
        "event_names": EVENT_NAMES,
        "input_features": ALL_EVENT_FEATURE_COLS,
        "n_features": len(ALL_EVENT_FEATURE_COLS),
        "n_events": len(EVENT_NAMES),
        "split": {
            "strategy": "fixed future blocks and complete held-out stations",
            "validation_start": validation_start,
            "test_start": test_start,
            "holdout_locations": holdout_locations,
            "raw_rows": {name: int(mask.sum()) for name, mask in partitions.items()},
        },
        "architecture": {
            "type": "one-vs-rest binary XGBoost",
            "max_trees": rounds,
            "max_depth": 4,
            "objective": "binary:logistic",
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "xgboost": xgb.__version__,
            "sklearn": sklearn.__version__,
        },
        "training": {
            "student_trees": rounds,
            "student_depth": 4,
            "threads": threads,
            "seed": seed,
        },
        "models": {},
    }

    # Require complete inputs
    current_ok = np.isfinite(features_df[ALL_EVENT_FEATURE_COLS].to_numpy()).all(axis=1)

    for event in EVENT_NAMES:
        print(f"Training {event}...", flush=True)
        truth = frame_labeled[event].to_numpy()
        usable = current_ok & np.isfinite(truth)
        masks = {name: mask & usable for name, mask in partitions.items()}

        train_mask = masks["train"]
        val_mask = masks["validation"]

        positives = int(truth[train_mask].sum())
        if train_mask.sum() < 10 or positives == 0:
            reason = "insufficient_data" if train_mask.sum() < 10 else "no_positive_training_labels"
            print(f"Skipping {event}: {reason}")
            report["models"][event] = {
                "skipped": True, "reason": reason,
                "train_rows": int(train_mask.sum()), "train_positives": positives,
            }
            continue

        spw = _class_weight(truth[train_mask])

        dtrain = xgb.DMatrix(
            features_df.loc[train_mask, ALL_EVENT_FEATURE_COLS],
            label=truth[train_mask],
            feature_names=ALL_EVENT_FEATURE_COLS,
        )
        dval = xgb.DMatrix(
            features_df.loc[val_mask, ALL_EVENT_FEATURE_COLS],
            label=truth[val_mask],
            feature_names=ALL_EVENT_FEATURE_COLS,
        )

        params = {
            "objective": "binary:logistic",
            "eval_metric": "aucpr",
            "tree_method": "hist",
            "eta": 0.05,
            "max_depth": 4,
            "min_child_weight": 10,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "lambda": 3.0,
            "scale_pos_weight": spw,
            "seed": seed,
            "nthread": threads,
        }

        model = xgb.train(
            params,
            dtrain,
            num_boost_round=rounds,
            evals=[(dval, "val")],
            verbose_eval=False,
        )

        student_file = f"esp32_student/{event}.ubj"
        model.save_model(output / student_file)

        entry = {
            "student_file": student_file,
            "student_sha256": sha256(output / student_file),
            "student_trees": model.num_boosted_rounds(),
            "student_depth": 4,
            "scale_pos_weight": spw,
            "train_rows": int(train_mask.sum()),
            "train_positives": positives,
            "metrics": {},
        }

        for name, mask in masks.items():
            if mask.sum() == 0:
                continue
            dtest = xgb.DMatrix(
                features_df.loc[mask, ALL_EVENT_FEATURE_COLS],
                feature_names=ALL_EVENT_FEATURE_COLS,
            )
            prob = model.predict(dtest)
            entry["metrics"][name] = _binary_metrics(truth[mask], prob)

        report["models"][event] = entry

    (output / "event_training_report.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data", type=Path, default=Path("data/uci_beijing_air_quality")
    )
    parser.add_argument("--output", type=Path, default=Path("ml/models/uci_beijing_event_rules_6sensor"))
    parser.add_argument("--validation-start", default="2016-01-01T00:00:00Z")
    parser.add_argument("--test-start", default="2016-07-01T00:00:00Z")
    parser.add_argument(
        "--holdout-locations", nargs="+", default=["Changping", "Dingling", "Huairou"]
    )
    parser.add_argument("--rounds", type=int, default=16)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    train(
        args.data,
        args.output,
        args.validation_start,
        args.test_start,
        args.holdout_locations,
        args.rounds,
        args.threads,
    )


if __name__ == "__main__":
    main()

"""Train temporal residual teachers and compact six-input forecast students."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.data import SCHEMA, sha256
from ml.six_sensor_forecast.features import build_features, future_targets, split_masks


def bounded(values: np.ndarray, target: str) -> np.ndarray:
    return np.clip(values, *PHYSICAL_RANGES[target])


def scores(truth: np.ndarray, prediction: np.ndarray) -> dict:
    return {
        "rows": len(truth),
        "mae": float(mean_absolute_error(truth, prediction)),
        "rmse": float(np.sqrt(mean_squared_error(truth, prediction))),
        "r2": float(r2_score(truth, prediction)),
    }


def choose_weight(
    truth: np.ndarray, current: np.ndarray, residual: np.ndarray, target: str
) -> float:
    weights = (0.0, 0.25, 0.5, 0.75, 1.0)
    return min(
        weights,
        key=lambda w: mean_absolute_error(
            truth, bounded(current + w * residual, target)
        ),
    )


def train(
    data: Path,
    output: Path,
    horizon_hours: int = 6,
    validation_start: str = "2016-01-01T00:00:00Z",
    test_start: str = "2016-07-01T00:00:00Z",
    holdout_locations: list[str] | None = None,
    rounds: int = 250,
    threads: int = 4,
    seed: int = 42,
) -> dict:
    if rounds < 1 or threads < 1:
        raise ValueError("rounds and threads must be positive")
    holdout_locations = holdout_locations or ["Changping", "Dingling", "Huairou"]
    source = json.loads((data / "dataset_manifest.json").read_text())
    if source.get("schema_version") != SCHEMA:
        raise ValueError("Wrong source schema")
    if sha256(data / "observations.csv") != source["observations_sha256"]:
        raise ValueError("Observation checksum does not match source manifest")
    frame, features = build_features(pd.read_csv(data / "observations.csv"))
    labels = future_targets(frame, horizon_hours)
    partitions = split_masks(
        frame, horizon_hours, validation_start, test_start, holdout_locations
    )
    # All six current readings required for the compact student's contract.
    # Temporal teacher histories may contain NaN, handled by XGBoost branches.
    current_ok = np.isfinite(frame[RAW_SENSOR_COLUMNS].to_numpy()).all(axis=1)
    output.mkdir(parents=True, exist_ok=True)
    (output / "teacher").mkdir(exist_ok=True)
    (output / "esp32_student").mkdir(exist_ok=True)
    report = {
        "schema_version": SCHEMA,
        "task": "six-sensor exact-future measurement regression",
        "horizon_hours": horizon_hours,
        "deployment_status": "OFFLINE_RESEARCH_ONLY",
        "hazard_detection_status": "NOT_VALIDATED",
        "source": source,
        "architecture": {
            "teacher": "per-target residual XGBoost; causal lags, trailing means/stds; validation depth selection and early stopping",
            "student": "per-target 16-tree depth-3 XGBoost; equal mix of observed and teacher residuals on training rows",
            "prediction": "physical_clip(current + validation_selected_weight * residual)",
            "teacher_features": features.columns.tolist(),
            "student_features": RAW_SENSOR_COLUMNS,
            "station_time_gps_as_features": False,
            "missing_policy": "no imputation; require six finite current inputs and observed future target; teacher allows missing historical features",
        },
        "split": {
            "strategy": "fixed future blocks and complete held-out stations; label horizon purged at boundaries",
            "validation_start": validation_start,
            "test_start": test_start,
            "holdout_locations": holdout_locations,
            "raw_rows": {name: int(mask.sum()) for name, mask in partitions.items()},
            "unused_rows": int(
                (~np.logical_or.reduce(list(partitions.values()))).sum()
            ),
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "xgboost": xgb.__version__,
            "sklearn": sklearn.__version__,
        },
        "training": {
            "seed": seed,
            "threads": threads,
            "max_rounds": rounds,
            "teacher_depth_candidates": [4, 6],
            "early_stopping_rounds": 25,
        },
        "models": {},
    }
    for target in RAW_SENSOR_COLUMNS:
        print(f"Training {target}...", flush=True)
        current = frame[target].to_numpy(dtype=np.float32)
        truth = labels[target].to_numpy()
        usable = current_ok & np.isfinite(truth)
        masks = {name: mask & usable for name, mask in partitions.items()}
        if any(mask.sum() < 2 for mask in masks.values()):
            raise ValueError(f"Insufficient observed labels for {target}")
        train_mask, val_mask = masks["train"], masks["validation"]
        residual = truth - current
        dtrain = xgb.DMatrix(features.loc[train_mask], label=residual[train_mask])
        dval = xgb.DMatrix(features.loc[val_mask], label=residual[val_mask])
        params = {
            "objective": "reg:squarederror",
            "eval_metric": "mae",
            "tree_method": "hist",
            "eta": 0.05,
            "min_child_weight": 20,
            "subsample": 0.85,
            "colsample_bytree": 0.9,
            "lambda": 5,
            "seed": seed,
            "nthread": threads,
        }
        candidates = []
        best = None
        for depth in (4, 6):
            model = xgb.train(
                dict(params, max_depth=depth),
                dtrain,
                num_boost_round=rounds,
                evals=[(dval, "validation")],
                early_stopping_rounds=25,
                verbose_eval=False,
            )
            model = model[: model.best_iteration + 1]
            val_residual = model.predict(dval)
            weight = choose_weight(
                truth[val_mask], current[val_mask], val_residual, target
            )
            mae = float(
                mean_absolute_error(
                    truth[val_mask],
                    bounded(current[val_mask] + weight * val_residual, target),
                )
            )
            candidates.append(
                {
                    "depth": depth,
                    "trees": model.num_boosted_rounds(),
                    "validation_mae": mae,
                    "persistence_blend_weight": weight,
                }
            )
            if best is None or mae < best[0]:
                best = (mae, model, weight, depth)
        _, teacher, teacher_weight, selected_depth = best
        teacher_file = f"teacher/{target}.ubj"
        teacher.save_model(output / teacher_file)
        # Neither validation nor test labels are used in student fitting.
        teacher_train_residual = teacher_weight * teacher.predict(dtrain)
        student_target = 0.5 * residual[train_mask] + 0.5 * teacher_train_residual
        student = xgb.train(
            dict(params, max_depth=3, eta=0.2),
            xgb.DMatrix(
                frame.loc[train_mask, RAW_SENSOR_COLUMNS].astype(np.float32),
                label=student_target,
            ),
            num_boost_round=16,
        )
        student_val = student.predict(
            xgb.DMatrix(frame.loc[val_mask, RAW_SENSOR_COLUMNS].astype(np.float32))
        )
        student_weight = choose_weight(
            truth[val_mask], current[val_mask], student_val, target
        )
        student_file = f"esp32_student/{target}.ubj"
        student.save_model(output / student_file)
        entry = {
            "teacher_file": teacher_file,
            "student_file": student_file,
            "teacher_sha256": sha256(output / teacher_file),
            "student_sha256": sha256(output / student_file),
            "teacher_weight": teacher_weight,
            "student_weight": student_weight,
            "teacher_depth": selected_depth,
            "teacher_trees": teacher.num_boosted_rounds(),
            "student_depth": 3,
            "student_trees": 16,
            "candidates": candidates,
            "metrics": {},
        }
        for name, mask in masks.items():
            if name == "train":
                entry["train_rows"] = int(mask.sum())
                continue
            baseline = current[mask]
            teacher_pred = bounded(
                baseline
                + teacher_weight * teacher.predict(xgb.DMatrix(features.loc[mask])),
                target,
            )
            student_pred = bounded(
                baseline
                + student_weight
                * student.predict(
                    xgb.DMatrix(frame.loc[mask, RAW_SENSOR_COLUMNS].astype(np.float32))
                ),
                target,
            )
            entry["metrics"][name] = {
                "persistence": scores(truth[mask], baseline),
                "teacher": scores(truth[mask], teacher_pred),
                "student": scores(truth[mask], student_pred),
            }
            if name == "validation":
                # Empirical validation residual band; coverage under shift is measured,
                # not assumed to be a calibrated guarantee.
                entry["teacher_absolute_error_p90"] = float(
                    np.quantile(np.abs(truth[mask] - teacher_pred), 0.9)
                )
                entry["student_absolute_error_p90"] = float(
                    np.quantile(np.abs(truth[mask] - student_pred), 0.9)
                )
            else:
                for kind, prediction in (
                    ("teacher", teacher_pred),
                    ("student", student_pred),
                ):
                    metric = entry["metrics"][name][kind]
                    baseline_mae = entry["metrics"][name]["persistence"]["mae"]
                    metric["mae_skill_vs_persistence"] = (
                        1 - metric["mae"] / baseline_mae if baseline_mae else None
                    )
                    metric["validation_p90_band_coverage"] = float(
                        np.mean(
                            np.abs(truth[mask] - prediction)
                            <= entry[f"{kind}_absolute_error_p90"]
                        )
                    )
        report["models"][target] = entry
        (output / "training_report.json").write_text(
            json.dumps(report, indent=2, allow_nan=False) + "\n"
        )
        print(
            f"  future MAE: {entry['metrics']['future_test']['teacher']['mae']:.3f}; "
            f"persistence: {entry['metrics']['future_test']['persistence']['mae']:.3f}",
            flush=True,
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data", type=Path, default=Path("data/uci_beijing_air_quality")
    )
    parser.add_argument("--output", type=Path, default=Path("ml/models/uci_beijing_6h"))
    parser.add_argument("--horizon-hours", type=int, default=6)
    parser.add_argument("--validation-start", default="2016-01-01T00:00:00Z")
    parser.add_argument("--test-start", default="2016-07-01T00:00:00Z")
    parser.add_argument(
        "--holdout-locations", nargs="+", default=["Changping", "Dingling", "Huairou"]
    )
    parser.add_argument("--rounds", type=int, default=250)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    train(
        args.data,
        args.output,
        args.horizon_hours,
        args.validation_start,
        args.test_start,
        args.holdout_locations,
        args.rounds,
        args.threads,
    )


if __name__ == "__main__":
    main()

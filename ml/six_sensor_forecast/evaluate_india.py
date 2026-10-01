"""Paired Indian holdout evaluation with matched sensor-profile baselines."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.data import sha256
from ml.six_sensor_forecast.features import build_features, future_targets, split_masks
from ml.six_sensor_forecast.train import bounded, scores

PROFILES = {
    "five_sensor": ("india_cpcb_5sensor_6h", "uci_beijing_5sensor_6h"),
    "pm_only": ("india_cpcb_pm_6h", "uci_beijing_pm_6h"),
}


def load_model(root: Path, report: dict, target: str, kind: str) -> xgb.Booster:
    entry = report["models"][target]
    path = root / entry[f"{kind}_file"]
    if sha256(path) != entry[f"{kind}_sha256"]:
        raise ValueError(f"Model checksum mismatch: {path}")
    model = xgb.Booster()
    model.load_model(path)
    return model


def evaluate(data: Path, models: Path, output: Path) -> dict:
    manifest = json.loads((data / "dataset_manifest.json").read_text())
    if sha256(data / "observations.csv") != manifest["observations_sha256"]:
        raise ValueError("Indian observations changed")
    frame, temporal = build_features(pd.read_csv(data / "observations.csv"))
    truth = future_targets(frame, 6)
    original_dir = models / "uci_beijing_6h"
    original = json.loads((original_dir / "training_report.json").read_text())
    report = {
        "task": "6-hour Indian station measurement forecasting",
        "status": "RESEARCH_WITH_DOCUMENTED_SOURCE_ASSUMPTIONS",
        "dataset_manifest": manifest,
        "original_six_input_model_complete_input_rows": int(
            np.isfinite(frame[RAW_SENSOR_COLUMNS]).all(axis=1).sum()
        ),
        "original_model_test_interpretation": "The unchanged six-input model has no fully observed input rows here. Its NaN stress test is diagnostic and outside the deployed complete-input contract; matched-profile Beijing models are the fair transfer baselines.",
        "holdout_policy": "Dates and Baddi station reserved before fitting; no model selection on these evaluation scores",
        "profiles": {},
    }
    for profile, (india_name, beijing_name) in PROFILES.items():
        india_dir, beijing_dir = models / india_name, models / beijing_name
        india = json.loads((india_dir / "training_report.json").read_text())
        beijing = json.loads((beijing_dir / "training_report.json").read_text())
        if india["source"]["observations_sha256"] != manifest["observations_sha256"]:
            raise ValueError("Indian model evaluated against a different source")
        sensors = india["sensor_profile"]
        if sensors != beijing["sensor_profile"]:
            raise ValueError("Paired models must have identical sensor profiles")
        split = india["split"]
        masks = split_masks(
            frame,
            6,
            split["validation_start"],
            split["test_start"],
            split["holdout_locations"],
        )
        common_input = np.isfinite(frame[sensors]).all(axis=1).to_numpy()
        entry = {
            "sensors": sensors,
            "india_model": india_name,
            "beijing_model": beijing_name,
            "india_report_sha256": sha256(india_dir / "training_report.json"),
            "beijing_report_sha256": sha256(beijing_dir / "training_report.json"),
            "original_report_sha256": sha256(original_dir / "training_report.json"),
            "split": split,
            "targets": {},
        }
        for target in sensors:
            target_results = {}
            boosters = {}
            for prefix, directory, metadata in (
                ("india", india_dir, india),
                ("beijing_matched", beijing_dir, beijing),
                ("original_six_input_nan_stress", original_dir, original),
            ):
                for kind in ("teacher", "student"):
                    boosters[f"{prefix}_{kind}"] = (
                        load_model(directory, metadata, target, kind),
                        metadata,
                        kind,
                    )
            for split_name in ("future_test", "geographic_test"):
                eligible = (
                    common_input
                    & np.isfinite(truth[target].to_numpy())
                    & masks[split_name]
                )
                groups = {"pooled": eligible}
                for station in sorted(frame.loc[eligible, "location_id"].unique()):
                    groups[station] = (
                        eligible & frame.location_id.eq(station).to_numpy()
                    )
                split_results = {}
                for group, mask in groups.items():
                    if mask.sum() < 2:
                        continue
                    y = truth.loc[mask, target].to_numpy()
                    current = frame.loc[mask, target].to_numpy(dtype=np.float32)
                    metrics = {"persistence": scores(y, current)}
                    for name, (booster, metadata, kind) in boosters.items():
                        names = metadata["architecture"][f"{kind}_features"]
                        features = (
                            temporal.loc[mask, names]
                            if kind == "teacher"
                            else frame.loc[mask, names].astype(np.float32)
                        )
                        prediction = bounded(
                            current
                            + metadata["models"][target][f"{kind}_weight"]
                            * booster.predict(
                                xgb.DMatrix(
                                    features, feature_names=features.columns.tolist()
                                )
                            ),
                            target,
                        )
                        metrics[name] = scores(y, prediction)
                        baseline = metrics["persistence"]["mae"]
                        metrics[name]["mae_skill_vs_persistence"] = (
                            1 - metrics[name]["mae"] / baseline if baseline else None
                        )
                    metrics["india_student"]["mae_skill_vs_beijing_matched_student"] = (
                        1
                        - metrics["india_student"]["mae"]
                        / metrics["beijing_matched_student"]["mae"]
                        if metrics["beijing_matched_student"]["mae"]
                        else None
                    )
                    split_results[group] = metrics
                target_results[split_name] = split_results
            entry["targets"][target] = target_results
        report["profiles"][profile] = entry
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/india_cpcb_research"))
    parser.add_argument("--models", type=Path, default=Path("ml/models"))
    parser.add_argument(
        "--output", type=Path, default=Path("ml/evaluation/india_transfer_report.json")
    )
    args = parser.parse_args()
    evaluate(args.data, args.models, args.output)
    print(f"Saved paired Indian evaluation to {args.output}")


if __name__ == "__main__":
    main()

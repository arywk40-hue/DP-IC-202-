"""Audit actual saved predictions and later API values without updating weights."""

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from ml.himachal.contracts import METADATA, snapshot
from ml.india_mandi.live import atomic_json
from ml.india_mandi.online import encode, for_model
from ml.india_mandi.registry import load_forecaster
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS


def audit(state, history):
    """Read one source namespace consistently and verify prediction/label timing."""
    records = [snapshot(r) for r in json.loads(Path(history).read_text())]
    if not records:
        raise ValueError("Collected source history required")
    identities = [
        {
            k: r[k]
            for k in METADATA
            if k not in {"timestamp_utc", "valid_time_utc", "available_at_utc"}
        }
        for r in records
    ]
    namespaces = {
        "live:" + hashlib.sha256(encode(i).encode()).hexdigest()[:32]
        for i in identities
    }
    if len(namespaces) != 1 or any(
        r["source_class"] != "modeled_grid" for r in records
    ):
        raise ValueError("Exactly one collected model-grid source required")
    ns = namespaces.pop()
    with sqlite3.connect(f"file:{Path(state).resolve()}?mode=ro", uri=True) as db:
        db.execute("BEGIN")
        rows = db.execute(
            "SELECT f.issue,f.target,f.issued_at,f.revision,f.base,f.shadow,f.truth,f.learned_at,o.available,o.measurements,i.measurements FROM forecasts f JOIN observations o ON f.namespace=o.namespace AND f.target=o.time JOIN observations i ON f.namespace=i.namespace AND f.issue=i.time WHERE f.namespace=? AND f.scored=1 AND f.eligible=1 ORDER BY f.target",
            (ns,),
        ).fetchall()
        pending = db.execute(
            "SELECT count(*) FROM forecasts WHERE namespace=? AND eligible=1 AND scored=0",
            (ns,),
        ).fetchone()[0]
    comparisons = []
    for (
        issue,
        target,
        issued,
        revision,
        base,
        shadow,
        truth,
        learned,
        available,
        measured,
        original,
    ) in rows:
        if (
            target - issue != 21600
            or not issue <= issued < target <= available <= learned
        ):
            raise ValueError("Prediction-before-truth timing violation")
        truth, base, shadow, measured = [
            np.asarray(json.loads(s), float) for s in [truth, base, shadow, measured]
        ]
        if any(
            a.shape != (6,) or not np.isfinite(a).all()
            for a in [truth, base, shadow, measured]
        ) or not np.array_equal(truth, measured):
            raise ValueError("Saved truth/source contract mismatch")
        stamp = lambda t: pd.Timestamp(t, unit="s", tz="UTC").isoformat()
        comparisons.append(
            {
                "input_valid_utc": stamp(issue),
                "target_valid_utc": stamp(target),
                "issued_at_utc": stamp(issued),
                "truth_available_utc": stamp(available),
                "learned_at_utc": stamp(learned),
                "actual_remaining_lead_minutes": (target - issued) / 60,
                "issued_in_input_hour": issued < issue + 3600,
                "checkpoint_revision_at_prediction": revision,
                "input": dict(zip(RAW_SENSOR_COLUMNS, json.loads(original))),
                "prediction": dict(zip(RAW_SENSOR_COLUMNS, base.tolist())),
                "shadow_prediction": dict(zip(RAW_SENSOR_COLUMNS, shadow.tolist())),
                "later_api_values": dict(zip(RAW_SENSOR_COLUMNS, truth.tolist())),
                "absolute_errors": dict(
                    zip(RAW_SENSOR_COLUMNS, np.abs(base - truth).tolist())
                ),
            }
        )
    engine = load_forecaster()
    return {
        "executed_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "source_class": "modeled_grid",
        "evidence": "PROSPECTIVELY_SAVED_PREDICTIONS_VS_LATER_MODEL_GRID_VALUES_NOT_STATION_TRUTH",
        "namespace": ns,
        "model_id": engine.profile["id"],
        "profile_sha256": engine.profile_sha256,
        "scored_forecasts": len(comparisons),
        "pending_forecasts": pending,
        "scored_issued_in_input_hour": sum(
            r["issued_in_input_hour"] for r in comparisons
        ),
        "scored_delayed_input_forecasts": sum(
            not r["issued_in_input_hour"] for r in comparisons
        ),
        "comparisons": comparisons,
        "online": for_model(state, engine).summary(),
        "field_validated": False,
        "calibrated_event_probabilities": False,
        "weights_promoted": False,
        "conclusion": "Sample is too small to assess improvement; delayed startup predictions are not full six-hour issuance tests.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state", type=Path, default=ROOT / "ml/data/himachal/mandi_v2_online_live.sqlite"
    )
    parser.add_argument(
        "--history",
        type=Path,
        default=ROOT / "ml/data/himachal/mandi_current_api_v1/history.json",
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "ml/reports/mandi_current_api_v1/prospective"
    )
    args = parser.parse_args()
    result = audit(args.state, args.history)
    atomic_json(args.output / "audit.json", result)
    lines = [
        "# Mandi prospective collection progress",
        "",
        f"Checked: {result['executed_at_utc']}",
        "",
        f"Scored forecasts: {result['scored_forecasts']}; pending: {result['pending_forecasts']}.",
        f"Issued in the input hour: {result['scored_issued_in_input_hour']}; delayed startup inputs: {result['scored_delayed_input_forecasts']}.",
        "",
        "The later values are API/model grids, not physical station truth. No six-hour field accuracy or model improvement is established.",
        "",
    ]
    for row in result["comparisons"][-12:]:
        lines += [
            f"## Target {row['target_valid_utc']}",
            "",
            f"Input valid: {row['input_valid_utc']}. Prediction actually saved: {row['issued_at_utc']}.",
            f"Remaining lead at issuance: **{row['actual_remaining_lead_minutes']:.2f} minutes**. Later values first available: {row['truth_available_utc']}.",
            "",
            "| Channel | Input | Saved prediction | Later API value | Absolute error |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        for c in RAW_SENSOR_COLUMNS:
            lines.append(
                f"| {c} | {row['input'][c]:.3f} | {row['prediction'][c]:.3f} | {row['later_api_values'][c]:.3f} | {row['absolute_errors'][c]:.3f} |"
            )
        lines.append("")
    lines += [
        "Predictions were saved before updates. Published offline weights remain unchanged; corrections are learned in shadow mode. All comparisons are retained in audit.json.",
        "",
    ]
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "REPORT.md").write_text("\n".join(lines))
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "scored_forecasts",
                    "pending_forecasts",
                    "scored_issued_in_input_hour",
                    "scored_delayed_input_forecasts",
                    "conclusion",
                ]
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

"""Evaluate the saved six-input student on independent, complete field records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ml.deployment.field_validation import forecast_metrics, utc_times
from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.data import SCHEMA, sha256
from ml.six_sensor_forecast.features import validate_observations
from ml.six_sensor_forecast.predict import predict


def validate_model(model_dir: Path) -> None:
    report = json.loads((model_dir / "training_report.json").read_text())
    if (
        report.get("schema_version") != SCHEMA
        or report.get("horizon_hours") != 6
        or report.get("sensor_profile", RAW_SENSOR_COLUMNS) != RAW_SENSOR_COLUMNS
        or set(report.get("models", {})) != set(RAW_SENSOR_COLUMNS)
        or report.get("architecture", {}).get("student_features") != RAW_SENSOR_COLUMNS
    ):
        raise ValueError(
            "Incompatible forecast model: this evaluator requires a six-hour student "
            "with all six canonical sensor inputs and outputs in the expected order. "
            "Use ml/models/uci_beijing_6h; reduced-input models are unsupported."
        )


def evaluate(
    observations: pd.DataFrame,
    provenance: dict,
    test_start: str,
    model_dir: Path,
) -> dict:
    """Use only observed six-hour pairs at/after a preselected test cutoff."""
    validate_model(model_dir)
    if (
        provenance.get("timezone_verified") is not True
        or provenance.get("units_verified") is not True
        or provenance.get("pressure_reference") != "station"
        or not provenance.get("observation_source")
    ):
        raise ValueError("Document verified source, timezone, units and station pressure")
    if set(observations.columns) != {"timestamp_utc", "location_id", *RAW_SENSOR_COLUMNS}:
        raise ValueError("Supply timestamp_utc, location_id and exactly six sensor columns")
    cutoff = utc_times([test_start])[0]
    observations = observations.copy()
    observations["timestamp_utc"] = utc_times(observations.timestamp_utc)
    for name, (low, high) in PHYSICAL_RANGES.items():
        values = pd.to_numeric(observations[name], errors="raise").to_numpy(dtype=float)
        if not np.isfinite(values).all() or ((values < low) | (values > high)).any():
            raise ValueError(f"Missing, nonfinite or out-of-range {name}; do not invent six-input rows")
    observations = validate_observations(observations)
    forecasts = predict(observations, model_dir, "student")
    metrics = forecast_metrics(observations, forecasts, cutoff)
    paired = metrics["ALL"][RAW_SENSOR_COLUMNS[0]]["pairs"]
    return {
        "status": "EVALUATED_REQUIRES_REVIEW" if paired else "NO_EXACT_SIX_HOUR_TEST_PAIRS",
        "model": str(model_dir),
        "model_report_sha256": sha256(model_dir / "training_report.json"),
        "test_start_utc": cutoff.isoformat(),
        "horizon_hours": 6,
        "observation_rows": len(observations),
        "six_hour_test_pairs": paired,
        "provenance_declaration": provenance,
        "metrics": metrics,
        "field_deployment_approved": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--test-start", required=True)
    parser.add_argument("--model", type=Path, default=Path("ml/models/uci_beijing_6h"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        provenance = json.loads(args.provenance.read_text())
        report = evaluate(pd.read_csv(args.observations), provenance, args.test_start, args.model)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    report["input_sha256"] = {
        str(args.observations): sha256(args.observations),
        str(args.provenance): sha256(args.provenance),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()

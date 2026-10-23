"""Score a new Mandi model-grid snapshot without fitting or changing weights."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from ml.paths import read_config
from ml.india_mandi.benchmark import metric
from ml.india_mandi.live import atomic_json
from ml.india_mandi.tabular_v2 import TabularV2
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.data import sha256
from ml.six_sensor_forecast.features import future_targets


def evaluate(directory, output):
    """Exact +6h comparison against later API values; never station/event truth."""
    directory, output = Path(directory), Path(output)
    manifest = json.loads((directory / "dataset_manifest.json").read_text())
    if sha256(directory / "observations.csv") != manifest["observations_sha256"]:
        raise ValueError("Downloaded source checksum mismatch")
    frame = pd.read_csv(directory / "observations.csv")
    frame["timestamp_utc"] = pd.to_datetime(frame.timestamp_utc, utc=True)
    frame = frame.sort_values(["location_id", "timestamp_utc"]).reset_index(drop=True)
    engine = TabularV2()
    predictions = engine.predict(frame)
    truth = future_targets(frame, 6).to_numpy(float)
    p = predictions[["forecast_" + c for c in RAW_SENSOR_COLUMNS]].to_numpy(float)
    now = frame[RAW_SENSOR_COLUMNS].to_numpy(float)
    ready = (predictions.status == "HYBRID_READY").to_numpy() & np.isfinite(truth).all(
        1
    )
    cfg = read_config(ROOT / "ml/configs/mandi_pipeline_v2.json")
    previous_end = pd.Timestamp(cfg["end_date"], tz="UTC") + pd.Timedelta(hours=23)
    new_date = (predictions.forecast_timestamp_utc > previous_end).to_numpy()
    cohorts = {}
    for name, mask in [
        ("recent_30_days_reused_dates", ready),
        ("targets_after_previous_archive", ready & new_date),
    ]:
        metrics = {}
        if mask.sum() >= 2:
            metrics = {
                c: metric(truth[mask, j], p[mask, j], now[mask, j])
                for j, c in enumerate(RAW_SENSOR_COLUMNS)
            }
        cohorts[name] = {"rows": int(mask.sum()), "metrics": metrics}
    report = {
        "source_evidence": "RETROSPECTIVE_MODEL_GRID_NOT_STATION_ACCURACY",
        "model_id": engine.profile["id"],
        "profile_sha256": engine.profile_sha256,
        "source_manifest": manifest,
        "previous_archive_end": previous_end.isoformat(),
        "cohorts": cohorts,
        "models_retrained": False,
        "weights_selected_on_this_snapshot": False,
        "hazards_evaluated": False,
        "source_revision_warning": "Upstream historical values may differ from earlier snapshots; first cohort reuses previously examined test dates.",
    }
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / "metrics.json", report)
    lines = [
        "# Latest fetched Mandi model-grid test",
        "",
        "Six-hour numerical forecasts against later API model values. No station or hazard accuracy is claimed.",
        "",
        f"Source: {manifest['coverage_start_utc']} to {manifest['coverage_end_utc']}; {manifest['rows']} complete hourly positions.",
        "",
        "No models were fitted, tuned or promoted using this snapshot.",
        "",
    ]
    for name, row in cohorts.items():
        lines += [
            f"## {name} — {row['rows']} pairs",
            "",
            "| Target | Model MAE | Persistence MAE | MAE skill vs persistence |",
            "| --- | ---: | ---: | ---: |",
        ]
        for c, m in row["metrics"].items():
            skill = (
                1 - m["mae"] / m["persistence_mae"] if m["persistence_mae"] else None
            )
            lines.append(
                f"| {c} | {m['mae']:.4f} | {m['persistence_mae']:.4f} | {100 * skill:.1f}% |"
                if skill is not None
                else f"| {c} | {m['mae']:.4f} | {m['persistence_mae']:.4f} | undefined |"
            )
        lines.append("")
    lines += [
        "Targets after the earlier archive end extend the existing test; the full 30-day cohort reuses previously examined dates. Historical API values can be revised. New-date results are small-sample diagnostics, not evidence for automatic retraining.",
        "",
        "MAE uses each channel's native unit. Full RMSE/R² and provenance are in metrics.json.",
        "",
        "Attribution: Open-Meteo, ECMWF IFS, Copernicus CAMS.",
        "",
    ]
    (output / "REPORT.md").write_text("\n".join(lines))
    print(json.dumps(cohorts, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evaluate(args.input, args.output)

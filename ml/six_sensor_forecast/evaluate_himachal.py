"""Offline missing-PM diagnostic of the unchanged six-input ESP32 student.

This intentionally exercises XGBoost's missing-value paths outside the production
complete-input contract. It must never be used to relax the deployment validator.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.data import sha256
from ml.six_sensor_forecast.evaluate_india import load_model
from ml.six_sensor_forecast.train import bounded, scores

FILES = {
    "temperature_c": "6b64941e-8646-4020-b7e8-a8024d86fae2",
    "relative_humidity_pct": "b9377211-44a9-4380-b99a-f40bd4bbdfde",
    "pressure_hpa": "bbb7d941-de74-438c-a19a-bfe9e42a5fad",
    "wind_speed_mps": "22ef7020-904b-4ef8-a975-d6baa5701988",
}


def evaluate(root: Path) -> dict:
    keys = ["Station", "Latitude", "Longitude", "Data Acquisition Time"]
    merged = None
    sources = {}
    for target, uid in FILES.items():
        path = root / "himachal 4-sensor dataset" / f"{uid}.csv"
        raw = pd.read_csv(path)
        value = raw.columns[-1]
        frame = raw[keys + [value]].copy().rename(columns={value: target})
        frame["Data Acquisition Time"] = pd.to_datetime(
            frame["Data Acquisition Time"], format="%d-%m-%Y %H:%M", errors="raise"
        )
        duplicates = frame.duplicated(keys, keep=False)
        frame = frame.loc[~duplicates].copy()
        frame[target] = pd.to_numeric(frame[target], errors="coerce")
        if target == "wind_speed_mps":
            frame[target] /= 3.6
        low, high = PHYSICAL_RANGES[target]
        frame = frame.loc[frame[target].between(low, high)]
        sources[target] = {
            "file": str(path.relative_to(root)),
            "sha256": sha256(path),
            "raw_rows": len(raw),
            "duplicate_rows_excluded": int(duplicates.sum()),
        }
        merged = (
            frame
            if merged is None
            else merged.merge(frame, on=keys, how="inner", validate="one_to_one")
        )
    # All times remain in the original unspecified local frame. A constant UTC
    # offset is unnecessary for an exact six-hour join and a snapshot student.
    future = merged.copy()
    future["Data Acquisition Time"] -= pd.Timedelta(hours=6)
    future = future.rename(columns={t: f"truth_{t}" for t in FILES})
    paired = merged.merge(future, on=keys, how="inner", validate="one_to_one")
    assert not paired.duplicated(keys).any()
    for target in RAW_SENSOR_COLUMNS:
        if target not in paired:
            paired[target] = np.nan
    model_dir = root / "ml/models/uci_beijing_6h"
    metadata = json.loads((model_dir / "training_report.json").read_text())
    assert metadata["horizon_hours"] == 6
    assert metadata["architecture"]["student_features"] == RAW_SENSOR_COLUMNS
    matrix = xgb.DMatrix(paired[RAW_SENSOR_COLUMNS].astype(np.float32))
    for target in FILES:
        model = load_model(model_dir, metadata, target, "student")
        paired[f"prediction_{target}"] = bounded(
            paired[target].to_numpy()
            + metadata["models"][target]["student_weight"] * model.predict(matrix),
            target,
        )

    def metrics(group):
        output = {}
        for target in FILES:
            truth = group[f"truth_{target}"].to_numpy()
            forecast = group[f"prediction_{target}"].to_numpy()
            baseline = group[target].to_numpy()
            if len(group) < 2:
                continue
            m, b = scores(truth, forecast), scores(truth, baseline)
            output[target] = {
                "model": m,
                "persistence": b,
                "mae_skill_pct": 100 * (1 - m["mae"] / b["mae"]) if b["mae"] else None,
            }
        return {"pairs": len(group), "metrics": output}

    # Sensitivity analysis only: these recurring values are suspicious, not
    # officially documented missing-value codes. Do not call this clean truth.
    suspect = [925.0, 1021.5]
    sensitivity = paired.loc[
        ~paired.pressure_hpa.isin(suspect) & ~paired.truth_pressure_hpa.isin(suspect)
    ]
    report = {
        "status": "MISSING_PM_OFFLINE_DIAGNOSTIC_ONLY",
        "model": str(model_dir.relative_to(root)),
        "kind": "student",
        "model_report_sha256": sha256(model_dir / "training_report.json"),
        "horizon_hours": 6,
        "sources": sources,
        "method": "All duplicated keys excluded; broad physical ranges; exact station/coordinate/time joins. No interpolation, fitting, or parameter selection. PM2.5 and PM10 are NaN; XGBoost missing branches are exercised directly.",
        "limitations": [
            "Production inference rejects these inputs; zero complete-six-input forecasts.",
            "Timezone, pressure reference and sensor quality remain unverified.",
            "Scores measure agreement with recorded telemetry, including possible faults.",
            "Pressure sensitivity exclusion is heuristic, not certified data cleaning.",
            "No PM performance or hardware performance is measured.",
        ],
        "four_input_rows": len(merged),
        "complete_six_input_rows": 0,
        "overall": metrics(paired),
        "by_station": {
            station: metrics(group) for station, group in paired.groupby("Station")
        },
        "pressure_sensitivity_excluding_925_and_1021_5_at_both_ends": metrics(
            sensitivity
        ),
    }
    out = root / "data/himachal_weather_audit"
    out.mkdir(parents=True, exist_ok=True)
    (out / "model_diagnostic.json").write_text(
        json.dumps(report, indent=2, allow_nan=False)
    )
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "status",
                    "overall",
                    "pressure_sensitivity_excluding_925_and_1021_5_at_both_ends",
                )
            },
            indent=2,
        )
    )
    print(
        "AWS IIT Mandi:",
        json.dumps(report["by_station"].get("AWS IIT Mandi"), indent=2),
    )
    return report


if __name__ == "__main__":
    evaluate(Path(__file__).resolve().parents[2])

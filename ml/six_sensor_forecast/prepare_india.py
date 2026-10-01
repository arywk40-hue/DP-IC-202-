"""Prepare observed Indian channels, quarantining unresolved pressure and units."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ml.six_sensor_forecast.audit_india import SAMPLES, read_table
from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.data import SCHEMA, sha256

# Explicit units only. 'AT (degree)' and every BP column are excluded.
MAPPING = {
    "temperature_c": ("AT (degree C)", "Temp (degree C)"),
    "relative_humidity_pct": ("RH (%)",),
    "pm25_ug_m3": ("PM2.5 (ug/m3)",),
    "pm10_ug_m3": ("PM10 (ug/m3)",),
    "wind_speed_mps": ("WS (m/s)",),
}


def prepare(source: Path, output: Path) -> dict:
    audit = json.loads((source / "coverage_report.json").read_text())
    source_metadata = json.loads((source / "source_metadata.json").read_text())
    expected = {entry["station_id"]: entry for entry in audit["downloaded_samples"]}
    parts, details = [], []
    for station in SAMPLES:
        path = source / "raw" / (station + ".csv")
        if sha256(path) != expected[station]["sha256"]:
            raise ValueError(f"Source changed since audit: {station}")
        raw = read_table(path)
        start = pd.to_datetime(raw["From Date"], errors="coerce")
        end = pd.to_datetime(raw["To Date"], errors="coerce")
        valid_time = (
            start.notna() & end.notna() & (end - start).eq(pd.Timedelta(hours=1))
        )
        duplicate = end.duplicated(keep=False)
        usable = valid_time & ~duplicate
        timestamps = end.dt.tz_localize("Asia/Kolkata").dt.tz_convert("UTC")
        frame = pd.DataFrame({"location_id": station, "timestamp_utc": timestamps})
        mapped = {}
        for column in RAW_SENSOR_COLUMNS:
            names = [name for name in MAPPING.get(column, ()) if name in raw]
            mapped[column] = names[0] if names else None
            values = (
                pd.to_numeric(raw[names[0]], errors="coerce")
                if names
                else pd.Series(np.nan, index=raw.index)
            )
            low, high = PHYSICAL_RANGES[column]
            frame[column] = values.where(values.between(low, high))
        frame = frame.loc[usable].reset_index(drop=True)
        parts.append(frame)
        details.append(
            {
                "station_id": station,
                "city": expected[station]["city"],
                "state": expected[station]["state"],
                "source_sha256": sha256(path),
                "source_columns": mapped,
                "raw_rows": len(raw),
                "retained_rows": len(frame),
                "invalid_intervals": int((~valid_time).sum()),
                "duplicate_end_rows_excluded": int(duplicate.sum()),
                "finite_rows_by_sensor": frame[RAW_SENSOR_COLUMNS]
                .notna()
                .sum()
                .to_dict(),
            }
        )
    observations = pd.concat(parts, ignore_index=True).sort_values(
        ["location_id", "timestamp_utc"]
    )
    output.mkdir(parents=True, exist_ok=True)
    path = output / "observations.csv"
    observations.to_csv(path, index=False)
    manifest = {
        "schema_version": SCHEMA,
        "source_name": "Indian CPCB secondary compilation, seven-station research subset",
        "source_url": audit["source_url"],
        "source_version": 2,
        "license": source_metadata["licenseName"],
        "rows": len(observations),
        "observations_sha256": sha256(path),
        "stations": details,
        "pressure_policy": "All pressure excluded, including columns labelled mmHg; no pressure target trained",
        "temperature_policy": "Only explicit degree C headers accepted; Dehradun AT (degree) excluded",
        "timestamp_policy": "Assume source local intervals are Asia/Kolkata; UTC timestamp is interval END, when hourly mean becomes available",
        "timestamp_verification": "Timezone is a documented research assumption, not confirmed in provider metadata; no time/calendar predictors",
        "forecast_target": "Observed hourly mean whose interval END is six hours after current interval END",
        "source_alignment_limit": "Indian inputs are hourly interval means; Beijing source describes hourly measurements; aggregation equivalence is not independently verified",
        "missing_policy": "No imputation. Unavailable or physically invalid sensors remain NaN; model profiles select required sensors",
        "geographic_limit": "Seven sampled stations, Baddi held out; no Mandi station or national representativeness claim",
        "status": "RESEARCH_WITH_DOCUMENTED_SOURCE_ASSUMPTIONS",
    }
    (output / "dataset_manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/india_station_audit"))
    parser.add_argument("--output", type=Path, default=Path("data/india_cpcb_research"))
    args = parser.parse_args()
    result = prepare(args.source, args.output)
    print(
        f"Prepared {result['rows']:,} Indian rows; unresolved sensors remain missing."
    )


if __name__ == "__main__":
    main()

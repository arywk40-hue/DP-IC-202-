"""Audit two original Delhi station CSV exports without changing their measurements."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


SOURCES = {
    "jahangirpuri_dpcc": "jahangirpuri_dpcc_2024_2025.csv",
    "crri_mathura_road_imd": "crri_mathura_road_imd_2024_2025.csv",
}
CHANNELS = {
    "temperature_c": "AT (degC)",
    "relative_humidity_pct": "RH (%)",
    "pressure_raw": "BP (mmHg)",
    "pm25_ug_m3": "PM2.5 (ug/m3)",
    "pm10_ug_m3": "PM10 (ug/m3)",
    "wind_speed_mps": "WS (m/s)",
}
SOURCE_URLS = {
    "jahangirpuri_dpcc": "https://data.opencity.in/dataset/delhi-hourly-air-quality-reports/resource/734c459f-3e47-44c7-b0b8-8270090cecf0",
    "crri_mathura_road_imd": "https://data.opencity.in/dataset/delhi-hourly-air-quality-reports/resource/c4ec16f3-edfc-465e-8fb8-5bfaa14f8baa",
}


def audit(directory: Path) -> dict:
    stations = {}
    for station, filename in SOURCES.items():
        path = directory / "raw" / filename
        frame = pd.read_csv(path)
        missing = set(["Station ID", "Station Name", "Timestamp", *CHANNELS.values()]) - set(frame)
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        times = pd.to_datetime(frame["Timestamp"], errors="coerce")
        station_ok = frame["Station ID"].astype(str).str.startswith("site_")
        valid = station_ok & times.notna()
        observations = frame.loc[valid].copy()
        observations["Timestamp"] = times[valid]
        values = observations[list(CHANNELS.values())].apply(pd.to_numeric, errors="coerce")
        complete = values.notna().all(axis=1)
        complete_times = observations.loc[complete, "Timestamp"]
        full_hours = int(complete_times.dt.floor("h").value_counts().eq(4).sum())
        pressure = values[CHANNELS["pressure_raw"]].dropna()
        stations[station] = {
            "file": str(path.relative_to(directory)),
            "source_url": SOURCE_URLS[station],
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
            "raw_rows": len(frame),
            "malformed_or_separator_rows": int((~valid).sum()),
            "valid_timestamp_rows": len(observations),
            "station_ids": observations["Station ID"].value_counts().to_dict(),
            "station_names": observations["Station Name"].value_counts().to_dict(),
            "first_timestamp_as_supplied": str(observations["Timestamp"].min()),
            "last_timestamp_as_supplied": str(observations["Timestamp"].max()),
            "duplicate_station_timestamp_rows": int(observations.duplicated(["Station ID", "Timestamp"]).sum()),
            "non_null_by_channel": {name: int(values[column].notna().sum())
                                    for name, column in CHANNELS.items()},
            "complete_six_channel_15_minute_rows": int(complete.sum()),
            "hours_with_four_complete_15_minute_rows": full_hours,
            "pressure_raw_header": CHANNELS["pressure_raw"],
            "pressure_raw_median": float(pressure.median()) if len(pressure) else None,
            "pressure_raw_values_above_850": int(pressure.gt(850).sum()),
        }
    return {
        "status": "SOURCE_AUDIT_ONLY_NOT_TRAINING_APPROVED",
        "time_reference": "NAIVE_IN_CSV_PROVIDER_CLAIMS_UTC_NOT_YET_VERIFIED",
        "pressure_reference_and_units": "UNRESOLVED_HEADER_MM_HG_CONFLICTS_WITH_MOST_NUMERIC_VALUES",
        "aggregation": "No hourly training rows created; four complete 15-minute slots per hour are counted only",
        "stations": stations,
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    report = audit(root)
    (root / "audit_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: {k: value[k] for k in (
        "valid_timestamp_rows", "complete_six_channel_15_minute_rows",
        "hours_with_four_complete_15_minute_rows", "pressure_raw_median")}
        for key, value in report["stations"].items()}, indent=2))

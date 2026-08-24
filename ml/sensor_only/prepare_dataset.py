"""Build the versioned INDRA sensor-only feature matrix.

This adapter consumes an aligned prepared dataset and identifiers table. It
uses only fields measurable by the approved INDRA hardware and trailing
derivations that can be reproduced on the ESP32-S3.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


SCHEMA_VERSION = "indra_sensor_only_v1"
HAZARDS = ["wildfire", "flood", "storm", "air_quality"]
FEATURE_NAMES = [
    "temperature_c",
    "relative_humidity_pct",
    "pressure_hpa",
    "wind_speed_mps",
    "pm25_ug_m3",
    "pressure_trend_hpa_per_hour",
    "dew_point_c",
    "heat_index_c",
    "hour_sin",
    "hour_cos",
    "day_of_year_sin",
    "day_of_year_cos",
    "latitude_deg",
    "longitude_deg",
]
SOURCE_FEATURES = [
    "temp_current",
    "humidity_current",
    "pressure_current",
    "wind_speed_current",
    "pm25_current",
]
IDENTIFIER_COLUMNS = ["location_name", "last_updated", "latitude", "longitude"]


def _require_columns(frame: pd.DataFrame, columns: list[str], source: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{source} is missing required columns: {missing}")


def _dew_point_c(temperature_c: pd.Series, humidity_pct: pd.Series) -> pd.Series:
    humidity = humidity_pct.clip(lower=1e-3, upper=100.0)
    gamma = np.log(humidity / 100.0) + (17.625 * temperature_c) / (243.04 + temperature_c)
    return 243.04 * gamma / (17.625 - gamma)


def _heat_index_c(temperature_c: pd.Series, humidity_pct: pd.Series) -> pd.Series:
    temperature_f = temperature_c * 9.0 / 5.0 + 32.0
    heat_index_f = 0.5 * (
        temperature_f
        + 61.0
        + (temperature_f - 68.0) * 1.2
        + humidity_pct * 0.094
    )
    return (heat_index_f - 32.0) * 5.0 / 9.0


def _trailing_pressure_slope(
    timestamps: pd.Series,
    pressure_hpa: pd.Series,
    window: int,
) -> np.ndarray:
    parsed_times = pd.to_datetime(timestamps, utc=True).dt.tz_convert(None)
    times = parsed_times.to_numpy(dtype="datetime64[ns]").astype(np.float64)
    values = pressure_hpa.to_numpy(dtype=np.float64)
    slopes = np.full(len(values), np.nan, dtype=np.float64)
    ns_per_hour = 3_600_000_000_000.0

    for end in range(1, len(values)):
        start = max(0, end - window + 1)
        segment_times = (times[start : end + 1] - times[start]) / ns_per_hour
        segment_values = values[start : end + 1]
        valid = np.isfinite(segment_times) & np.isfinite(segment_values)
        if valid.sum() >= 2 and np.ptp(segment_times[valid]) > 0:
            slopes[end] = np.polyfit(segment_times[valid], segment_values[valid], 1)[0]
    return slopes


def build_sensor_only_dataset(
    prepared_dir: Path,
    output_dir: Path,
    humidity_input_scale: str = "fraction",
    wind_input_unit: str = "kph",
    pressure_window: int = 6,
) -> dict:
    features = pd.read_csv(prepared_dir / "features.csv")
    labels = pd.read_csv(prepared_dir / "labels.csv")
    identifiers = pd.read_csv(prepared_dir / "identifiers.csv")
    if not (len(features) == len(labels) == len(identifiers)):
        raise ValueError("features.csv, labels.csv, and identifiers.csv are not aligned")

    _require_columns(features, SOURCE_FEATURES, "features.csv")
    _require_columns(labels, HAZARDS, "labels.csv")
    _require_columns(identifiers, IDENTIFIER_COLUMNS, "identifiers.csv")
    if pressure_window < 2:
        raise ValueError("pressure_window must be at least 2")

    work = pd.DataFrame({"_row_id": np.arange(len(features), dtype=np.int64)})
    for column in SOURCE_FEATURES:
        work[column] = pd.to_numeric(features[column], errors="coerce")
    for column in IDENTIFIER_COLUMNS:
        work[column] = identifiers[column]

    work["last_updated"] = pd.to_datetime(work["last_updated"], utc=True, errors="coerce")
    work["latitude"] = pd.to_numeric(work["latitude"], errors="coerce")
    work["longitude"] = pd.to_numeric(work["longitude"], errors="coerce")
    work = work.sort_values(["location_name", "last_updated", "_row_id"]).reset_index(drop=True)

    output = pd.DataFrame(index=work.index)
    output["temperature_c"] = work["temp_current"]
    if humidity_input_scale == "fraction":
        output["relative_humidity_pct"] = work["humidity_current"] * 100.0
    elif humidity_input_scale == "percent":
        output["relative_humidity_pct"] = work["humidity_current"]
    else:
        raise ValueError(f"Unknown humidity input scale: {humidity_input_scale}")
    output["pressure_hpa"] = work["pressure_current"]
    if wind_input_unit == "kph":
        output["wind_speed_mps"] = work["wind_speed_current"] / 3.6
    elif wind_input_unit == "mps":
        output["wind_speed_mps"] = work["wind_speed_current"]
    else:
        raise ValueError(f"Unknown wind input unit: {wind_input_unit}")
    output["pm25_ug_m3"] = work["pm25_current"]

    output["pressure_trend_hpa_per_hour"] = np.nan
    for _, indices in work.groupby("location_name", sort=False).groups.items():
        group_indices = list(indices)
        output.loc[group_indices, "pressure_trend_hpa_per_hour"] = _trailing_pressure_slope(
            work.loc[group_indices, "last_updated"],
            output.loc[group_indices, "pressure_hpa"],
            pressure_window,
        )

    output["dew_point_c"] = _dew_point_c(
        output["temperature_c"], output["relative_humidity_pct"]
    )
    output["heat_index_c"] = _heat_index_c(
        output["temperature_c"], output["relative_humidity_pct"]
    )
    hour = work["last_updated"].dt.hour + work["last_updated"].dt.minute / 60.0
    day_of_year = work["last_updated"].dt.dayofyear
    output["hour_sin"] = np.sin(2.0 * math.pi * hour / 24.0)
    output["hour_cos"] = np.cos(2.0 * math.pi * hour / 24.0)
    output["day_of_year_sin"] = np.sin(2.0 * math.pi * day_of_year / 365.25)
    output["day_of_year_cos"] = np.cos(2.0 * math.pi * day_of_year / 365.25)
    output["latitude_deg"] = work["latitude"]
    output["longitude_deg"] = work["longitude"]

    finite_mask = np.isfinite(output.to_numpy(dtype=np.float64)).all(axis=1)
    range_mask = (
        output["relative_humidity_pct"].between(0.0, 100.0)
        & output["pressure_hpa"].between(800.0, 1200.0)
        & output["wind_speed_mps"].ge(0.0)
        & output["pm25_ug_m3"].ge(0.0)
        & output["latitude_deg"].between(-90.0, 90.0)
        & output["longitude_deg"].between(-180.0, 180.0)
    )
    keep_mask = finite_mask & range_mask.to_numpy()
    kept_rows = work.loc[keep_mask, "_row_id"].to_numpy(dtype=np.int64)
    output = output.loc[keep_mask, FEATURE_NAMES].reset_index(drop=True)
    output_labels = labels.iloc[kept_rows][HAZARDS].reset_index(drop=True)
    output_identifiers = identifiers.iloc[kept_rows].reset_index(drop=True)

    output_dir.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_dir / "features.csv", index=False)
    output_labels.to_csv(output_dir / "labels.csv", index=False)
    output_identifiers.to_csv(output_dir / "identifiers.csv", index=False)

    schema_path = Path(__file__).with_name("feature_schema_v1.json")
    schema_hash = hashlib.sha256(schema_path.read_bytes()).hexdigest()
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "schema_sha256": schema_hash,
        "feature_names": FEATURE_NAMES,
        "num_features": len(FEATURE_NAMES),
        "num_samples": len(output),
        "dropped_rows": int(len(features) - len(output)),
        "pressure_window_observations": pressure_window,
        "source_prepared_dir": str(prepared_dir),
        "source_units": {
            "humidity_current": humidity_input_scale,
            "wind_speed_current": wind_input_unit,
        },
        "forbidden_features_removed": [
            "co2_current",
            "lightning_dist_current",
            "lightning_threat",
        ],
        "label_provenance": "legacy_weak_labels_with_synthetic_dependencies",
        "metric_scope": "integration_baseline_only_not_valid_indra_metrics",
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--humidity-input-scale", choices=["fraction", "percent"], default="fraction")
    parser.add_argument("--wind-input-unit", choices=["kph", "mps"], default="kph")
    parser.add_argument("--pressure-window", type=int, default=6)
    args = parser.parse_args()
    metadata = build_sensor_only_dataset(
        args.prepared,
        args.output,
        args.humidity_input_scale,
        args.wind_input_unit,
        args.pressure_window,
    )
    print(
        f"Saved {metadata['num_samples']:,} rows with {metadata['num_features']} "
        f"{metadata['schema_version']} features to {args.output}"
    )
    print("WARNING: inherited labels are weak; resulting metrics are not valid INDRA metrics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

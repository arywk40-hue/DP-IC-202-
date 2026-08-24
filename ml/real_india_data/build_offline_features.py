"""Build a richer offline feature set from the joined India pilot.

This schema is intentionally not edge-compatible. It is used to test whether
real pollutant fields improve generalization before feature distillation to the
14-feature ESP32 model.
"""

import argparse
import json
import os

import numpy as np
import pandas as pd


FEATURE_NAMES = [
    "temp_current", "humidity_current", "pressure_current", "wind_speed_current",
    "pm25_current", "pm10_current", "co_current", "so2_current", "o3_current",
    "no2_current", "precipitation_current",
    "temp_humidity_ratio", "pressure_trend", "heat_index", "dew_point",
    "fire_risk_index", "flood_risk_index", "doy_sin", "doy_cos",
]


def pressure_slope(values):
    values = np.asarray(values, dtype=float)
    valid = np.isfinite(values)
    if valid.sum() < 2:
        return 0.0
    t = np.arange(len(values), dtype=float)[valid]
    return float(np.polyfit(t, values[valid], 1)[0])


def build(raw_path: str, labels_path: str, output_dir: str):
    df = pd.read_csv(raw_path)
    labels = pd.read_csv(labels_path)
    required = {
        "location_name", "last_updated", "temperature_celsius", "humidity",
        "pressure_mb", "wind_kph", "air_quality_PM2.5", "air_quality_PM10",
        "air_quality_Carbon_Monoxide", "air_quality_Sulphur_dioxide",
        "air_quality_Ozone", "air_quality_Nitrogen_dioxide",
        "precipitation_mm",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Raw India input missing columns: {sorted(missing)}")

    df["last_updated"] = pd.to_datetime(df["last_updated"], utc=True, errors="coerce")
    df = df.dropna(subset=["last_updated"]).sort_values(
        ["location_name", "last_updated"]
    ).reset_index(drop=True)
    if len(df) != len(labels):
        raise ValueError("Raw input and labels are not row-aligned")

    out = pd.DataFrame(index=df.index)
    out["temp_current"] = df["temperature_celsius"]
    out["humidity_current"] = df["humidity"] / 100.0
    out["pressure_current"] = df["pressure_mb"]
    out["wind_speed_current"] = df["wind_kph"]
    out["pm25_current"] = df["air_quality_PM2.5"]
    out["pm10_current"] = df["air_quality_PM10"]
    out["co_current"] = df["air_quality_Carbon_Monoxide"]
    out["so2_current"] = df["air_quality_Sulphur_dioxide"]
    out["o3_current"] = df["air_quality_Ozone"]
    out["no2_current"] = df["air_quality_Nitrogen_dioxide"]
    out["precipitation_current"] = df["precipitation_mm"]

    out["temp_humidity_ratio"] = out["temp_current"] / out["humidity_current"].clip(lower=0.01)
    out["pressure_trend"] = (
        df.groupby("location_name")["pressure_mb"]
        .transform(lambda s: s.rolling(6, min_periods=1).apply(pressure_slope, raw=True))
        .fillna(0.0)
    )
    humidity_pct = out["humidity_current"] * 100.0
    out["heat_index"] = out["temp_current"] + 0.5 * humidity_pct
    out["dew_point"] = out["temp_current"] - (100.0 - humidity_pct) / 5.0
    out["fire_risk_index"] = (
        (out["temp_current"] > 30).astype(float) * 0.25
        + (humidity_pct < 35).astype(float) * 0.25
        + (out["wind_speed_current"] > 5).astype(float) * 0.15
        + (out["pm25_current"] > 40).astype(float) * 0.35
    ).clip(0, 1)
    out["flood_risk_index"] = (
        (out["pressure_current"] < 1005).astype(float) * 0.30
        + (humidity_pct > 85).astype(float) * 0.30
        + (out["wind_speed_current"] > 8).astype(float) * 0.20
        + (out["pressure_current"] < 1000).astype(float) * 0.20
    ).clip(0, 1)

    day_of_year = df["last_updated"].dt.dayofyear
    out["doy_sin"] = np.sin(2 * np.pi * day_of_year / 365.25)
    out["doy_cos"] = np.cos(2 * np.pi * day_of_year / 365.25)
    teacher_features = [c for c in df.columns if c.startswith("teacher_next_day_")]
    feature_names = FEATURE_NAMES + teacher_features
    out = out[FEATURE_NAMES].copy()
    for column in teacher_features:
        out[column] = pd.to_numeric(df[column], errors="coerce")
    out = out[feature_names]
    out = out.ffill().bfill()

    identifiers = df[[c for c in [
        "location_name", "latitude", "longitude", "last_updated", "last_updated_epoch"
    ] if c in df.columns]].copy()
    os.makedirs(output_dir, exist_ok=True)
    out.to_csv(os.path.join(output_dir, "features.csv"), index=False)
    labels.to_csv(os.path.join(output_dir, "labels.csv"), index=False)
    identifiers.to_csv(os.path.join(output_dir, "identifiers.csv"), index=False)
    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump({
            "schema": "india_offline_v1",
            "feature_names": feature_names,
            "num_features": len(feature_names),
            "num_samples": len(out),
            "label_names": labels.columns.tolist(),
            "synthetic_fields": [],
            "source": os.path.basename(raw_path),
        }, f, indent=2)
    print(f"Saved {len(out):,} rows with {len(FEATURE_NAMES)} offline features to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    build(args.raw, args.labels, args.output)


if __name__ == "__main__":
    main()

"""Join the India city-hour air-quality pilot with daily weather.

The air-quality archive timestamps are treated as India Standard Time. Weather
pilot timestamps are already UTC. Both are converted to a UTC date before the
daily join.

Output is compatible with prepare_dataset_real.py.
"""

import argparse
import os

import pandas as pd


def build(aq_path: str, weather_path: str, output_path: str):
    aq = pd.read_csv(aq_path)
    weather = pd.read_csv(weather_path)

    required_aq = {"City", "Datetime", "PM2.5", "PM10", "CO", "SO2", "O3", "NO2"}
    missing = required_aq - set(aq.columns)
    if missing:
        raise ValueError(f"Air-quality input missing columns: {sorted(missing)}")

    required_weather = {
        "location_name", "latitude", "longitude", "date_utc",
        "temperature_celsius", "humidity", "pressure_mb", "wind_kph",
    }
    missing = required_weather - set(weather.columns)
    if missing:
        raise ValueError(f"Weather input missing columns: {sorted(missing)}")

    aq["timestamp_utc"] = (
        pd.to_datetime(aq["Datetime"], errors="coerce")
        .dt.tz_localize("Asia/Kolkata")
        .dt.tz_convert("UTC")
    )
    aq = aq.dropna(subset=["timestamp_utc"])
    aq["date_utc"] = aq["timestamp_utc"].dt.strftime("%Y-%m-%d")

    numeric = ["PM2.5", "PM10", "CO", "SO2", "O3", "NO2", "AQI"]
    for col in numeric:
        if col in aq:
            aq[col] = pd.to_numeric(aq[col], errors="coerce")

    aq_daily = aq.groupby(["City", "date_utc"], as_index=False).agg(
        pm25=("PM2.5", "mean"),
        pm10=("PM10", "mean"),
        co=("CO", "mean"),
        so2=("SO2", "mean"),
        o3=("O3", "mean"),
        no2=("NO2", "mean"),
        aqi=("AQI", "max"),
        aq_source_hours=("timestamp_utc", "count"),
    )

    weather = weather.rename(columns={"location_name": "City"})
    joined = weather.merge(aq_daily, on=["City", "date_utc"], how="inner")
    joined = joined.dropna(subset=["pm25"])
    if joined.empty:
        raise ValueError("No rows with observed PM2.5 remain after weather/AQ join")

    result = pd.DataFrame({
        "location_name": joined["City"],
        "latitude": joined["latitude"],
        "longitude": joined["longitude"],
        "last_updated": pd.to_datetime(joined["date_utc"], utc=True),
        "last_updated_epoch": pd.to_datetime(joined["date_utc"], utc=True).astype("int64") // 10**9,
        "temperature_celsius": joined["temperature_celsius"],
        "humidity": joined["humidity"],
        "pressure_mb": joined["pressure_mb"],
        "wind_kph": joined["wind_kph"],
        "precipitation_mm": joined.get("precipitation_mm", 0.0),
        "air_quality_PM2.5": joined["pm25"],
        "air_quality_PM10": joined["pm10"],
        "air_quality_Carbon_Monoxide": joined["co"],
        "air_quality_Sulphur_dioxide": joined["so2"],
        "air_quality_Ozone": joined["o3"],
        "air_quality_Nitrogen_dioxide": joined["no2"],
        "AQI": joined["aqi"],
        "aq_source_hours": joined["aq_source_hours"],
        "weather_source_hours": joined["source_hours"],
    }).sort_values(["location_name", "last_updated"])

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    result.to_csv(output_path, index=False)
    print(f"Joined rows: {len(result):,}")
    print(f"Locations:   {result['location_name'].nunique()}")
    print(f"Date range:  {result['last_updated'].min()} -> {result['last_updated'].max()}")
    print(f"Saved:       {output_path}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--air-quality", required=True)
    parser.add_argument("--weather", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    build(args.air_quality, args.weather, args.output)


if __name__ == "__main__":
    main()

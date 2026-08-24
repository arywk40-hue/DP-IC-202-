"""Aggregate public OpenAQ station data and join it to daily weather."""

import argparse
from pathlib import Path

import pandas as pd


def join(aq_path, weather_path, location_name, output, station_location_id=None):
    aq = pd.read_csv(aq_path)
    weather = pd.read_csv(weather_path)
    required_aq = {"datetime", "parameter", "value", "lat", "lon"}
    required_weather = {"date_utc", "temperature_celsius", "humidity", "pressure_mb", "wind_kph", "precipitation_mm"}
    if missing := required_aq - set(aq.columns):
        raise ValueError(f"OpenAQ input missing columns: {sorted(missing)}")
    if missing := required_weather - set(weather.columns):
        raise ValueError(f"Weather input missing columns: {sorted(missing)}")
    if "location_name" in weather.columns:
        weather = weather[weather["location_name"].eq(location_name)].copy()
        if weather.empty:
            raise ValueError(f"Weather input has no rows for {location_name}")
    aq = aq[aq["parameter"].eq("pm25")].copy()
    if station_location_id is not None:
        aq["location_id"] = pd.to_numeric(aq["location_id"], errors="coerce")
        aq = aq[aq["location_id"].eq(station_location_id)].copy()
    aq["timestamp_utc"] = pd.to_datetime(aq["datetime"], utc=True, errors="raise")
    aq["date_utc"] = aq["timestamp_utc"].dt.strftime("%Y-%m-%d")
    aq["value"] = pd.to_numeric(aq["value"], errors="coerce")
    aq = aq.dropna(subset=["value"])
    aq = aq[aq["value"] >= 0]
    daily = aq.groupby("date_utc", as_index=False).agg(
        pm25_ug_m3=("value", "mean"), aq_source_hours=("value", "count"),
        station_lat=("lat", "first"), station_lon=("lon", "first"),
    )
    weather = weather.copy()
    weather["date_utc"] = pd.to_datetime(weather["date_utc"], utc=True).dt.strftime("%Y-%m-%d")
    joined = weather.merge(daily, on="date_utc", how="inner")
    joined["location_name"] = location_name
    joined["last_updated"] = pd.to_datetime(joined["date_utc"], utc=True)
    joined["last_updated_epoch"] = joined["last_updated"].astype("int64") // 10**9
    joined["pm25_target_next_day"] = joined["pm25_ug_m3"].shift(-1)
    joined["target_date_utc"] = joined["date_utc"].shift(-1)
    joined = joined.dropna(subset=["pm25_target_next_day"])
    columns = ["location_name", "latitude", "longitude", "last_updated", "last_updated_epoch",
               "temperature_celsius", "humidity", "pressure_mb", "wind_kph", "precipitation_mm",
               "pm25_ug_m3", "pm25_target_next_day", "aq_source_hours", "station_lat", "station_lon"]
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    joined[columns].to_csv(output, index=False)
    print(f"Joined {len(joined):,} daily rows to {output}")
    print(f"PM2.5 range: {joined.pm25_ug_m3.min():.1f}–{joined.pm25_ug_m3.max():.1f} ug/m3")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--air-quality", required=True)
    parser.add_argument("--weather", required=True)
    parser.add_argument("--location-name", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--station-location-id", type=int)
    args = parser.parse_args()
    join(args.air_quality, args.weather, args.location_name, args.output, args.station_location_id)


if __name__ == "__main__":
    main()

"""Download a bounded daily India weather pilot from Open-Meteo.

This adapter intentionally downloads only the weather side of the pilot. Air
quality should be joined from a separately downloaded station/city dataset so
its provenance is not confused with reanalysis weather data.

Input locations CSV columns:
    location_name,latitude,longitude

Example:
    python3 download_weather_pilot.py \
        --locations locations.csv \
        --start 2015-01-01 --end 2020-07-01 \
        --output weather_pilot.csv
"""

import argparse
import json
import ssl
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd


API_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY = ",".join([
    "temperature_2m",
    "relative_humidity_2m",
    "pressure_msl",
    "wind_speed_10m",
    "precipitation",
])


def fetch_location(name, latitude, longitude, start, end, ssl_context=None):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start,
        "end_date": end,
        "hourly": HOURLY,
        "timezone": "UTC",
        "wind_speed_unit": "kmh",
    }
    with urlopen(f"{API_URL}?{urlencode(params)}", timeout=60, context=ssl_context) as response:
        payload = json.load(response)

    hourly = payload.get("hourly")
    if not hourly or "time" not in hourly:
        raise ValueError(f"No hourly data returned for {name}")

    frame = pd.DataFrame(hourly)
    frame["timestamp_utc"] = pd.to_datetime(frame.pop("time"), utc=True)
    frame["location_name"] = name
    frame["latitude"] = float(latitude)
    frame["longitude"] = float(longitude)

    # Aggregate to daily records so this pilot can align with the commonly
    # distributed city_day.csv air-quality data without inventing sub-daily AQ.
    frame["date_utc"] = frame["timestamp_utc"].dt.date.astype(str)
    daily = frame.groupby(
        ["location_name", "latitude", "longitude", "date_utc"],
        as_index=False,
    ).agg(
        temperature_celsius=("temperature_2m", "mean"),
        humidity=("relative_humidity_2m", "mean"),
        pressure_mb=("pressure_msl", "mean"),
        wind_kph=("wind_speed_10m", "mean"),
        precipitation_mm=("precipitation", "sum"),
        source_hours=("timestamp_utc", "count"),
    )
    return daily


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locations", required=True, help="CSV with location_name,latitude,longitude")
    parser.add_argument("--start", required=True, help="UTC start date, YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="UTC end date, YYYY-MM-DD")
    parser.add_argument("--output", required=True)
    parser.add_argument("--delay-seconds", type=float, default=0.2)
    parser.add_argument("--cache-dir", help="Optional per-location CSV cache for resumable downloads")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--continue-on-error", action="store_true",
                        help="Keep successful locations when one request fails")
    parser.add_argument("--ca-file", help="Optional PEM CA bundle for environments with missing system certificates")
    args = parser.parse_args()

    locations = pd.read_csv(args.locations)
    required = {"location_name", "latitude", "longitude"}
    missing = required - set(locations.columns)
    if missing:
        raise ValueError(f"Locations file missing columns: {sorted(missing)}")
    if locations["location_name"].duplicated().any():
        raise ValueError("Locations file contains duplicate location_name values")

    ssl_context = ssl.create_default_context(cafile=args.ca_file) if args.ca_file else None
    frames = []
    for row in locations.itertuples(index=False):
        cache_path = None
        if args.cache_dir:
            cache_path = Path(args.cache_dir) / f"{row.location_name}.csv"
            cache_path.parent.mkdir(parents=True, exist_ok=True)
        if cache_path is not None and cache_path.exists():
            print(f"Using cached {row.location_name}")
            frames.append(pd.read_csv(cache_path))
            continue
        print(f"Downloading {row.location_name}...", flush=True)
        last_error = None
        for attempt in range(args.retries + 1):
            try:
                frame = fetch_location(
                    row.location_name, row.latitude, row.longitude,
                    args.start, args.end,
                    ssl_context,
                )
                if cache_path is not None:
                    frame.to_csv(cache_path, index=False)
                frames.append(frame)
                last_error = None
                break
            except Exception as error:
                last_error = error
                if attempt < args.retries:
                    time.sleep(max(args.delay_seconds, 1.0) * (attempt + 1))
        if last_error is not None:
            if not args.continue_on_error:
                raise last_error
            print(f"Skipping {row.location_name}: {last_error}", flush=True)
        time.sleep(args.delay_seconds)

    if not frames:
        raise RuntimeError("No weather locations were downloaded")
    result = pd.concat(frames, ignore_index=True)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    print(f"Saved {len(result):,} daily rows to {output}")


if __name__ == "__main__":
    main()

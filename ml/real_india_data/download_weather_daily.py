"""Download resumable daily historical weather for a location list."""

import argparse
import json
import ssl
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd


API_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY = ",".join([
    "temperature_2m_mean", "relative_humidity_2m_mean", "pressure_msl_mean",
    "wind_speed_10m_mean", "precipitation_sum",
])


def fetch(row, start, end, context):
    params = {
        "latitude": row.latitude, "longitude": row.longitude,
        "start_date": start, "end_date": end, "daily": DAILY,
        "timezone": "UTC", "wind_speed_unit": "kmh",
    }
    with urlopen(f"{API_URL}?{urlencode(params)}", timeout=120, context=context) as response:
        payload = json.load(response)
    daily = payload.get("daily")
    if not daily or "time" not in daily:
        raise ValueError(f"No daily data returned for {row.location_name}")
    result = pd.DataFrame({
        "location_name": row.location_name,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "date_utc": daily["time"],
        "temperature_celsius": daily.get("temperature_2m_mean"),
        "humidity": daily.get("relative_humidity_2m_mean"),
        "pressure_mb": daily.get("pressure_msl_mean"),
        "wind_kph": daily.get("wind_speed_10m_mean"),
        "precipitation_mm": daily.get("precipitation_sum"),
    })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locations", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--ca-file", default=None)
    args = parser.parse_args()
    locations = pd.read_csv(args.locations)
    required = {"location_name", "latitude", "longitude"}
    if missing := required - set(locations.columns):
        raise ValueError(f"Locations CSV missing columns: {sorted(missing)}")
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    context = ssl.create_default_context(cafile=args.ca_file) if args.ca_file else None
    frames = []
    for row in locations.itertuples(index=False):
        cache = cache_dir / f"{row.location_name}.csv"
        if cache.exists():
            print(f"Using cached {row.location_name}", flush=True)
            frames.append(pd.read_csv(cache))
            continue
        last_error = None
        for attempt in range(args.retries + 1):
            try:
                print(f"Downloading {row.location_name}", flush=True)
                frame = fetch(row, args.start, args.end, context)
                frame.to_csv(cache, index=False)
                frames.append(frame)
                last_error = None
                break
            except Exception as error:
                last_error = error
                if attempt < args.retries:
                    time.sleep(max(1.0, args.delay_seconds) * (attempt + 1))
        if last_error is not None:
            raise last_error
        time.sleep(args.delay_seconds)
    result = pd.concat(frames, ignore_index=True).sort_values(["location_name", "date_utc"])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    print(f"Saved {len(result):,} rows to {output}")


if __name__ == "__main__":
    main()

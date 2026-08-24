"""Download daily Indian station observations from OpenAQ v3.

The API key is read only from ``OPENAQ_API_KEY``. The output is deliberately
long-form so parameter, sensor, unit, and coverage metadata are not lost before
the canonical weather/AQ join.
"""

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_ROOT = "https://api.openaq.org/v3"
PARAMETERS = {"pm25", "pm10", "co", "no2", "so2", "o3", "temperature", "relativehumidity"}


def get_json(path, api_key, params=None, timeout=60):
    query = f"?{urlencode(params)}" if params else ""
    request = Request(
        f"{API_ROOT}{path}{query}",
        headers={"X-API-Key": api_key, "Accept": "application/json"},
    )
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def paged(path, api_key, params=None, max_pages=None, delay=0.2):
    params = dict(params or {})
    page = 1
    while True:
        params.update({"page": page, "limit": 100})
        payload = get_json(path, api_key, params)
        results = payload.get("results", [])
        yield from results
        meta = payload.get("meta", {})
        if not results or page >= int(meta.get("pages", page)):
            break
        if max_pages is not None and page >= max_pages:
            break
        page += 1
        time.sleep(delay)


def normalize_parameter(sensor):
    parameter = sensor.get("parameter", {})
    return str(parameter.get("name") or parameter.get("displayName") or "").lower().replace(".", "")


def download(start, end, output, max_locations=None, delay=0.2):
    api_key = os.environ.get("OPENAQ_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENAQ_API_KEY in the environment; do not put it in a file or command log")

    locations = list(paged("/locations", api_key, {"countries_id": 9}, delay=delay))
    if max_locations:
        locations = locations[:max_locations]
    rows = []
    sensor_count = 0
    for location in locations:
        location_id = location.get("id")
        sensors = get_json(f"/locations/{location_id}/sensors", api_key).get("results", [])
        for sensor in sensors:
            parameter = normalize_parameter(sensor)
            if parameter not in PARAMETERS:
                continue
            sensor_count += 1
            sensor_id = sensor.get("id")
            for value in paged(
                f"/sensors/{sensor_id}/days",
                api_key,
                {"date_from": start, "date_to": end},
                delay=delay,
            ):
                period = value.get("period", {})
                date_from = period.get("datetimeFrom", {}).get("utc")
                if not date_from:
                    continue
                coordinates = location.get("coordinates") or {}
                rows.append({
                    "location_id": location_id,
                    "location_name": location.get("name"),
                    "latitude": coordinates.get("latitude"),
                    "longitude": coordinates.get("longitude"),
                    "sensor_id": sensor_id,
                    "parameter": parameter,
                    "value": value.get("value"),
                    "unit": sensor.get("parameter", {}).get("units"),
                    "date_utc": date_from[:10],
                    "observed_count": (value.get("coverage") or {}).get("observedCount"),
                    "expected_count": (value.get("coverage") or {}).get("expectedCount"),
                    "source": "OpenAQ",
                })
            time.sleep(delay)

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "location_id", "location_name", "latitude", "longitude", "sensor_id",
        "parameter", "value", "unit", "date_utc", "observed_count",
        "expected_count", "source",
    ]
    import csv
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "source_name": "OpenAQ v3 daily sensor observations",
        "source_url": "https://docs.openaq.org/",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_start_utc": start,
        "requested_end_utc": end,
        "locations_requested": len(locations),
        "sensors_selected": sensor_count,
        "rows": len(rows),
        "parameters": sorted(PARAMETERS),
        "label_provenance": "Observations only; hazard labels are not inferred",
        "api_key_stored": False,
    }
    with output.with_suffix(".manifest.json").open("w") as handle:
        json.dump(manifest, handle, indent=2)
    print(json.dumps(manifest, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-locations", type=int, default=None)
    parser.add_argument("--delay-seconds", type=float, default=0.2)
    args = parser.parse_args()
    download(args.start, args.end, args.output, args.max_locations, args.delay_seconds)


if __name__ == "__main__":
    main()

"""Download bounded OpenAQ public-S3 daily files without an API key."""

import argparse
import csv
import gzip
import io
import json
import ssl
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta, timezone, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen


ROOT = "https://openaq-data-archive.s3.amazonaws.com/records/csv.gz"


def daterange(start, end):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def fetch_day(location_id, day, cache_dir, context):
    cache = cache_dir / f"location-{location_id}-{day:%Y%m%d}.csv.gz"
    if cache.exists():
        return cache, True
    url = (
        f"{ROOT}/locationid={location_id}/year={day:%Y}/month={day:%m}/"
        f"location-{location_id}-{day:%Y%m%d}.csv.gz"
    )
    try:
        with urlopen(url, timeout=60, context=context) as response:
            cache.write_bytes(response.read())
        return cache, False
    except HTTPError as error:
        if error.code == 404:
            return None, False
        raise


def available_days(location_id, year, context):
    """Return archive dates that actually exist, avoiding slow 404 probes."""
    prefix = f"records/csv.gz/locationid={location_id}/year={year}/"
    url = f"https://openaq-data-archive.s3.amazonaws.com/?list-type=2&prefix={prefix}&max-keys=1000"
    with urlopen(url, timeout=60, context=context) as response:
        root = ET.fromstring(response.read())
    keys = []
    for element in root.iter():
        if element.tag.endswith("}Key") or element.tag == "Key":
            keys.append(element.text)
    return {key.rsplit("/", 1)[-1][len(f"location-{location_id}-"):-len(".csv.gz")] for key in keys}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--location-id", type=int, action="append", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--delay-seconds", type=float, default=0.1)
    parser.add_argument("--ca-file", default=None)
    args = parser.parse_args()
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    context = ssl.create_default_context(cafile=args.ca_file) if args.ca_file else None
    files = []
    downloaded = 0
    for location_id in args.location_id:
        available = {}
        for year in range(start.year, end.year + 1):
            available[year] = available_days(location_id, year, context)
        for day in daterange(start, end):
            if day.strftime("%Y%m%d") not in available.get(day.year, set()):
                continue
            path, cached = fetch_day(location_id, day, cache_dir, context)
            if path:
                files.append(path)
                downloaded += int(not cached)
            time.sleep(args.delay_seconds)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["location_id", "sensors_id", "location", "datetime", "lat", "lon", "parameter", "units", "value"]
    rows = []
    for path in files:
        with gzip.open(path, "rt", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                rows.append(row)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "source_name": "OpenAQ public data archive on AWS",
        "source_url": "https://docs.openaq.org/aws/about",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "location_ids": args.location_id,
        "requested_start_utc": args.start,
        "requested_end_utc": args.end,
        "files_found": len(files),
        "files_downloaded": downloaded,
        "rows": len(rows),
        "api_key_required": False,
        "hazard_labels_generated": False,
    }
    with output.with_suffix(".manifest.json").open("w") as handle:
        json.dump(manifest, handle, indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

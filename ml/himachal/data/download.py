"""Bounded monthly context acquisition or audited manual import; no scraping."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from http.client import IncompleteRead

from ml.himachal.data.sources import DEFAULT, load
from ml.operational.contracts import canonical_bytes
from ml.six_sensor_forecast.data import sha256


def reject_secret_metadata(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if any(s in str(key).lower() for s in ("password", "token", "secret", "api_key", "authorization", "cookie", "access_key")):
                raise ValueError("Credentials must not enter source provenance or logs")
            reject_secret_metadata(item)
    elif isinstance(value, list):
        for item in value:
            reject_secret_metadata(item)
    elif isinstance(value, str) and any(s in value.lower() for s in ("bearer ", "token=", "api_key=", "password=")):
        raise ValueError("Signed/credential URLs must not enter source provenance")


def windows(start, end):
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last or (last-first).days > 366*20:
        raise ValueError("Ordered dates within a bounded twenty-year research window required")
    while first <= last:
        following = (first.replace(day=28)+timedelta(days=4)).replace(day=1)
        stop = min(last, following-timedelta(days=1))
        yield first.isoformat(), stop.isoformat()
        first = stop+timedelta(days=1)


def request_for(config, source, start, end):
    entry = config["sources"][source]
    lat, lon = config["location"]["latitude"], config["location"]["longitude"]
    common = dict(latitude=lat, longitude=lon)
    if source == "open_meteo_weather":
        params = dict(**common, start_date=start, end_date=end, timezone="UTC", wind_speed_unit="ms",
                      models="era5", elevation="nan", hourly="temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,precipitation,snowfall")
    elif source == "open_meteo_air":
        params = dict(**common, start_date=start, end_date=end, timezone="UTC", domains="cams_global", hourly="pm2_5,pm10")
    elif source == "nasa_power":
        params = dict(**common, start=start.replace("-", ""), end=end.replace("-", ""), community="AG",
                      parameters="T2M,RH2M,PS,WS10M,PRECTOTCORR", format="JSON", **{"time-standard": "UTC"})
    else:
        raise ValueError("Use an approved manual export for this source; no bulk endpoint is assumed")
    return entry["endpoint"] + "?" + urlencode(params)


def cached_download(url, destination, *, max_bytes, attempts, opener=urlopen, sleep=time.sleep):
    """Resume only a validated Content-Range continuation with a fixed ETag.

    Retries retain partial bytes; a server ignoring Range restarts from zero.
    Authentication headers/tokens are not used or written by these public feeds.
    """
    part = destination.with_suffix(".partial")
    identity = destination.with_suffix(".partial.identity.json")
    host = urlsplit(url).hostname
    for attempt in range(attempts):
        offset = part.stat().st_size if part.exists() else 0
        etag = json.loads(identity.read_text()).get("etag") if identity.exists() else None
        headers = {"User-Agent": "INDRA-academic-research/1 source-aware-context"}
        if offset and etag:
            headers.update(Range=f"bytes={offset}-", **{"If-Range": etag})
        try:
            with opener(Request(url, headers=headers), timeout=30) as response:
                if urlsplit(response.geturl()).hostname != host:
                    raise ValueError("Unexpected source redirect; inspect provider access route")
                continuation = offset and etag and response.status == 206
                if continuation and (response.headers.get("ETag") != etag or not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-")):
                    raise ValueError("Unsafe partial response identity/range")
                if response.status not in {200, 206} or response.status == 206 and not continuation:
                    raise ValueError("Unexpected source response status")
                total = offset if continuation else 0
                identity.write_text(json.dumps({"etag": response.headers.get("ETag")}))
                with part.open("ab" if continuation else "wb") as handle:
                    while True:
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > max_bytes:
                            raise ValueError("Source response exceeds byte budget")
                        handle.write(chunk)
                content = json.loads(part.read_text())
                if not isinstance(content, dict) or content.get("error"):
                    raise ValueError("Provider returned an error instead of data")
                part.replace(destination)
                identity.unlink(missing_ok=True)
                return content
        except (HTTPError, URLError, OSError, IncompleteRead, json.JSONDecodeError) as exc:
            retryable = not isinstance(exc, HTTPError) or exc.code in {429, 500, 502, 503, 504}
            if attempt+1 == attempts or not retryable:
                raise
            retry_after = exc.headers.get("Retry-After", "") if isinstance(exc, HTTPError) else ""
            sleep(min(30., float(retry_after)) if retry_after.isdigit() else 2.**attempt)
    raise RuntimeError("Bounded download exhausted")


def acquire(config, source, start, end, output, *, offline=False, input_path=None, metadata=None, opener=urlopen, sleep=time.sleep):
    if source not in config["sources"]:
        raise ValueError("Unknown source; select a registered provider")
    chunks = list(windows(start, end))
    entry = config["sources"][source]
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if entry["mode"] == "manual_import":
        if input_path is None or metadata is None:
            return dict(status="NOT_READY", source=source, reason="APPROVED_EXPORT_AND_METADATA_REQUIRED", documentation=entry["documentation"], empirical_training_ready=False)
        reject_secret_metadata(metadata)
        required = {"provider_version", "source_station_or_cell_id", "native_cadence_seconds", "units", "rights_evidence_uri", "reviewed_by", "original_request", "retrieved_at_utc"}
        if not required <= set(metadata) or any(metadata[k] is None for k in required):
            raise ValueError("Audited import metadata missing; do not infer source clocks/rights/cell")
        from ml.operational.contracts import utc
        utc(metadata["retrieved_at_utc"])
        for key in ("provider_version", "source_station_or_cell_id", "rights_evidence_uri", "reviewed_by"):
            if not isinstance(metadata[key], str) or not metadata[key].strip():
                raise ValueError("Explicit import version/identity/rights reviewer required")
        if type(metadata["native_cadence_seconds"]) is not int or metadata["native_cadence_seconds"] < 1 or not isinstance(metadata["units"], dict) or not metadata["units"]:
            raise ValueError("Native cadence and named source units required")
        path = Path(input_path)
        if path.stat().st_size > config["limits"]["maximum_bytes"]:
            raise ValueError("Partition manual exports within the byte budget")
        digest = sha256(path)
        folder = output / digest
        folder.mkdir(exist_ok=True)
        destination = folder / "source.bin"
        if destination.exists() and sha256(destination) != digest:
            raise ValueError("Immutable imported source was modified")
        if not destination.exists():
            shutil.copyfile(path, destination)
        receipt = dict(schema_version="indra_source_cache_v1", status="CACHED_NOT_ADMITTED", source=source,
                       sha256=digest, source_role=entry, metadata=metadata, requested_interval=[start,end],
                       original_filename=path.name, empirical_training_ready=False)
        receipt_path = folder / "receipt.json"
        encoded = json.dumps(receipt, indent=2, allow_nan=False)+"\n"
        if receipt_path.exists() and receipt_path.read_text() != encoded:
            raise ValueError("Immutable import provenance differs; review a new source identity")
        receipt_path.write_text(encoded)
        return receipt
    receipts = []
    for first, last in chunks:
        url = request_for(config, source, first, last)
        request = dict(source=source, url=url, start=first, end=last, source_role=entry)
        key = hashlib.sha256(canonical_bytes(request)).hexdigest()
        folder = output / key
        folder.mkdir(exist_ok=True)
        raw, receipt_path = folder / "response.json", folder / "receipt.json"
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text())
            if receipt["request"] != request or not raw.exists() or receipt["sha256"] != sha256(raw):
                raise ValueError("Immutable source cache/provenance checksum mismatch")
        else:
            if offline:
                raise ValueError("Offline source cache incomplete; no provider call made")
            if raw.exists():
                raise ValueError("Unreceipted response exists; audit it before resuming")
            content = cached_download(url, raw, max_bytes=config["limits"]["maximum_bytes"], attempts=config["limits"]["attempts"], opener=opener, sleep=sleep)
            receipt = dict(schema_version="indra_source_cache_v1", status="CACHED_NOT_ADMITTED", request=request,
                sha256=sha256(raw), retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                returned_coordinates={k: content.get(k) for k in ("latitude", "longitude", "elevation")},
                units=content.get("hourly_units", content.get("parameters")),
                station_or_cell_id="UNVERIFIED_REQUIRES_PROVIDER_METADATA", native_role=entry,
                original_issue_time_availability="UNVERIFIED", empirical_training_ready=False)
            receipt_path.write_text(json.dumps(receipt, indent=2, allow_nan=False)+"\n")
            sleep(config["limits"]["minimum_request_interval_s"])
        receipts.append(receipt)
    return dict(status="CACHED_NOT_ADMITTED", source=source, chunks=receipts, empirical_training_ready=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, default=DEFAULT)
    p.add_argument("--source", required=True)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--offline", action="store_true")
    p.add_argument("--input", type=Path)
    p.add_argument("--metadata", type=Path)
    a = p.parse_args()
    result = acquire(load(a.config), a.source, a.start, a.end, a.output, offline=a.offline,
                     input_path=a.input, metadata=json.loads(a.metadata.read_text()) if a.metadata else None)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

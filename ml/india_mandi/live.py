"""Current Mandi model-grid collection; never physical station observations.

Discard future-valid rows before inference. Preserve first-seen values and actual
availability across provider revisions so delayed tests cannot rewrite the past.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from ml.himachal.contracts import snapshot
from ml.india_mandi.data import AIR, WEATHER, response_frame
from ml.operational.contracts import UNITS
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS

SOURCE = "OpenMeteo_current_ECMWF_IFS_CAMS_global"


def current_records(weather, air, retrieved_at):
    """Join exact UTC hours, exclude future hours, and retain provider grid IDs."""
    clock = pd.Timestamp(retrieved_at)
    if clock.tzinfo is None or any(
        v.get("utc_offset_seconds") != 0 for v in [weather, air]
    ):
        raise ValueError("Actual timezone-aware retrieval and UTC responses required")
    cells = {
        name: [value["latitude"], value["longitude"]]
        for name, value in [("weather", weather), ("air", air)]
    }
    for xy in cells.values():
        if (
            not np.isfinite(xy).all()
            or abs(xy[0] - 31.71) > 1
            or abs(xy[1] - 76.93) > 1
        ):
            raise ValueError("Unexpected provider cell for Mandi")
    frame = response_frame(weather, WEATHER).merge(
        response_frame(air, AIR), on="timestamp_utc", how="outer", validate="one_to_one"
    )
    if (frame.timestamp_utc != frame.timestamp_utc.dt.floor("h")).any():
        raise ValueError("Exact UTC hourly timestamps required")
    excluded = int((frame.timestamp_utc > clock).sum())
    frame = frame.loc[frame.timestamp_utc <= clock].sort_values("timestamp_utc")
    rows = []
    for _, row in frame.iterrows():
        stamp = row.timestamp_utc.isoformat()
        record = {
            "node_id": "mandi-api-current",
            "physical_site_id": "NOT_A_PHYSICAL_STATION",
            "registration_id": "mandi-current-api-v1",
            "latitude": 31.71,
            "longitude": 76.93,
            "elevation_m": None,
            "elevation_datum": "unknown",
            "sensor_height_m": None,
            "wind_height_m": None,
            "native_interval_seconds": 3600,
            "source_class": "modeled_grid",
            "source_id": SOURCE,
            "source_cell_id": json.dumps(cells, sort_keys=True, separators=(",", ":")),
            "pressure_reference": "grid_surface",
            "timestamp_utc": stamp,
            "valid_time_utc": stamp,
            "available_at_utc": clock.isoformat(),
            "sensor_model": "ECMWF_IFS_CAMS_NOT_SENSOR_HARDWARE",
            "calibration_ids": dict.fromkeys(RAW_SENSOR_COLUMNS),
            "units": UNITS.copy(),
            "measurements": {
                c: float(row[c]) if pd.notna(row[c]) else None
                for c in RAW_SENSOR_COLUMNS
            },
        }
        checked = snapshot(record)
        # Re-importable public contract only, never the validator's extra fields.
        record["measurements"] = checked["measurements"]
        record["quality_flags"] = checked["quality_flags"]
        rows.append(record)
    if not rows:
        raise ValueError("No past/current model hours available")
    return rows, excluded


def first_seen(previous, incoming):
    """Freeze past versions and availability; accept only newly seen hours."""
    lookup = {r["timestamp_utc"]: r for r in previous}
    revisions = added = 0
    for row in incoming:
        key = row["timestamp_utc"]
        if key not in lookup:
            lookup[key] = row
            added += 1
            continue
        old = lookup[key]
        if any(
            old[k] != row[k]
            for k in [
                "node_id",
                "source_id",
                "source_cell_id",
                "pressure_reference",
                "units",
            ]
        ):
            raise ValueError(
                "Source identity changed; start a separate collection directory"
            )
        if old["measurements"] != row["measurements"]:
            revisions += 1
        # A missing old record remains missing, not retrospectively repaired for
        # a prediction already issued using that history. Its replacement requires
        # a separate versioned source, just like any other provider revision.
    return (
        sorted(lookup.values(), key=lambda r: r["timestamp_utc"])[-193:],
        added,
        revisions,
    )


def atomic_json(path, value):
    """Publish a complete JSON file with one atomic rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    os.replace(temporary, path)


def collect(directory):
    """Download pinned current weather/PM sources and preserve retrieval receipts."""
    import hashlib
    import ssl
    import urllib.parse
    import urllib.request

    import certifi

    directory = Path(directory)
    run = directory / "raw" / pd.Timestamp.now(tz="UTC").strftime("%Y%m%dT%H%M%S%fZ")
    run.mkdir(parents=True, exist_ok=False)
    params = {
        "latitude": 31.71,
        "longitude": 76.93,
        "past_days": 3,
        "forecast_days": 1,
        "timezone": "UTC",
    }
    requests = {
        "weather": (
            "https://api.open-meteo.com/v1/forecast",
            {
                **params,
                "models": "ecmwf_ifs",
                "wind_speed_unit": "ms",
                "hourly": ",".join(WEATHER.values()),
            },
        ),
        "air": (
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            {**params, "domains": "cams_global", "hourly": ",".join(AIR.values())},
        ),
    }
    values, receipts = {}, {}
    for kind, (endpoint, query) in requests.items():
        url = endpoint + "?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(
            url, headers={"User-Agent": "INDRA-Mandi-local-test/1.0"}
        )
        with urllib.request.urlopen(
            request,
            context=ssl.create_default_context(cafile=certifi.where()),
            timeout=45,
        ) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("Oversized model API response")
        value = json.loads(raw)
        if value.get("error") or "hourly" not in value:
            raise ValueError(value.get("reason", "Missing hourly response"))
        (run / (kind + ".json")).write_bytes(raw)
        values[kind] = value
        receipts[kind] = {
            "url": url,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "returned_latitude": value["latitude"],
            "returned_longitude": value["longitude"],
        }
    retrieved = pd.Timestamp.now(tz="UTC").isoformat()
    rows, excluded = current_records(values["weather"], values["air"], retrieved)
    previous_path = directory / "history.json"
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else []
    rows, added, revisions = first_seen(previous, rows)
    atomic_json(previous_path, rows)
    manifest = {
        "source_class": "modeled_grid",
        "evidence": "CURRENT_MODEL_GRID_NOT_STATION_OBSERVATIONS",
        "requested_coordinates": [31.71, 76.93],
        "weather_model": "ecmwf_ifs",
        "air_domain": "cams_global",
        "retrieved_at_utc": retrieved,
        "rows": len(rows),
        "new_hours": added,
        "provider_revisions_ignored": revisions,
        "future_hours_excluded": excluded,
        "latest_valid_utc": rows[-1]["timestamp_utc"],
        "source_receipts": receipts,
        "history_sha256": hashlib.sha256(previous_path.read_bytes()).hexdigest(),
        "attribution": "Open-Meteo; ECMWF IFS; Copernicus Atmosphere Monitoring Service (CAMS)",
        "station_accuracy": False,
        "hazard_accuracy": False,
    }
    atomic_json(run / "receipt.json", manifest)
    atomic_json(directory / "latest_receipt.json", manifest)
    return rows, manifest

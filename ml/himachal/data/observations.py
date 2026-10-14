"""Source normalization without inventing native cadence or co-location."""
import math

import pandas as pd

from ml.himachal.contracts import snapshot
from ml.operational.contracts import utc
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS


def sensor_frame(records):
    """Separate histories by audited site/registration; no cross-source fusion."""
    rows = [snapshot(r) for r in records]
    keys = [(r["physical_site_id"], r["registration_id"], r["timestamp_utc"]) for r in rows]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate station/registration/time; reconcile aliases before labels")
    seen = {}
    output = []
    for r in rows:
        site = r["physical_site_id"] + ":" + r["registration_id"]
        identity = tuple(r[k] for k in ("latitude", "longitude", "elevation_m", "elevation_datum", "source_id", "source_cell_id", "pressure_reference"))
        if site in seen and seen[site] != identity:
            raise ValueError("Relocation or source/reference change within one history")
        seen[site] = identity
        output.append(dict(physical_site_id=site, original_physical_site_id=r["physical_site_id"],
            registration_id=r["registration_id"], location_id=r["node_id"], country_code="UNVERIFIED",
            timestamp_utc=utc(r["timestamp_utc"]), available_at_utc=utc(r["available_at_utc"]),
            latitude=r["latitude"], longitude=r["longitude"], elevation_m=r["elevation_m"],
            pressure_reference=r["pressure_reference"], source_class=r["source_class"],
            source_id=r["source_id"], source_cell_id=r["source_cell_id"], interval_seconds=r["native_interval_seconds"],
            evidence_kind="SYNTHETIC_CONTRACT_ONLY" if r["source_class"]=="synthetic_demo" else "SOURCE_ROLE_REVIEW_REQUIRED",
            **r["measurements"]))
    if not output:
        raise ValueError("Nonempty six-channel records required")
    return pd.DataFrame(output)


def imerg_hourly(records):
    """Convert *rates* to half-hour amounts; retain both quality/error records.

    Input timestamps are interval starts, not invented gauge event onset. Missing
    intervals/quality-rejected/fill values leave hourly amount null, never zero.
    """
    groups, seen = {}, set()
    for r in records:
        required = {"source_cell_id", "interval_start_utc", "interval_end_utc", "rate", "unit", "quality", "random_error", "fill_value"}
        if set(r) != required or not isinstance(r["source_cell_id"], str) or not r["source_cell_id"]:
            raise ValueError("IMERG interval/source/QC metadata required")
        start, end = utc(r["interval_start_utc"]), utc(r["interval_end_utc"])
        if (end-start).total_seconds() != 1800 or start.value % (1800*1_000_000_000) or r["unit"] != "mm/h":
            raise ValueError("Explicit half-hour mm/h rate intervals required")
        key = (r["source_cell_id"], start)
        if key in seen:
            raise ValueError("Duplicate IMERG cell/interval")
        seen.add(key)
        v = r["rate"]
        good = v is not None and not isinstance(v, bool) and math.isfinite(v) and v>=0 and v != r["fill_value"] and r["quality"] == "valid"
        # An advertised fill value of zero makes dry vs missing ambiguous;
        # preserve that ambiguity, never turn it into observed dry truth.
        amount = v*.5 if good else None
        groups.setdefault((r["source_cell_id"], start.floor("h")), []).append((start, amount, r))
    output = []
    for (cell, hour), pieces in sorted(groups.items()):
        complete = len(pieces)==2 and all(v is not None for _, v, _ in pieces)
        output.append(dict(source_cell_id=cell, interval_start_utc=hour.isoformat(),
            interval_end_utc=(hour+pd.Timedelta(hours=1)).isoformat(), precipitation_mm=sum(v for _, v, _ in pieces) if complete else None,
            unit="mm", expected_half_hours=2, observed_half_hours=len(pieces),
            quality="complete_estimate" if complete else "missing_or_rejected_interval",
            original_quality_error=[{k: repr(v) if isinstance(v,float) and not math.isfinite(v) else v for k,v in r.items()} for _, _, r in pieces], source_class="modeled_grid",
            independent_local_gauge=False, cloudburst_label_admissible=False))
    return output


def power_hourly(response):
    if response.get("header", {}).get("time_standard") != "UTC":
        raise ValueError("NASA POWER time standard must explicitly be UTC, never default LST")
    data, parameters = response["properties"]["parameter"], response["parameters"]
    expected_units = {"T2M": "C", "RH2M": "%", "PS": "kPa", "WS10M": "m/s"}
    for k, unit in expected_units.items():
        if parameters[k]["units"] != unit:
            raise ValueError("Unexpected POWER units; no magnitude inference")
    times = sorted(set().union(*(set(v) for v in data.values())))
    fill = response["header"]["fill_value"]
    output = []
    for t in times:
        stamp = pd.to_datetime(t, format="%Y%m%d%H", utc=True)
        values = {}
        for field, channel in (("T2M", "temperature_c"), ("RH2M", "relative_humidity_pct"), ("PS", "pressure_hpa"), ("WS10M", "wind_speed_mps")):
            v = data[field].get(t)
            values[channel] = None if v is None or v == fill or not math.isfinite(v) else v*10 if field == "PS" else v
        output.append(dict(timestamp_utc=stamp.isoformat(), source_class="modeled_grid",
            pressure_reference="grid_surface", native_interval_seconds=3600,
            measurements={**{c: None for c in RAW_SENSOR_COLUMNS}, **values}, independent_observed=False))
    return output

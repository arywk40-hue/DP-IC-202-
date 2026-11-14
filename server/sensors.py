"""Physical sensor ingestion, storage and multi-node combination.

This is the path real ESP32 readings take into INDRA. It is deliberately
separate from the Open-Meteo Mandi model-grid store in ``dashboard.py``:
modeled grid values and physical sensor values are never mixed in one table.

Accepted inputs on ``POST /api/ingest`` (JSON body):

1. The firmware's native long format (``esp32/operational_node``)::

     {"schema_version": "indra_weather_records_v1",
      "observations": [{"node_id": "...", "timestamp_utc": "...", "latitude": ..,
                        "longitude": .., "channel": "temperature_c", "value": 21.4, ...}, ...]}

2. A flat reading, convenient for other devices, scripts and the browser::

     {"node_id": "ridge-01", "temperature_c": 21.4, "relative_humidity_pct": 64,
      "pressure_hpa": 873.2, "pm25_ug_m3": 12, "pm10_ug_m3": 30, "wind_speed_mps": 3.1,
      "lat": 31.72, "lon": 76.94, "elevation_m": 1280, "battery_v": 3.98}

3. A list of flat readings (batch upload after an offline period).

4. An ``indra_hmac_v1`` envelope produced by ``packet_auth.h``; its base64
   payload must be one of the formats above.

Missing timestamps are stamped with the server receive time and marked
``timestamp_source = "server_receive"``. Values outside the physical ranges
are stored as null, never clamped, and counted in ``rejected_values``.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS

CHANNELS = list(RAW_SENSOR_COLUMNS)
UNITS = {
    "temperature_c": "°C",
    "relative_humidity_pct": "%",
    "pressure_hpa": "hPa",
    "pm25_ug_m3": "µg/m³",
    "pm10_ug_m3": "µg/m³",
    "wind_speed_mps": "m/s",
}
# Flat-format aliases accepted from other devices / older firmware.
ALIASES = {
    "temperature": "temperature_c", "temp": "temperature_c", "temp_c": "temperature_c",
    "humidity": "relative_humidity_pct", "rh": "relative_humidity_pct", "rh_pct": "relative_humidity_pct",
    "pressure": "pressure_hpa",
    "pm25": "pm25_ug_m3", "pm2_5": "pm25_ug_m3",
    "pm10": "pm10_ug_m3",
    "wind": "wind_speed_mps", "wind_speed": "wind_speed_mps",
    "latitude": "lat", "longitude": "lon", "lng": "lon",
    "elevation": "elevation_m", "altitude_m": "elevation_m",
    "battery": "battery_v", "bus_voltage_v": "battery_v",
    "timestamp": "timestamp_utc", "ts": "timestamp_utc", "time": "timestamp_utc",
    "id": "node_id", "node": "node_id",
}
NODE_ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
MAX_READINGS_PER_REQUEST = 5000
MAX_FUTURE_SKEW_S = 300
ONLINE_AFTER_S = 120          # seen within 2 min  -> ONLINE
STALE_AFTER_S = 15 * 60       # seen within 15 min -> STALE, else OFFLINE
HISTORY_HOURS = 24            # forecaster needs 24 h history + current hour


class IngestError(ValueError):
    """Raised for payloads that cannot be accepted at all."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value: Any) -> datetime | None:
    if value in (None, "", 0):
        return None
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 1e12 else value
        return datetime.fromtimestamp(seconds, timezone.utc)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    stamp = datetime.fromisoformat(text)
    if stamp.tzinfo is None:
        raise IngestError("timestamp_utc must include a timezone (e.g. trailing Z)")
    return stamp.astimezone(timezone.utc)


def iso(stamp: datetime) -> str:
    return stamp.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _number(value: Any) -> float | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _node_id(value: Any) -> str:
    node = str(value or "").strip()
    if not node or len(node) > 64 or any(c not in NODE_ID_CHARS for c in node):
        raise IngestError("node_id must be 1-64 characters of letters, digits, _ or -")
    if node == "UNCONFIGURED":
        raise IngestError("Node still uses the example config; set device_node_id() in device_config.h")
    return node


def _canonical(record: dict) -> dict:
    out = {}
    for key, value in record.items():
        out[ALIASES.get(key, key)] = value
    return out


def _from_long_format(observations: list) -> list[dict]:
    grouped: dict[tuple, dict] = {}
    for obs in observations:
        if not isinstance(obs, dict):
            raise IngestError("Each observation must be an object")
        node = _node_id(obs.get("node_id"))
        key = (node, obs.get("timestamp_utc") or "")
        row = grouped.setdefault(key, {
            "node_id": node,
            "timestamp_utc": obs.get("timestamp_utc"),
            "lat": obs.get("latitude"),
            "lon": obs.get("longitude"),
            "elevation_m": obs.get("elevation_m"),
            "battery_v": obs.get("battery_v"),
            "rssi_dbm": obs.get("rssi_dbm"),
            "transport": obs.get("transport"),
            "sensor_source": obs.get("source"),
        })
        channel = obs.get("channel")
        if channel in CHANNELS:
            valid = obs.get("quality_flag", "valid") == "valid"
            row[channel] = obs.get("value") if valid else None
    return list(grouped.values())


def decode_hmac_envelope(envelope: dict, key: bytes | None) -> Any:
    """Verify an ``indra_hmac_v1`` envelope from packet_auth.h and return its payload."""
    if key is None:
        raise IngestError("Signed packets received but INDRA_INGEST_HMAC_KEY is not configured")
    try:
        payload = base64.b64decode(envelope["payload_base64"], validate=True).decode("utf-8")
        message = "\n".join([envelope["node_id"], envelope["nonce"], envelope["sent_at_utc"], payload])
    except Exception as exc:
        raise IngestError(f"Malformed signed packet: {exc}") from exc
    expected = hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, str(envelope.get("signature_hex", "")).lower()):
        raise IngestError("Signature verification failed")
    return json.loads(payload)


def normalize(body: Any, *, hmac_key: bytes | None = None, received: datetime | None = None) -> tuple[list[dict], int]:
    """Turn any accepted payload into validated wide rows. Returns (rows, rejected_value_count)."""
    received = received or utc_now()
    signed = False
    if isinstance(body, dict) and body.get("protocol") == "indra_hmac_v1":
        body = decode_hmac_envelope(body, hmac_key)
        signed = True
    if isinstance(body, dict) and isinstance(body.get("observations"), list):
        raw = _from_long_format(body["observations"])
    elif isinstance(body, dict):
        raw = [body]
    elif isinstance(body, list):
        raw = []
        for item in body:
            if isinstance(item, dict) and isinstance(item.get("observations"), list):
                raw.extend(_from_long_format(item["observations"]))
            elif isinstance(item, dict):
                raw.append(item)
            else:
                raise IngestError("Batch items must be objects")
    else:
        raise IngestError("Body must be a JSON object or a list of objects")
    if not raw:
        raise IngestError("No readings in payload")
    if len(raw) > MAX_READINGS_PER_REQUEST:
        raise IngestError(f"At most {MAX_READINGS_PER_REQUEST} readings per request")

    rows, rejected = [], 0
    for item in raw:
        rec = _canonical(item)
        node = _node_id(rec.get("node_id"))
        stamp = parse_time(rec.get("timestamp_utc"))
        source = "device_clock"
        if stamp is None:
            stamp, source = received, "server_receive"
        if (stamp - received).total_seconds() > MAX_FUTURE_SKEW_S:
            raise IngestError(f"{node}: timestamp {iso(stamp)} is in the future; check the node clock")
        values = {}
        for channel in CHANNELS:
            value = _number(rec.get(channel))
            low, high = PHYSICAL_RANGES[channel]
            if value is not None and not low <= value <= high:
                rejected += 1
                value = None
            values[channel] = value
        lat, lon = _number(rec.get("lat")), _number(rec.get("lon"))
        if lat is not None and not -90 <= lat <= 90:
            lat = None
        if lon is not None and not -180 <= lon <= 180:
            lon = None
        if all(v is None for v in values.values()):
            rejected += 1
            continue
        rows.append(dict(
            node_id=node,
            timestamp_utc=iso(stamp),
            timestamp_source=source,
            received_utc=iso(received),
            lat=lat, lon=lon,
            elevation_m=_number(rec.get("elevation_m")),
            battery_v=_number(rec.get("battery_v")),
            rssi_dbm=_number(rec.get("rssi_dbm")),
            transport=str(rec.get("transport") or ("signed" if signed else "http"))[:24],
            name=str(rec["name"])[:80] if rec.get("name") else None,
            **values,
        ))
    return rows, rejected


class SensorStore:
    """SQLite store of physical readings; thread-safe for the FastAPI worker pool."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(f"""CREATE TABLE IF NOT EXISTS readings (
                node_id TEXT NOT NULL, timestamp_utc TEXT NOT NULL, timestamp_source TEXT NOT NULL,
                received_utc TEXT NOT NULL, lat REAL, lon REAL, elevation_m REAL,
                battery_v REAL, rssi_dbm REAL, transport TEXT,
                {', '.join(f'{c} REAL' for c in CHANNELS)},
                PRIMARY KEY (node_id, timestamp_utc))""")
            db.execute("""CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY, name TEXT, lat REAL, lon REAL, elevation_m REAL,
                first_seen_utc TEXT NOT NULL, last_seen_utc TEXT NOT NULL,
                last_received_utc TEXT NOT NULL, battery_v REAL, rssi_dbm REAL,
                transport TEXT, reading_count INTEGER NOT NULL DEFAULT 0)""")
            db.execute("CREATE INDEX IF NOT EXISTS readings_time ON readings(timestamp_utc)")

    def _connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def insert(self, rows: Iterable[dict]) -> dict:
        rows = list(rows)
        cols = ["node_id", "timestamp_utc", "timestamp_source", "received_utc", "lat", "lon",
                "elevation_m", "battery_v", "rssi_dbm", "transport", *CHANNELS]
        stored = 0
        with self._lock, self._connect() as db:
            for r in rows:
                cur = db.execute(
                    f"INSERT OR REPLACE INTO readings ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                    [r.get(c) for c in cols])
                stored += cur.rowcount
                db.execute("""INSERT INTO nodes (node_id, name, lat, lon, elevation_m, first_seen_utc,
                        last_seen_utc, last_received_utc, battery_v, rssi_dbm, transport, reading_count)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,1)
                    ON CONFLICT(node_id) DO UPDATE SET
                        name=COALESCE(excluded.name, nodes.name),
                        lat=COALESCE(excluded.lat, nodes.lat),
                        lon=COALESCE(excluded.lon, nodes.lon),
                        elevation_m=COALESCE(excluded.elevation_m, nodes.elevation_m),
                        first_seen_utc=CASE WHEN nodes.reading_count=0 THEN excluded.first_seen_utc
                                            ELSE nodes.first_seen_utc END,
                        last_seen_utc=MAX(nodes.last_seen_utc, excluded.last_seen_utc),
                        last_received_utc=excluded.last_received_utc,
                        battery_v=COALESCE(excluded.battery_v, nodes.battery_v),
                        rssi_dbm=COALESCE(excluded.rssi_dbm, nodes.rssi_dbm),
                        transport=excluded.transport,
                        reading_count=nodes.reading_count+1""",
                    (r["node_id"], r.get("name"), r.get("lat"), r.get("lon"), r.get("elevation_m"),
                     r["timestamp_utc"], r["timestamp_utc"], r["received_utc"], r.get("battery_v"),
                     r.get("rssi_dbm"), r.get("transport")))
        return dict(stored=stored, nodes=sorted({r["node_id"] for r in rows}))

    def register(self, node_id: str, **meta) -> dict:
        """Set fixed metadata (name, location, elevation) for a node, e.g. one without GPS."""
        node_id = _node_id(node_id)
        now = iso(utc_now())
        with self._lock, self._connect() as db:
            db.execute("""INSERT INTO nodes (node_id, name, lat, lon, elevation_m, first_seen_utc,
                    last_seen_utc, last_received_utc, reading_count) VALUES (?,?,?,?,?,?,?,?,0)
                ON CONFLICT(node_id) DO UPDATE SET name=COALESCE(excluded.name,nodes.name),
                    lat=COALESCE(excluded.lat,nodes.lat), lon=COALESCE(excluded.lon,nodes.lon),
                    elevation_m=COALESCE(excluded.elevation_m,nodes.elevation_m)""",
                (node_id, meta.get("name"), _number(meta.get("lat")), _number(meta.get("lon")),
                 _number(meta.get("elevation_m")), "1970-01-01T00:00:00Z", "1970-01-01T00:00:00Z", now))
        return self.node(node_id)

    def node(self, node_id: str) -> dict | None:
        return next((n for n in self.nodes() if n["node_id"] == node_id), None)

    def nodes(self, now: datetime | None = None) -> list[dict]:
        now = now or utc_now()
        with self._connect() as db:
            db.row_factory = sqlite3.Row
            items = [dict(r) for r in db.execute("SELECT * FROM nodes ORDER BY node_id")]
        for n in items:
            seen = parse_time(n["last_received_utc"])
            age = (now - seen).total_seconds() if n["reading_count"] else None
            n["age_seconds"] = None if age is None else round(max(0.0, age), 1)
            n["status"] = ("NO_DATA" if age is None else "ONLINE" if age <= ONLINE_AFTER_S
                           else "STALE" if age <= STALE_AFTER_S else "OFFLINE")
        return items

    def latest(self, node_id: str) -> dict | None:
        with self._connect() as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM readings WHERE node_id=? ORDER BY timestamp_utc DESC LIMIT 1",
                             (node_id,)).fetchone()
        return dict(row) if row else None

    def history(self, node_id: str, hours: float = 24, limit: int = 5000) -> list[dict]:
        since = iso(utc_now() - timedelta(hours=hours))
        with self._connect() as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("""SELECT * FROM readings WHERE node_id=? AND timestamp_utc>=?
                ORDER BY timestamp_utc DESC LIMIT ?""", (node_id, since, limit)).fetchall()
        return [dict(r) for r in reversed(rows)]

    def hourly(self, node_id: str, hours: int = HISTORY_HOURS + 1, now: datetime | None = None) -> list[dict]:
        """Hourly means (floor-hour buckets) for the forecaster; missing hours are absent."""
        now = now or utc_now()
        since = iso((now - timedelta(hours=hours)).replace(minute=0, second=0, microsecond=0))
        avg = ", ".join(f"AVG({c}) AS {c}" for c in CHANNELS)
        with self._connect() as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(f"""SELECT substr(timestamp_utc,1,13) AS hour, COUNT(*) AS samples, {avg}
                FROM readings WHERE node_id=? AND timestamp_utc>=? GROUP BY hour ORDER BY hour""",
                (node_id, since)).fetchall()
        return [dict(r, timestamp_utc=r["hour"] + ":00:00Z") for r in rows]

    def prune(self, keep_days: int = 30) -> int:
        cutoff = iso(utc_now() - timedelta(days=keep_days))
        with self._lock, self._connect() as db:
            return db.execute("DELETE FROM readings WHERE timestamp_utc<?", (cutoff,)).rowcount


def _stats(values: list[float]) -> dict | None:
    if not values:
        return None
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return dict(mean=round(mean, 3), min=round(min(values), 3), max=round(max(values), 3),
                spread=round(max(values) - min(values), 3), std=round(math.sqrt(var), 3), n=len(values))


LAPSE_RADIUS_KM = 50.0   # vertical gradients only make sense between nearby sites


def _km(a: dict, b: dict) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def local_cluster(entries: list[dict], radius_km: float = LAPSE_RADIUS_KM) -> list[dict]:
    """Largest group of positioned nodes within radius_km of one member (ties: lowest node_id)."""
    placed = [e for e in entries if e["lat"] is not None and e["lon"] is not None]
    best: list[dict] = []
    for centre in sorted(placed, key=lambda e: e["node_id"]):
        group = [e for e in placed if _km(centre, e) <= radius_km]
        if len(group) > len(best):
            best = group
    return best


def lapse_rate(points: list[tuple[float, float]]) -> float | None:
    """Least-squares dT/dz in °C per km from (elevation_m, temperature_c) pairs."""
    if len(points) < 2:
        return None
    zs = [p[0] for p in points]
    if max(zs) - min(zs) < 50:  # elevations too close for a meaningful gradient
        return None
    zm = sum(zs) / len(zs)
    tm = sum(p[1] for p in points) / len(points)
    den = sum((z - zm) ** 2 for z in zs)
    slope = sum((z - zm) * (t - tm) for z, t in points) / den
    return round(slope * 1000, 3)


def forecast_node(store: SensorStore, engine, node_id: str, now: datetime | None = None) -> dict:
    """Run the active +6 h forecaster on a node's hourly means, never filling gaps."""
    now = now or utc_now()
    buckets = store.hourly(node_id, now=now)
    if not buckets:
        return dict(status="NO_DATA", history_hours=0, required_hours=HISTORY_HOURS + 1)
    if engine is None:
        return dict(status="FORECASTER_UNAVAILABLE", history_hours=len(buckets), required_hours=HISTORY_HOURS + 1)
    import pandas as pd

    end = pd.Timestamp(buckets[-1]["timestamp_utc"])
    by_hour = {pd.Timestamp(b["timestamp_utc"]): b for b in buckets}
    rows = []
    for h in range(HISTORY_HOURS, -1, -1):
        stamp = end - pd.Timedelta(hours=h)
        b = by_hour.get(stamp, {})
        rows.append(dict(location_id=node_id, timestamp_utc=stamp.isoformat(),
                         **{c: b.get(c) for c in CHANNELS}))
    frame = pd.DataFrame(rows)
    for c in CHANNELS:
        frame[c] = pd.to_numeric(frame[c])
    result = engine.predict(frame).iloc[-1]
    forecast = {c: (float(result["forecast_" + c]) if math.isfinite(result["forecast_" + c]) else None)
                for c in CHANNELS}
    complete_hours = sum(1 for r in rows if all(r[c] is not None for c in CHANNELS))
    return dict(status=str(result["status"]), model_id=str(result["model_id"]),
                issued_for_utc=iso(end.to_pydatetime()),
                valid_at_utc=iso((end + pd.Timedelta(hours=6)).to_pydatetime()),
                values=forecast, history_hours=complete_hours, required_hours=HISTORY_HOURS + 1,
                note=None if result["status"] == "HYBRID_READY" else
                "Needs 25 consecutive complete hourly readings; showing persistence until then.")


def combined_view(store: SensorStore, engine=None, *, include_forecast: bool = True,
                  now: datetime | None = None) -> dict:
    """Latest reading of every node side by side, plus network-wide combination."""
    now = now or utc_now()
    nodes = store.nodes(now)
    entries, fresh = [], []
    for n in nodes:
        latest = store.latest(n["node_id"])
        entry = dict(
            node_id=n["node_id"], name=n["name"] or n["node_id"], status=n["status"],
            age_seconds=n["age_seconds"], lat=n["lat"], lon=n["lon"], elevation_m=n["elevation_m"],
            battery_v=n["battery_v"], rssi_dbm=n["rssi_dbm"], transport=n["transport"],
            reading_count=n["reading_count"],
            reading=None if latest is None else dict(
                timestamp_utc=latest["timestamp_utc"], timestamp_source=latest["timestamp_source"],
                **{c: latest[c] for c in CHANNELS}),
        )
        if include_forecast and latest is not None:
            try:
                entry["forecast_6h"] = forecast_node(store, engine, n["node_id"], now)
            except Exception as exc:  # a bad node must not take down the whole view
                entry["forecast_6h"] = dict(status="ERROR", error=f"{type(exc).__name__}: {exc}")
        entries.append(entry)
        if latest is not None and n["status"] in ("ONLINE", "STALE"):
            fresh.append(entry)

    network = {c: _stats([e["reading"][c] for e in fresh if e["reading"][c] is not None]) for c in CHANNELS}
    cluster = local_cluster([e for e in fresh if e["elevation_m"] is not None])
    temp_points = [(e["elevation_m"], e["reading"]["temperature_c"]) for e in cluster
                   if e["elevation_m"] is not None and e["reading"]["temperature_c"] is not None]
    press_points = [(e["elevation_m"], e["reading"]["pressure_hpa"]) for e in cluster
                    if e["elevation_m"] is not None and e["reading"]["pressure_hpa"] is not None]
    lapse = lapse_rate(temp_points)
    wind = [e["reading"]["wind_speed_mps"] for e in fresh if e["reading"]["wind_speed_mps"] is not None]
    n_fresh = len(fresh)
    quorum = n_fresh * 2 // 3 + 1 if n_fresh else 0
    return dict(
        generated_at_utc=iso(now),
        source="PHYSICAL_SENSORS",
        node_count=len(nodes),
        online=sum(e["status"] == "ONLINE" for e in entries),
        stale=sum(e["status"] == "STALE" for e in entries),
        offline=sum(e["status"] == "OFFLINE" for e in entries),
        units=UNITS,
        nodes=entries,
        network=dict(
            channels=network,
            contributing_nodes=n_fresh,
            quorum_rule="floor(2/3 * N) + 1",
            quorum_needed=quorum,
            spatial=dict(
                lapse_rate_c_per_km=lapse,
                pressure_gradient_hpa_per_km=lapse_rate(press_points),
                wind_shear_mps=round(max(wind) - min(wind), 3) if len(wind) >= 2 else None,
                stability=None if lapse is None else
                    ("ABSOLUTELY_UNSTABLE" if lapse < -9.8 else
                     "CONDITIONALLY_UNSTABLE" if lapse < -6.5 else
                     "STABLE" if lapse <= 0 else "INVERSION"),
                nodes_used=sorted(e["node_id"] for e in cluster),
                radius_km=LAPSE_RADIUS_KM,
                note=None if lapse is not None else
                    f"Needs at least 2 fresh nodes within {LAPSE_RADIUS_KM:.0f} km of each other "
                    "with elevations at least 50 m apart.",
            ),
        ),
    )


HEATMAP_SYNC_WINDOW_S = 120   # readings within this window count as one snapshot
COLLINEAR_RATIO = 0.25        # cross-valley spread below 25% of along-valley spread -> transect


def _snapshot(store: SensorStore, now: datetime, sync_window_s: int):
    """Latest reading per located node, keeping only those within sync_window_s of the newest."""
    candidates, excluded = [], []
    for n in store.nodes(now):
        latest = store.latest(n["node_id"])
        if latest is None:
            continue
        if n["lat"] is None or n["lon"] is None:
            excluded.append({"id": n["node_id"], "reason": "NO_LOCATION"})
            continue
        candidates.append((n, latest, parse_time(latest["timestamp_utc"])))
    if not candidates:
        return [], excluded, None
    newest = max(c[2] for c in candidates)
    kept = []
    for n, latest, stamp in candidates:
        if (newest - stamp).total_seconds() > sync_window_s:
            excluded.append({"id": n["node_id"], "reason": "OLDER_THAN_SYNC_WINDOW"})
        else:
            kept.append((n, latest))
    return kept, excluded, newest


def sensor_parameter_maps(store: SensorStore, resolution: int = 24, *, now: datetime | None = None,
                          sync_window_s: int = HEATMAP_SYNC_WINDOW_S) -> dict:
    """IDW surfaces (ml.himachal.parameter_maps) over the latest physical readings.

    Each node's latest reading is used if it falls within ``sync_window_s`` of the newest
    one; the group is then treated as one snapshot. No values are filled or extrapolated:
    cells exist only inside the nodes' convex hull (or on the segment for 2 nodes).
    """
    from ml.himachal.parameter_maps import parameter_maps

    now = now or utc_now()
    candidates, excluded, newest = _snapshot(store, now, sync_window_s)
    snapshot_ms = int(newest.timestamp() * 1000) if newest else 0
    stale = bool(newest) and (now - newest).total_seconds() > STALE_AFTER_S
    adapted = [dict(
        id=n["node_id"], name=n["name"] or n["node_id"], lat=n["lat"], lng=n["lon"],
        timestamp=snapshot_ms, stale=stale, sourceClass="physical_sensor", sourceId=n["node_id"],
        physicalSiteId=n["node_id"], pressureReference="station",
        sensors={c: latest[c] for c in CHANNELS}) for n, latest in candidates]
    # Catchment nodes often sit along one valley/slope: a thin triangle has no cells
    # inside it, so nearly collinear layouts are shown as a transect instead.
    result = parameter_maps(adapted, resolution, collinear_ratio=COLLINEAR_RATIO)
    result["source_class"] = "physical_sensor" if adapted else None
    result["sync_window_seconds"] = sync_window_s
    result["excluded_nodes"] = excluded + result["excluded_nodes"]
    if result["observation_timestamp"] is not None:
        result["observation_timestamp"] = iso(datetime.fromtimestamp(result["observation_timestamp"] / 1000, timezone.utc))
    elevations = [n["elevation_m"] for n, _ in candidates if n["elevation_m"] is not None]
    if len(elevations) >= 2 and max(elevations) - min(elevations) >= 100:
        result["elevation_note"] = (
            f"Nodes span {min(elevations):.0f}-{max(elevations):.0f} m: temperature and pressure "
            "differences are mostly elevation, not horizontal weather. No terrain correction is applied.")
    return result


AREA_MIN_RADIUS_KM = 0.25
AREA_MAX_RADIUS_KM = 25.0
AREA_MAX_EXTENT_KM = 100.0


def _elevation_note(nodes) -> str | None:
    elevations = [n["elevation_m"] for n in nodes if n["elevation_m"] is not None]
    if len(elevations) >= 2 and max(elevations) - min(elevations) >= 100:
        return (f"Nodes span {min(elevations):.0f}-{max(elevations):.0f} m: temperature and pressure "
                "differences are mostly elevation, not horizontal weather. No terrain correction is applied.")
    return None


def sensor_area_heatmap(store: SensorStore, channel: str = "temperature_c", *, radius_km: float | None = None,
                        resolution: int = 40, power: float = 2.0, now: datetime | None = None,
                        sync_window_s: int = HEATMAP_SYNC_WINDOW_S) -> dict:
    """Area estimate covering every point within radius_km of a node (GeoJSON cells).

    Values are inverse-distance-weighted (power 2) from all nodes with a reading for the
    channel, so every cell stays between the lowest and highest measured value. Each cell
    carries the distance to its nearest node and a 0-1 confidence (1 at a node, 0 at the
    radius edge). Auto radius: 0.75 x the largest nearest-neighbour spacing, clamped to
    0.25-25 km (1 km for a single node). Works for any number of nodes: three nodes 300 m
    apart get ~225 m, three nodes 10 km apart get ~7 km, and the gaps between them are covered.
    """
    import numpy as np

    if channel not in CHANNELS:
        raise ValueError("Unknown parameter")
    if type(resolution) is not int or not 10 <= resolution <= 80:
        raise ValueError("Resolution must be an integer from 10 to 80")
    if radius_km is not None and not 0.1 <= radius_km <= 50:
        raise ValueError("radius_km must be between 0.1 and 50")
    now = now or utc_now()
    snapshot, excluded, newest = _snapshot(store, now, sync_window_s)
    used = [(n, l) for n, l in snapshot if l[channel] is not None]
    excluded += [{"id": n["node_id"], "reason": "NO_VALUE_FOR_CHANNEL"} for n, l in snapshot if l[channel] is None]
    out = dict(type="FeatureCollection", features=[], channel=channel, unit=UNITS[channel], mode="radius",
               method=f"IDW_POWER_{power:g}_WITHIN_RADIUS", status="UNAVAILABLE", reason="No located node has a "
               "current reading for this channel.", minimum=None, maximum=None, radius_km=None, cell_size_km=None,
               node_count=len(used), nodes=[], excluded_nodes=excluded, bounds=None,
               observation_timestamp=iso(newest) if newest else None,
               stale=bool(newest) and (now - newest).total_seconds() > STALE_AFTER_S,
               elevation_note=_elevation_note([n for n, _ in used]),
               interpretation="ESTIMATED_BETWEEN_AND_AROUND_MEASUREMENTS_NOT_OBSERVATIONS")
    if not used:
        return out
    lat = np.array([n["lat"] for n, _ in used], float)
    lon = np.array([n["lon"] for n, _ in used], float)
    values = np.array([l[channel] for _, l in used], float)
    origin = np.array([lat.mean(), lon.mean()])
    kx = 111195.0 * math.cos(math.radians(origin[0]))   # metres per degree longitude
    ky = 111195.0                                        # metres per degree latitude
    xy = np.column_stack([(lon - origin[1]) * kx, (lat - origin[0]) * ky])
    if len(used) > 1:
        dist = np.linalg.norm(xy[:, None, :] - xy[None, :, :], axis=2)
        np.fill_diagonal(dist, np.inf)
        if dist.min() < 1.0:
            raise ValueError("Two nodes report from the same position")
        nn_max_km = dist.min(axis=1).max() / 1000
        auto = min(max(0.75 * nn_max_km, AREA_MIN_RADIUS_KM), AREA_MAX_RADIUS_KM)
    else:
        auto = 1.0
    radius_m = float(radius_km if radius_km is not None else auto) * 1000
    low, high = xy.min(0) - radius_m, xy.max(0) + radius_m
    extent_km = (high - low).max() / 1000
    if extent_km > AREA_MAX_EXTENT_KM:
        out["reason"] = (f"Nodes plus radius span {extent_km:.0f} km; area maps are limited to "
                         f"{AREA_MAX_EXTENT_KM:.0f} km. Use a smaller radius or nearby nodes.")
        return out
    cell = (high - low).max() / resolution
    nx, ny = int(math.ceil((high[0] - low[0]) / cell)), int(math.ceil((high[1] - low[1]) / cell))
    cx = low[0] + (np.arange(nx) + 0.5) * cell
    cy = low[1] + (np.arange(ny) + 0.5) * cell
    gx, gy = np.meshgrid(cx, cy)
    query = np.column_stack([gx.ravel(), gy.ravel()])
    d = np.linalg.norm(query[:, None, :] - xy[None, :, :], axis=2)
    nearest = d.min(axis=1)
    inside = nearest <= radius_m
    weights = 1 / np.maximum(d[inside], 1e-6) ** power
    estimate = weights @ values / weights.sum(axis=1)
    lo_v, hi_v = float(values.min()), float(values.max())
    features = []
    half = cell / 2
    for (qx, qy), v, near in zip(query[inside], estimate, nearest[inside]):
        ring = [[qx - half, qy - half], [qx + half, qy - half], [qx + half, qy + half], [qx - half, qy + half],
                [qx - half, qy - half]]
        coords = [[round(origin[1] + x / kx, 6), round(origin[0] + y / ky, 6)] for x, y in ring]
        features.append(dict(type="Feature", geometry=dict(type="Polygon", coordinates=[coords]), properties=dict(
            value=round(float(v), 3), channel=channel, unit=UNITS[channel],
            intensity=0.5 if hi_v == lo_v else round((float(v) - lo_v) / (hi_v - lo_v), 4),
            distance_km=round(float(near) / 1000, 2),
            confidence=round(max(0.0, 1 - float(near) / radius_m), 3))))
    out.update(
        features=features, status="AREA_ESTIMATE" if len(used) > 1 else "SINGLE_NODE_AREA",
        minimum=lo_v, maximum=hi_v, radius_km=round(radius_m / 1000, 2), cell_size_km=round(cell / 1000, 3),
        bounds=[origin[0] + low[1] / ky, origin[1] + low[0] / kx, origin[0] + high[1] / ky, origin[1] + high[0] / kx],
        nodes=[dict(id=n["node_id"], lat=n["lat"], lng=n["lon"], value=l[channel]) for n, l in used],
        reason=("One node: its reading is shown around it; add nodes to see variation."
                if len(used) == 1 else
                f"Estimated within {radius_m / 1000:.2g} km of a node from {len(used)} nodes; colors fade "
                "with distance from the nearest node. Not measured between nodes; no terrain correction."))
    return out


def register_routes(app, store: SensorStore, engine=None, *, ingest_token: str | None = None,
                    hmac_key: bytes | None = None) -> None:
    """Mount the physical-sensor API on an existing FastAPI app."""
    from fastapi import Body, Header, HTTPException, Query

    ingest_token = ingest_token if ingest_token is not None else os.environ.get("INDRA_INGEST_TOKEN") or None
    if hmac_key is None and os.environ.get("INDRA_INGEST_HMAC_KEY"):
        hmac_key = bytes.fromhex(os.environ["INDRA_INGEST_HMAC_KEY"])
    stats = dict(accepted=0, rejected_requests=0, last_error=None, last_ingest_utc=None)
    app.state.sensor_store = store
    app.state.sensor_ingest_stats = stats

    def check_token(token: str | None):
        if ingest_token and not hmac.compare_digest(token or "", ingest_token):
            raise HTTPException(401, "Missing or wrong X-Indra-Token")

    @app.post("/api/ingest")
    def ingest(body: Any = Body(...), x_indra_token: str | None = Header(None)):
        check_token(x_indra_token)
        try:
            rows, rejected = normalize(body, hmac_key=hmac_key)
        except (IngestError, ValueError) as exc:
            stats["rejected_requests"] += 1
            stats["last_error"] = str(exc)
            raise HTTPException(400, str(exc)) from exc
        result = store.insert(rows)
        stats["accepted"] += len(rows)
        stats["last_ingest_utc"] = iso(utc_now())
        return dict(ok=True, accepted=len(rows), rejected_values=rejected, **result)

    @app.post("/api/sensors/{node_id}/register")
    def register(node_id: str, body: dict = Body(...), x_indra_token: str | None = Header(None)):
        check_token(x_indra_token)
        try:
            return store.register(node_id, **body)
        except IngestError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/sensors")
    def sensor_nodes():
        return dict(nodes=store.nodes(), ingest=stats, auth_required=bool(ingest_token))

    @app.get("/api/sensors/combined")
    def combined(forecast: bool = Query(True)):
        return combined_view(store, engine, include_forecast=forecast)

    @app.get("/api/sensors/parameter-maps")
    def sensor_maps(resolution: int = Query(24, ge=8, le=40)):
        try:
            return sensor_parameter_maps(store, resolution)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/sensors/heatmap")
    def sensor_heatmap(channel: str = Query("temperature_c"), mode: str = Query("radius"),
                       radius_km: float = Query(None), resolution: int = Query(40, ge=8, le=80)):
        """mode=radius: area around nodes (default). mode=hull: strictly between nodes."""
        try:
            if mode == "radius":
                radius = None if radius_km in (None, "") else float(radius_km)
                return sensor_area_heatmap(store, channel, radius_km=radius, resolution=int(resolution))
            if mode != "hull":
                raise ValueError("mode must be 'radius' or 'hull'")
            from ml.himachal.parameter_maps import geojson
            bundle = sensor_parameter_maps(store, min(resolution, 40))
            out = geojson(bundle, channel)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        out.update(mode="hull", observation_timestamp=bundle["observation_timestamp"],
                   excluded_nodes=bundle["excluded_nodes"], elevation_note=bundle.get("elevation_note"),
                   node_count=len(bundle["nodes"]))
        return out

    @app.get("/api/sensors/{node_id}/latest")
    def latest(node_id: str):
        row = store.latest(node_id)
        if row is None:
            raise HTTPException(404, "No readings for this node")
        return row

    @app.get("/api/sensors/{node_id}/history")
    def history(node_id: str, hours: float = Query(24, gt=0, le=24 * 30),
                limit: int = Query(2000, gt=0, le=20000)):
        if store.node(node_id) is None:
            raise HTTPException(404, "Unknown node")
        return dict(node_id=node_id, units=UNITS, readings=store.history(node_id, hours, limit))

    @app.get("/api/sensors/{node_id}/hourly")
    def hourly(node_id: str, hours: int = Query(48, gt=0, le=24 * 30)):
        if store.node(node_id) is None:
            raise HTTPException(404, "Unknown node")
        return dict(node_id=node_id, units=UNITS, hours=store.hourly(node_id, hours))

    @app.get("/api/sensors/{node_id}/forecast")
    def forecast(node_id: str):
        if store.node(node_id) is None:
            raise HTTPException(404, "Unknown node")
        return forecast_node(store, engine, node_id)

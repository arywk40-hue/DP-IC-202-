"""Tolerant parser for a LoRa mesh gateway's serial output -> INDRA /api/ingest payloads.

We do not know in advance how a third-party mesh prints its readings, so this
accepts the common shapes and normalises field names and units:

  * JSON object / list, flat or wrapped ({"data": {...}}, {"payload": {...}},
    {"nodes": [...]}, {"readings": [...]})
  * "key=value" / "key:value" lines  ->  RX id=n3 T=24.1 H=55 P=1008.2 lat=31.7 lon=76.9 rssi=-97
  * CSV rows, optionally preceded by a header line
        id,lat,lon,temp,hum,press,pm25,pm10,wind
        n3,31.725,76.942,24.1,55,1008.2,12,20,1.4
  * An optional log prefix such as "[LoRa]" or "RX:" before any of the above

Node ids get a prefix (default ``lora-``) so a mesh node can never overwrite one
of your own nodes. Unknown or out-of-range values are dropped, never guessed.
"""
from __future__ import annotations

import json
import re
from typing import Any

CHANNELS = ["temperature_c", "relative_humidity_pct", "pressure_hpa",
            "pm25_ug_m3", "pm10_ug_m3", "wind_speed_mps"]

# normalised key (lower case, letters+digits only) -> canonical field
_KEYS: dict[str, str] = {}
for _canon, _names in {
    "node_id": ["node", "nodeid", "id", "nid", "src", "source", "from", "sender", "device", "deviceid", "dev", "addr", "address", "name"],
    "temperature_c": ["t", "temp", "tmp", "tempc", "temperature", "temperaturec", "airtemp"],
    "relative_humidity_pct": ["h", "hum", "humi", "humidity", "rh", "rhpct", "relativehumidity", "relativehumiditypct"],
    "pressure_hpa": ["p", "pres", "press", "pressure", "pressurehpa", "baro", "hpa", "pressurepa", "pa"],
    "pm25_ug_m3": ["pm25", "pm2", "pm2p5", "pm25ugm3", "pm", "dust25"],
    "pm10_ug_m3": ["pm10", "pm10ugm3", "dust10"],
    "wind_speed_mps": ["w", "wind", "windspeed", "windspeedmps", "ws", "windms", "anemometer"],
    "lat": ["lat", "latitude", "la", "latdeg", "latitudei"],
    "lon": ["lon", "lng", "long", "longitude", "lo", "londeg", "longitudei"],
    "elevation_m": ["alt", "altitude", "altitudem", "elev", "elevation", "elevationm", "height"],
    "battery_v": ["bat", "batt", "battery", "batteryv", "vbat", "vbatt", "voltage", "vbus"],
    "rssi_dbm": ["rssi", "rssidbm", "signal"],
    "snr_db": ["snr", "snrdb"],
    "timestamp_utc": ["ts", "time", "timestamp", "timestamputc", "datetime", "utc", "epoch", "unixtime"],
}.items():
    for _n in _names:
        _KEYS[_n] = _canon

_WRAPPERS = ("data", "payload", "reading", "readings", "sensors", "sensor", "measurements",
             "values", "nodes", "msg", "message", "packet", "pkt", "records", "obs")
_PREFIX = re.compile(r"^\s*(?:\[[^\]]{1,24}\]|(?:RX|LORA|LoRa|MESH|GW|DATA|PKT|RECV|RECEIVED)\b\s*[:>-]?)\s*", re.I)
_SAFE_ID = re.compile(r"[^A-Za-z0-9_-]+")
_KV = re.compile(r"([A-Za-z_][A-Za-z0-9_.]*)\s*[=:]\s*(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?|[A-Za-z0-9_-]+)")
_NUMBER = re.compile(r"^-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?$")


def _norm_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        out = float(str(value).strip().rstrip("%"))
    except ValueError:
        return None
    return out if out == out and abs(out) != float("inf") else None


def _flatten(obj: Any, found: dict, depth: int = 0) -> None:
    """Collect canonical fields from a (possibly nested) object, outer values win."""
    if depth > 4 or not isinstance(obj, dict):
        return
    for key, value in obj.items():
        if isinstance(value, dict) and _norm_key(key) in _WRAPPERS + tuple(_KEYS):
            _flatten(value, found, depth + 1)
            continue
        canon = _KEYS.get(_norm_key(key))
        if canon and canon not in found and not isinstance(value, (dict, list)):
            found[canon] = value


def _fix_units(rec: dict, raw_keys: set[str]) -> dict:
    out: dict[str, Any] = {}
    for channel in CHANNELS:
        value = _num(rec.get(channel))
        if value is None:
            continue
        if channel == "pressure_hpa":
            if value > 20000:                 # Pa -> hPa
                value /= 100.0
            elif value > 2000 and "pa" not in raw_keys:   # unlabeled but implausible for hPa
                value /= 100.0
        out[channel] = value
    lat, lon = _num(rec.get("lat")), _num(rec.get("lon"))
    for name, val in (("lat", lat), ("lon", lon)):
        if val is None:
            continue
        if abs(val) > 180:                    # integer micro/10-micro degrees (1e6 or 1e7)
            val = val / 1e7 if abs(val) > 1e8 else val / 1e6
        out[name] = val
    for name in ("elevation_m", "rssi_dbm", "snr_db"):
        v = _num(rec.get(name))
        if v is not None:
            out[name] = v
    batt = _num(rec.get("battery_v"))
    if batt is not None:
        batt = batt / 1000.0 if batt > 100 else batt
        if 2.0 <= batt <= 6.5:                # anything else is probably a percentage: skip
            out["battery_v"] = batt
    ts = rec.get("timestamp_utc")
    tsn = _num(ts)
    if tsn is not None:
        if tsn > 1.5e9:                       # a real epoch; a small number is uptime, so ignore it
            out["timestamp_utc"] = tsn
    elif isinstance(ts, str) and re.match(r"^\d{4}-\d\d-\d\d[T ]\d\d:\d\d", ts) and re.search(r"(Z|[+-]\d\d:?\d\d)$", ts):
        out["timestamp_utc"] = ts.replace(" ", "T")
    return out


def _node_id(value: Any, prefix: str) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)
    text = _SAFE_ID.sub("-", text.strip()).strip("-")
    if not text:
        return None
    return (prefix + text)[:64]


def _build(rec: dict, args_like, default_node: str | None, raw_keys: set[str]) -> dict | None:
    prefix = getattr(args_like, "node_prefix", "lora-")
    node = _node_id(rec.get("node_id"), prefix) or default_node
    fields = _fix_units(rec, raw_keys)
    if not node or not any(c in fields for c in CHANNELS):
        return None
    out = {"node_id": node, "transport": "lora_mesh", **fields}
    fixed = getattr(args_like, "nodes", None) or {}
    meta = fixed.get(node) or fixed.get(str(rec.get("node_id")))
    if meta:                                   # config only fills what the packet did not carry
        for key in ("lat", "lon", "elevation_m", "name"):
            if out.get(key) is None and meta.get(key) is not None:
                out[key] = meta[key]
    return out


def _from_object(obj: Any, args_like, default_node, out: list, depth: int = 0) -> None:
    if depth > 3:
        return
    if isinstance(obj, list):
        for item in obj:
            _from_object(item, args_like, default_node, out, depth + 1)
        return
    if not isinstance(obj, dict):
        return
    # {"nodes": [...]}, {"readings": {...}} etc: descend if the wrapper holds list-of-objects
    for key, value in obj.items():
        if _norm_key(key) in ("nodes", "readings", "records", "packets", "msgs", "messages") and isinstance(value, (list, dict)) \
                and (isinstance(value, list) or all(isinstance(v, dict) for v in value.values())):
            items = value if isinstance(value, list) else [
                {**v, **({"node_id": k} if not any(_KEYS.get(_norm_key(x)) == "node_id" for x in v) else {})} for k, v in value.items()]
            gateway: dict = {}
            _flatten({k: v for k, v in obj.items() if not isinstance(v, (dict, list))}, gateway)
            for item in items:
                if isinstance(item, dict):
                    merged = {**{k: v for k, v in gateway.items() if k in ("rssi_dbm", "snr_db")}, **item}
                    _from_object(merged, args_like, default_node, out, depth + 1)
            return
    found: dict = {}
    _flatten(obj, found)
    raw_keys = {_norm_key(k) for k in obj}
    built = _build(found, args_like, default_node, raw_keys)
    if built:
        out.append(built)


def parse_kv(text: str) -> dict:
    found: dict = {}
    raw_keys: set[str] = set()
    for key, value in _KV.findall(text):
        nk = _norm_key(key)
        canon = _KEYS.get(nk)
        if canon and canon not in found:
            found[canon] = value
            raw_keys.add(nk)
    return found


class LoraParser:
    """Stateful so a CSV header line seen earlier labels the rows that follow."""

    def __init__(self, args_like=None):
        self.args = args_like
        self.csv_header: list[str | None] | None = None

    def parse(self, line: str, default_node: str | None = None) -> list[dict]:
        text = line.strip()
        if not text:
            return []
        text = _PREFIX.sub("", text, count=1) if not text.startswith(("{", "[{")) else text
        out: list[dict] = []
        if text.startswith(("{", "[")):
            try:
                _from_object(json.loads(text), self.args, default_node, out)
            except json.JSONDecodeError:
                pass
            return out
        parts = [p.strip() for p in re.split(r"[,;\t]", text)]
        if len(parts) >= 3 and "=" not in text and ":" not in text.replace("://", ""):
            labels = [_KEYS.get(_norm_key(p)) if not _NUMBER.match(p) else None for p in parts]
            if sum(1 for lab in labels if lab) >= 3 and not any(_NUMBER.match(p) for p in parts):
                self.csv_header = labels            # header line: remember column order
                return []
            if self.csv_header and len(parts) == len(self.csv_header):
                rec = {lab: val for lab, val in zip(self.csv_header, parts) if lab}
                built = _build(rec, self.args, default_node, set())
                return [built] if built else []
        found = parse_kv(text)
        if found:
            built = _build(found, self.args, default_node, {_norm_key(k) for k in re.findall(r"([A-Za-z_][A-Za-z0-9_.]*)\s*[=:]", text)})
            if built:
                out.append(built)
        return out

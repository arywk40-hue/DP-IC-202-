"""Strict sensor_only_v1 feature contract shared with the ESP32 firmware."""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Mapping

FEATURE_NAMES = (
    "temperature_c", "relative_humidity_pct", "pressure_hpa", "wind_speed_mps",
    "pm25_ug_m3", "pressure_trend_hpa_per_hour", "dew_point_c", "heat_index_c",
    "hour_sin", "hour_cos", "day_of_year_sin", "day_of_year_cos",
    "latitude_deg", "longitude_deg",
)
SCHEMA_VERSION = "sensor_only_v1"
MODEL_STATUS = "NOT_READY"
MODEL_CHECKSUM = "NOT_READY-no-trained-model"

def schema_checksum() -> str:
    return hashlib.sha256("\n".join(FEATURE_NAMES).encode()).hexdigest()

def _require(row: Mapping[str, float], name: str) -> float:
    value = row.get(name)
    if value is None or not math.isfinite(float(value)):
        raise ValueError(f"missing required feature: {name}")
    return float(value)

def build_feature_vector(row: Mapping[str, float]) -> list[float]:
    t = _require(row, "temperature_c")
    rh = _require(row, "relative_humidity_pct")
    pressure = _require(row, "pressure_hpa")
    wind = _require(row, "wind_speed_mps")
    pm25 = _require(row, "pm25_ug_m3")
    trend = _require(row, "pressure_trend_hpa_per_hour")
    hour = _require(row, "hour")
    day = _require(row, "day_of_year")
    latitude = _require(row, "latitude_deg")
    longitude = _require(row, "longitude_deg")
    if not 0 <= hour <= 23 or not 1 <= day <= 366 or not 0 < rh <= 100:
        raise ValueError("feature input outside contract range")
    gamma = 17.27 * t / (237.7 + t) + math.log(rh / 100.0)
    dew_point = 237.7 * gamma / (17.27 - gamma)
    heat_index = t
    if t >= 26.7 and rh >= 40:
        f = t * 9 / 5 + 32
        hi_f = (-42.379 + 2.04901523*f + 10.14333127*rh - .22475541*f*rh
                - .00683783*f*f - .05481717*rh*rh + .00122874*f*f*rh
                + .00085282*f*rh*rh - .00000199*f*f*rh*rh)
        heat_index = (hi_f - 32) * 5 / 9
    return [t, rh, pressure, wind, pm25, trend, dew_point, heat_index,
            math.sin(2 * math.pi * hour / 24), math.cos(2 * math.pi * hour / 24),
            math.sin(2 * math.pi * (day - 1) / 365), math.cos(2 * math.pi * (day - 1) / 365),
            latitude, longitude]

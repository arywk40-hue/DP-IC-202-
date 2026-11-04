"""Mandi-shaped Open-Meteo responses for isolated automated tests only."""
from datetime import datetime, timedelta, timezone
import math

from ml.india_mandi.live import current_records

NOW = datetime(2026, 10, 15, 6, tzinfo=timezone.utc)


def mandi_api_rows(now=NOW, hours=73):
    times = [now - timedelta(hours=hours - 1 - i) for i in range(hours)]
    stamps = [value.strftime("%Y-%m-%dT%H:%M") for value in times]
    weather = {
        "latitude": 31.71, "longitude": 76.93, "utc_offset_seconds": 0,
        "hourly_units": {"temperature_2m": "°C", "relative_humidity_2m": "%",
                          "surface_pressure": "hPa", "wind_speed_10m": "m/s"},
        "hourly": {
            "time": stamps,
            "temperature_2m": [12 + 4 * math.sin(i / 6) for i in range(hours)],
            "relative_humidity_2m": [68 + 8 * math.cos(i / 9) for i in range(hours)],
            "surface_pressure": [887 + 2 * math.sin(i / 11) for i in range(hours)],
            "wind_speed_10m": [1.5 + abs(math.sin(i / 7)) for i in range(hours)],
        },
    }
    air = {
        "latitude": 31.71, "longitude": 76.93, "utc_offset_seconds": 0,
        "hourly_units": {"pm2_5": "µg/m³", "pm10": "µg/m³"},
        "hourly": {
            "time": stamps,
            "pm2_5": [15 + 3 * abs(math.sin(i / 8)) for i in range(hours)],
            "pm10": [28 + 5 * abs(math.cos(i / 9)) for i in range(hours)],
        },
    }
    rows, _ = current_records(weather, air, now.isoformat())
    return rows

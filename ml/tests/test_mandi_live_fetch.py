"""Current API data never become physical or future-derived sensor labels."""

import copy

import pytest

from ml.india_mandi.live import current_records, first_seen


def payloads():
    weather = {
        "latitude": 31.67,
        "longitude": 76.94,
        "utc_offset_seconds": 0,
        "hourly_units": {
            "temperature_2m": "°C",
            "relative_humidity_2m": "%",
            "surface_pressure": "hPa",
            "wind_speed_10m": "m/s",
        },
        "hourly": {
            "time": ["2026-10-21T10:00", "2026-10-21T11:00", "2026-10-21T12:00"],
            "temperature_2m": [20, 21, 22],
            "relative_humidity_2m": [50, 51, 52],
            "surface_pressure": [930, 931, 932],
            "wind_speed_10m": [1, 2, 3],
        },
    }
    air = {
        "latitude": 31.7,
        "longitude": 76.9,
        "utc_offset_seconds": 0,
        "hourly_units": {"pm2_5": "µg/m³", "pm10": "µg/m³"},
        "hourly": {
            "time": weather["hourly"]["time"],
            "pm2_5": [20, 21, 22],
            "pm10": [40, 41, 42],
        },
    }
    return weather, air


def test_future_excluded_actual_availability_and_modeled_identity():
    weather, air = payloads()
    rows, excluded = current_records(weather, air, "2026-10-21T11:20:00Z")
    assert len(rows) == 2 and excluded == 1
    assert all(r["source_class"] == "modeled_grid" for r in rows)
    assert rows[-1]["available_at_utc"] == "2026-10-21T11:20:00+00:00"
    assert rows[0]["timestamp_utc"] == "2026-10-21T10:00:00+00:00"
    assert "NOT_A_PHYSICAL" in rows[0]["physical_site_id"]
    assert "31.67" in rows[0]["source_cell_id"] and "31.7" in rows[0]["source_cell_id"]


def test_provider_revisions_do_not_rewrite_first_seen_truth_or_availability():
    weather, air = payloads()
    old, _ = current_records(weather, air, "2026-10-21T11:20:00Z")
    weather["hourly"]["temperature_2m"][0] = 30
    new, _ = current_records(weather, air, "2026-10-21T12:20:00Z")
    merged, added, revisions = first_seen(old, new)
    assert added == 1 and revisions == 1
    assert merged[:2] == old
    assert merged[-1]["timestamp_utc"] == "2026-10-21T12:00:00+00:00"
    new[0]["source_cell_id"] = "changed-cell"
    with pytest.raises(ValueError, match="identity changed"):
        first_seen(old, new)


def test_missing_pm_stays_missing_and_wrong_units_or_grid_fail_closed():
    weather, air = payloads()
    air["hourly"]["pm2_5"][0] = None
    rows, _ = current_records(weather, air, "2026-10-21T12:20:00Z")
    assert rows[0]["measurements"]["pm25_ug_m3"] is None
    bad = copy.deepcopy(weather)
    bad["hourly_units"]["wind_speed_10m"] = "km/h"
    with pytest.raises(ValueError, match="unit"):
        current_records(bad, air, "2026-10-21T12:20:00Z")
    weather["latitude"] = 40
    with pytest.raises(ValueError, match="cell"):
        current_records(weather, air, "2026-10-21T12:20:00Z")

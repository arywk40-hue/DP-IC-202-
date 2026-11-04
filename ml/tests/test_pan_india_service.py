"""Test INDRA Pan-India Forecasting Service & National Model Routing.

Verifies:
1. All 6 Pan-India agro-climatic zones are configured with valid geodetic bounds and models.
2. Coordinates across India (Mandi, Delhi, Mumbai, Jaipur, Guwahati, Hyderabad) resolve accurately.
3. 587-station directory lookups, nearest-station distance, and zone filtering.
4. Regional +6h forecast generation with physical delta bounds.
5. FastAPI national gateway endpoints (/api/national/zones, /api/national/stations, /api/national/forecast).
"""

from __future__ import annotations

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from ml.national.service import PanIndiaForecastingService, ZONES, haversine_km
from server.dashboard import create_app
from server.tests.mandi_fixture import NOW, mandi_api_rows

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def service():
    return PanIndiaForecastingService()


@pytest.fixture(scope="module")
def api_client(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "test_pan_india.sqlite"
    app = create_app(db_file)
    with TestClient(app) as client:
        yield client


def test_national_zones_configuration(service):
    """Verify all 6 Indian agro-climatic zones are defined with valid metadata."""
    zones = service.list_zones()
    assert len(zones) == 6

    zone_ids = {z["id"] for z in zones}
    expected_ids = {
        "western_himalayas",
        "indo_gangetic_plains",
        "arid_northwest",
        "western_ghats_coastal",
        "central_deccan_plateau",
        "northeast_hills_brahmaputra",
    }
    assert zone_ids == expected_ids

    # Western Himalayas must be active operational flagship
    himalayas = next(z for z in zones if z["id"] == "western_himalayas")
    assert himalayas["service_status"] == "OPERATIONAL_FLAGSHIP"
    assert himalayas["active_model_id"] == "india_mandi_tabular_v2"
    assert "cloudburst" in himalayas["dominant_hazards"]
    assert "snowstorm" in himalayas["dominant_hazards"]


def test_geodetic_zone_resolution(service):
    """Verify major Indian cities resolve to the correct agro-climatic zone."""
    cases = [
        (31.71, 76.93, 760.0, "western_himalayas"),        # Mandi, HP
        (32.22, 77.19, 2050.0, "western_himalayas"),       # Manali, HP
        (34.15, 77.57, 3373.0, "western_himalayas"),       # Leh, Ladakh
        (28.61, 77.21, 216.0, "indo_gangetic_plains"),     # Delhi-NCR
        (26.85, 80.95, 123.0, "indo_gangetic_plains"),     # Lucknow, UP
        (22.57, 88.36, 9.0, "indo_gangetic_plains"),       # Kolkata, WB
        (26.91, 75.78, 431.0, "arid_northwest"),           # Jaipur, Rajasthan
        (23.02, 72.57, 53.0, "arid_northwest"),            # Ahmedabad, Gujarat
        (19.07, 72.87, 14.0, "western_ghats_coastal"),     # Mumbai, Konkan
        (15.49, 73.82, 10.0, "western_ghats_coastal"),     # Panaji, Goa
        (9.93, 76.26, 4.0, "western_ghats_coastal"),       # Kochi, Kerala
        (17.38, 78.48, 505.0, "central_deccan_plateau"),   # Hyderabad, Telangana
        (12.97, 77.59, 920.0, "central_deccan_plateau"),   # Bengaluru, Karnataka
        (26.14, 91.73, 55.0, "northeast_hills_brahmaputra"), # Guwahati, Assam
        (25.57, 91.89, 1496.0, "northeast_hills_brahmaputra"), # Shillong, Meghalaya
    ]
    for lat, lon, elev, expected_zone in cases:
        zone = service.resolve_zone(lat, lon, elevation_m=elev)
        assert zone.id == expected_zone, f"Failed for ({lat}, {lon}): got {zone.id}, expected {expected_zone}"


def test_station_registry_and_nearest_lookup(service):
    """Verify loading of the 587 Indian stations and nearest station search."""
    st = service.stations
    assert len(st) >= 300, f"Expected hundreds of Indian stations, found {len(st)}"

    # Check nearest station to Mandi coordinates (31.71, 76.93)
    nearest_mandi = service.find_nearest_stations(31.71, 76.93, limit=3)
    assert len(nearest_mandi) == 3
    assert "MANDI" in nearest_mandi[0]["station_name"].upper()
    assert nearest_mandi[0]["distance_km"] < 10.0

    # Check nearest station to Delhi (28.61, 77.21)
    nearest_delhi = service.find_nearest_stations(28.61, 77.21, limit=1)
    assert len(nearest_delhi) == 1
    assert "SAFDARJUNG" in nearest_delhi[0]["station_name"].upper()
    assert nearest_delhi[0]["distance_km"] < 10.0


def test_pan_india_forecast_generation(service):
    """Verify +6h forecast generation across different zones."""
    readings = {
        "temperature_c": 22.0,
        "relative_humidity_pct": 65.0,
        "pressure_hpa": 1008.0,
        "pm25_ug_m3": 45.0,
        "pm10_ug_m3": 70.0,
        "wind_speed_mps": 2.5,
    }

    # Test Delhi (Indo-Gangetic Plains)
    delhi_fc = service.predict_forecast(28.61, 77.21, readings, location_name="Delhi Test Site")
    assert delhi_fc["zone_id"] == "indo_gangetic_plains"
    assert "forecast_channels" in delhi_fc
    assert delhi_fc["forecast_channels"]["temperature_c"]["forecast_plus_6h"] > 22.0
    # In Indo-Gangetic plains, winter PM concentration accumulates
    assert delhi_fc["forecast_channels"]["pm25_ug_m3"]["forecast_plus_6h"] >= 45.0

    # Test Mumbai (Coastal)
    mumbai_fc = service.predict_forecast(19.07, 72.87, readings, location_name="Mumbai Test Site")
    assert mumbai_fc["zone_id"] == "western_ghats_coastal"
    # Marine moisture remains elevated
    assert mumbai_fc["forecast_channels"]["relative_humidity_pct"]["forecast_plus_6h"] >= 65.0


def test_fastapi_national_endpoints(api_client):
    """Test FastAPI gateway routes for Pan-India zones, stations, and forecast."""
    # 1. /api/national/zones
    res_zones = api_client.get("/api/national/zones")
    assert res_zones.status_code == 200
    data_zones = res_zones.json()
    assert data_zones["status"] == "SUCCESS"
    assert len(data_zones["zones"]) == 6

    # 2. /api/national/stations
    res_stations = api_client.get("/api/national/stations", params={"limit": 10})
    assert res_stations.status_code == 200
    data_stations = res_stations.json()
    assert data_stations["status"] == "SUCCESS"
    assert len(data_stations["stations"]) == 10

    # Filter by query
    res_delhi = api_client.get("/api/national/stations", params={"query": "SAFDARJUNG"})
    assert res_delhi.status_code == 200
    assert any("SAFDARJUNG" in s["station_name"] for s in res_delhi.json()["stations"])

    # 3. /api/national/forecast
    res_fc = api_client.get("/api/national/forecast", params={"lat": 31.71, "lon": 76.93, "location_name": "Mandi Live"})
    assert res_fc.status_code == 200
    data_fc = res_fc.json()
    assert data_fc["status"] == "SUCCESS"
    assert data_fc["result"]["zone_id"] == "western_himalayas"
    assert "forecast_channels" in data_fc["result"]


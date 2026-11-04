"""Tests for the ESP32 Edge Inference Endpoint and Regional Physics Routing."""
import pytest
from fastapi.testclient import TestClient
from server.dashboard import create_app


@pytest.fixture
def client(tmp_path):
    db = tmp_path / "test_esp32.sqlite"
    app = create_app(db, mandi_data_dir=tmp_path / "cache")
    return TestClient(app)


def test_esp32_infer_arid_andhi_raw_line(client):
    # Research vector for Jaipur Andhi squall: ts, temp, rh, press, pm25, pm10, wind
    raw_line = "1767225600,30.5,22.0,971.2,240.0,1650.0,25.5"
    payload = {
        "raw_line": raw_line,
        "zone_id": "arid_northwest",
        "lat": 26.82,
        "lon": 75.81,
    }
    response = client.post("/api/national/esp32/infer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["target_hardware"] == "ESP32-S3 Dual-Core Xtensa LX7 @ 240MHz"
    assert data["runtime_language"] == "C++17 Header-Only (Zero Dynamic Allocations)"
    assert data["ram_heap_allocated_bytes"] == 0
    assert data["latency_us"] == 1420
    assert len(data["forecast_6h"]) == 6
    assert data["timestamp_utc"] == 1767225600

    diag = data["edge_diagnostics"]
    assert diag["zone"] == "arid_northwest"
    assert diag["state"] == "Rajasthan"
    assert diag["andhi_dust_storm_active"] is True
    assert diag["wind_alert"] == "SEVERE_WINDSTORM_WARNING"
    assert diag["air_density_kg_m3"] > 1.0
    assert diag["wind_power_density_w_m2"] > 8000.0
    assert "INF_OUT:" in data["serial_stream_line"]
    assert "lat_us=1420 ram_heap=0" in data["serial_stream_line"]


def test_esp32_infer_himalayan_cloudburst(client):
    payload = {
        "temperature_c": 16.0,
        "relative_humidity_pct": 94.0,
        "pressure_hpa": 910.0,
        "pm25_ug_m3": 15.0,
        "pm10_ug_m3": 25.0,
        "wind_speed_mps": 14.5,
        "zone_id": "western_himalayas",
        "lat": 31.71,
        "lon": 76.93,
    }
    response = client.post("/api/national/esp32/infer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    diag = data["edge_diagnostics"]
    assert diag["zone"] == "western_himalayas"
    assert diag["state"] == "Himachal Pradesh"
    assert diag["cloudburst_active"] is True
    assert diag["hazard_alert"] == "CLOUDBURST_EMERGENCY"


def test_national_forecast_with_custom_readings(client):
    response = client.get("/api/national/forecast?lat=26.82&lon=75.81&temp_c=32.0&rh_pct=25.0&wind_speed_mps=26.0&pm10_ug_m3=1400.0&pm25_ug_m3=220.0")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    result = data["result"]
    assert result["zone_id"] == "arid_northwest"
    assert "andhi_dust_storm_assessment" in result
    assert result["wind_storm_assessment"]["alert_level"] == "SEVERE_WINDSTORM_WARNING"

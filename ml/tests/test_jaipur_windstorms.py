"""Automated Test Suite for Jaipur & Arid Northwest Windstorms, Dust Storms (Andhi), and Heatwaves."""

from __future__ import annotations

import math
import numpy as np
import pytest
from starlette.testclient import TestClient

from ml.national.service import PanIndiaForecastingService, ZONES
from ml.national.jaipur_engine import (
    JaipurAridWindEngine,
    calculate_air_density,
    calculate_vapor_pressure_deficit,
    calculate_wind_power_density,
    classify_wind_storm,
    evaluate_andhi_dust_storm,
    evaluate_arid_heat_stress,
)
from ml.national.jaipur_scenarios import (
    JAIPUR_SCENARIOS,
    simulate_arid_wind_hazards,
)
from pathlib import Path
from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS
from server.dashboard import create_app

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def national_service():
    return PanIndiaForecastingService()


@pytest.fixture(scope="module")
def jaipur_engine():
    return JaipurAridWindEngine()


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "test_jaipur.sqlite"
    app = create_app(db_file)
    with TestClient(app) as test_client:
        yield test_client


def test_jaipur_ground_stations_and_geodetic_resolution(national_service):
    """Verify that Jaipur resolves to the Arid Northwest zone and has verified ground stations."""
    # Jaipur coordinates
    lat, lon = 26.8242, 75.8122
    zone = national_service.resolve_zone(lat, lon)
    assert zone.id == "arid_northwest"
    assert "dust_storm_andhi" in zone.dominant_hazards
    assert "wind_storms_gale_burst" in zone.dominant_hazards

    nearest = national_service.find_nearest_stations(lat, lon, limit=3)
    assert len(nearest) == 3
    # Nearest station should be the Jaipur IMD/NOAA site (INI0000VIJP or INMU0020391)
    first = nearest[0]
    assert "JAIPUR" in first["station_name"].upper()
    assert first["distance_km"] < 20.0
    assert first["climate_zone"] == "BSh"


def test_jaipur_arid_wind_engine_deterministic_forecast(jaipur_engine):
    """Verify 6-channel forecast generation and physical validity under arid conditions."""
    readings = {
        "temperature_c": 34.0,
        "relative_humidity_pct": 20.0,
        "pressure_hpa": 974.5,
        "pm25_ug_m3": 42.0,
        "pm10_ug_m3": 115.0,
        "wind_speed_mps": 5.2,
    }
    res = jaipur_engine.predict_jaipur_forecast(readings)
    assert res["region"] == "JAIPUR_AND_ARID_NORTHWEST"
    assert res["air_density_kg_m3"] > 1.0
    assert res["wind_power_density_w_m2"] > 0.0

    channels = res["forecast_channels"]
    for c in RAW_SENSOR_COLUMNS:
        assert c in channels
        curr = channels[c]["current"]
        fc = channels[c]["forecast_plus_6h"]
        assert PHYSICAL_RANGES[c][0] <= fc <= PHYSICAL_RANGES[c][1]
        assert math.isclose(channels[c]["delta"], round(fc - curr, 2), abs_tol=1e-2)

    # In fair weather arid regime, diurnal warming and RH drop are expected
    assert channels["temperature_c"]["forecast_plus_6h"] > readings["temperature_c"]
    assert channels["relative_humidity_pct"]["forecast_plus_6h"] < readings["relative_humidity_pct"]


def test_severe_windstorm_and_gale_burst_classification():
    """Verify classification thresholds for wind storms across the Beaufort/IMD scale."""
    # 1. Calm / light
    c1 = classify_wind_storm(5.0)
    assert c1["alert_level"] == "CALM_OR_MODERATE"
    assert c1["severity"] == "NORMAL"

    # 2. Strong Wind Watch (15 m/s = 54 km/h)
    c2 = classify_wind_storm(15.0)
    assert c2["alert_level"] == "STRONG_WIND_WATCH"
    assert c2["severity"] == "ADVISORY"

    # 3. Gale Squall Warning (22 m/s = 79.2 km/h)
    c3 = classify_wind_storm(22.0)
    assert c3["alert_level"] == "GALE_SQUALL_WARNING"
    assert c3["severity"] == "WARNING"

    # 4. Severe Windstorm Warning (26 m/s = 93.6 km/h)
    c4 = classify_wind_storm(26.0)
    assert c4["alert_level"] == "SEVERE_WINDSTORM_WARNING"
    assert c4["severity"] == "SEVERE"

    # 5. Extreme Gale Burst (32 m/s = 115.2 km/h)
    c5 = classify_wind_storm(32.0)
    assert c5["alert_level"] == "EXTREME_GALE_BURST_EMERGENCY"
    assert c5["severity"] == "CRITICAL"
    assert c5["estimated_gust_kmh"] > 140.0


def test_andhi_dust_storm_convective_diagnostic():
    """Verify detection of Rajasthan Andhi convective dust storms."""
    # Case A: Severe Andhi conditions
    andhi = evaluate_andhi_dust_storm(
        wind_speed_mps=25.5,
        pm10_ug_m3=1650.0,
        pm25_ug_m3=240.0,
        temp_c=30.5,
        rh_pct=22.0,
        pressure_drop_hpa=6.5,
        temp_drop_c=11.5
    )
    assert andhi["andhi_index"] >= 0.70
    assert andhi["category"] in ("SEVERE", "EXTREME")
    assert andhi["coarse_particulate_ratio"] >= 5.0
    assert "Andhi dust storm" in andhi["recommended_action"]

    # Case B: Calm sunny conditions
    calm = evaluate_andhi_dust_storm(
        wind_speed_mps=3.5,
        pm10_ug_m3=60.0,
        pm25_ug_m3=25.0,
        temp_c=28.0,
        rh_pct=35.0
    )
    assert calm["andhi_index"] < 0.25
    assert calm["status"] == "NORMAL_ARID_CONDITIONS"


def test_arid_heat_stress_and_loo_warning():
    """Verify Vapor Pressure Deficit and Loo heatwave emergency triggers."""
    # Loo condition: 47.5°C and 11% RH
    loo = evaluate_arid_heat_stress(temp_c=47.5, rh_pct=11.0)
    assert loo["status"] == "EXTREME_LOO_HEATWAVE_EMERGENCY"
    assert loo["risk_level"] == "EMERGENCY"
    assert loo["vapor_pressure_deficit_kpa"] > 8.0

    # Normal thermal: 32°C and 40% RH
    normal = evaluate_arid_heat_stress(temp_c=32.0, rh_pct=40.0)
    assert normal["status"] == "NOMINAL_ARID_THERMAL"
    assert normal["risk_level"] == "NORMAL"


def test_jaipur_scenarios_and_monte_carlo_simulation():
    """Verify research scenario vectors and bounded Monte Carlo execution."""
    assert len(JAIPUR_SCENARIOS) == 4
    for key in ("andhi_dust_storm", "extreme_gale_burst", "loo_heatwave", "calm_arid_diurnal"):
        assert key in JAIPUR_SCENARIOS
        sc = JAIPUR_SCENARIOS[key]
        for col in RAW_SENSOR_COLUMNS:
            assert col in sc["readings"]

    # Run Monte Carlo on Andhi vector
    sim = simulate_arid_wind_hazards(
        JAIPUR_SCENARIOS["andhi_dust_storm"]["readings"],
        draws=256,
        pressure_drop_hpa=6.5,
        temp_drop_c=11.5,
        seed=20261105
    )
    assert sim["status"] == "SUCCESS"
    assert sim["draws"] == 256
    fractions = sim["simulation_fractions"]
    assert fractions["andhi_dust_storm_active"]["fraction"] > 0.80
    assert fractions["severe_windstorm_exceedance"]["fraction"] > 0.80
    assert 0.0 <= fractions["andhi_dust_storm_active"]["standard_error"] <= 0.10


def test_fastapi_jaipur_endpoints(client):
    """Verify dedicated Jaipur and Arid Northwest REST endpoints in FastAPI."""
    # 1. /api/national/jaipur/wind-risk
    res_risk = client.get("/api/national/jaipur/wind-risk?wind_speed_mps=26.0&pm10_ug_m3=1400.0&temp_c=31.0")
    assert res_risk.status_code == 200
    data_risk = res_risk.json()
    assert data_risk["status"] == "SUCCESS"
    assert "assessment" in data_risk
    assert data_risk["assessment"]["wind_storm_assessment"]["alert_level"] == "SEVERE_WINDSTORM_WARNING"
    assert data_risk["assessment"]["andhi_dust_storm_assessment"]["category"] in ("SEVERE", "EXTREME")

    # 2. /api/national/jaipur/scenarios
    res_sc = client.get("/api/national/jaipur/scenarios")
    assert res_sc.status_code == 200
    data_sc = res_sc.json()
    assert data_sc["status"] == "SUCCESS"
    assert "andhi_dust_storm" in data_sc["scenarios"]

    # 3. /api/national/jaipur/simulate
    res_sim = client.get("/api/national/jaipur/simulate?scenario=andhi_dust_storm&draws=128")
    assert res_sim.status_code == 200
    data_sim = res_sim.json()
    assert data_sim["status"] == "SUCCESS"
    assert "simulation_fractions" in data_sim["simulation"]

    # 4. /api/national/forecast for Jaipur coordinates
    res_fc = client.get("/api/national/forecast?lat=26.8242&lon=75.8122&location_name=Jaipur")
    assert res_fc.status_code == 200
    data_fc = res_fc.json()["result"]
    assert data_fc["zone_id"] == "arid_northwest"
    assert "wind_storm_assessment" in data_fc
    assert "andhi_dust_storm_assessment" in data_fc
    assert "heat_stress_assessment" in data_fc


def test_esp32_jaipur_runtime_c_parity():
    """Verify that the embedded C++17 runtime matches the Python assessment."""
    import shutil
    import subprocess
    cxx = shutil.which("clang++") or shutil.which("g++")
    if not cxx:
        pytest.skip("C++ compiler not available for parity test")

    header_path = ROOT / "esp32/ml_integration/include/indra_jaipur_wind_runtime.h"
    assert header_path.is_file()

    cpp_code = f"""
    #include <iostream>
    #include <cassert>
    #include "{header_path}"

    int main() {{
        float raw[6] = {{30.5f, 22.0f, 971.2f, 240.0f, 1650.0f, 25.5f}};
        auto assessment = indra_jaipur::assess_jaipur(raw, 6.5f, 11.5f);
        assert(assessment.andhi.andhi_index >= 0.70f);
        assert(assessment.wind.alert_code == 3);
        assert(assessment.wind.wind_speed_kmh > 90.0f);
        std::cout << "OK";
        return 0;
    }}
    """
    tmp_bin = "/tmp/test_jaipur_cpp"
    res = subprocess.run([cxx, "-std=c++17", "-x", "c++", "-", "-o", tmp_bin],
                         input=cpp_code, text=True, capture_output=True)
    assert res.returncode == 0, f"Compilation failed: {res.stderr}"
    run_res = subprocess.run([tmp_bin], capture_output=True, text=True)
    assert run_res.returncode == 0
    assert run_res.stdout.strip() == "OK"
    Path(tmp_bin).unlink(missing_ok=True)


"""Test Research-Grounded Atmospheric Scenarios and Real Mandi API Model Evaluation.

Verifies:
1. Mandi Live API dataset evaluation with TabularV2 model.
2. Cloudburst research vector triggers 'cloudburst_like' pattern and elevated hazard fractions.
3. Snowstorm research vector triggers 'snowstorm' pattern and physical liquid suppression.
4. Rain Burst research vector triggers 'rainstorm' and 'rain' patterns with runoff sensitivity.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.himachal.hazard_scenarios import simulate
from ml.himachal.weather_categories import WeatherCategories, episode_features
from ml.india_mandi.tabular_v2 import TabularV2
from ml.scripts.test_research_hazards_and_mandi import build_research_vectors, MANDI_OBS_PATH
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS


@pytest.fixture(scope="module")
def research_vectors():
    return build_research_vectors()


@pytest.fixture(scope="module")
def weather_engine():
    return WeatherCategories()


@pytest.fixture(scope="module")
def tabular_model():
    return TabularV2()


def test_mandi_api_observations_exist_and_run_tabular_v2(tabular_model):
    """Verify TabularV2 produces valid, bounded +6h predictions on real Mandi observations."""
    assert MANDI_OBS_PATH.exists(), f"Missing Mandi observation archive: {MANDI_OBS_PATH}"
    df = pd.read_csv(MANDI_OBS_PATH, parse_dates=["timestamp_utc"])
    assert len(df) >= 720, f"Expected 720 hours in archive, found {len(df)}"

    preds = tabular_model.predict(df)
    assert len(preds) == len(df)

    latest = preds.iloc[-1]
    assert latest.status == "HYBRID_READY"
    assert latest.model_id == "india_mandi_tabular_v2"
    assert np.isfinite([latest["forecast_" + c] for c in RAW_SENSOR_COLUMNS]).all()

    # Physical bounds for Himachal mountain valley
    assert -10.0 <= latest.forecast_temperature_c <= 45.0
    assert 5.0 <= latest.forecast_relative_humidity_pct <= 100.0
    assert 800.0 <= latest.forecast_pressure_hpa <= 1050.0
    assert 0.0 <= latest.forecast_pm25_ug_m3 <= 500.0
    assert 0.0 <= latest.forecast_pm10_ug_m3 <= 800.0
    assert 0.0 <= latest.forecast_wind_speed_mps <= 35.0


def test_cloudburst_research_vector(research_vectors, weather_engine):
    """Verify IMD-standard cloudburst signature triggers cloudburst_like pattern & elevated hazard."""
    cb = research_vectors["cloudburst"]
    feat = episode_features(cb)
    scores = weather_engine.scores(feat)[0]

    # Category indices: 0: rain, 1: rainstorm, 2: snowstorm, 9: cloudburst_like
    cloudburst_idx = 9
    assert scores[cloudburst_idx] >= weather_engine.thresholds[cloudburst_idx]
    assert scores[cloudburst_idx] > 0.95, f"Expected high cloudburst score, got {scores[cloudburst_idx]}"

    # Run hazard simulation
    sim = simulate(cb, draws=1024)
    # Cloudburst fraction in wetter family should be significant (> 15%)
    assert sim["wetter"]["fraction"][0, 0] > 0.15
    # Flash-flood fraction in wetter family should exceed 50%
    assert sim["wetter"]["fraction"][0, 1] > 0.50


def test_snowstorm_research_vector(research_vectors, weather_engine):
    """Verify Western Disturbance blizzard vector triggers snowstorm pattern and liquid hazard suppression."""
    sn = research_vectors["snowstorm"]
    feat = episode_features(sn)
    scores = weather_engine.scores(feat)[0]

    snow_idx = 2
    assert scores[snow_idx] >= weather_engine.thresholds[snow_idx]
    assert scores[snow_idx] > 0.95, f"Expected high snowstorm score, got {scores[snow_idx]}"

    # Run hazard simulation: sub-zero temps must physically suppress liquid rainfall & runoff
    sim = simulate(sn, draws=1024)
    assert sim["central"]["fraction"][0, 0] <= 0.01  # Liquid cloudburst near zero
    assert sim["central"]["fraction"][0, 1] <= 0.02  # Liquid runoff near zero


def test_rain_burst_research_vector(research_vectors, weather_engine):
    """Verify monsoon deluge burst triggers rain and rainstorm patterns."""
    rb = research_vectors["rain_burst"]
    feat = episode_features(rb)
    scores = weather_engine.scores(feat)[0]

    rain_idx = 0
    rainstorm_idx = 1
    assert scores[rain_idx] >= weather_engine.thresholds[rain_idx]
    assert scores[rainstorm_idx] >= weather_engine.thresholds[rainstorm_idx]
    assert scores[rainstorm_idx] > 0.90, f"Expected high rainstorm score, got {scores[rainstorm_idx]}"

    # Run hazard simulation: central family flash-flood should be elevated (> 15%)
    sim = simulate(rb, draws=1024)
    assert sim["central"]["fraction"][0, 1] > 0.15
    assert sim["central"]["fraction"][0, 2] > 0.10


"""Research-grounded atmospheric scenario vectors and Monte Carlo simulation for Jaipur & Arid Northwest.

Models Rajasthan / Thar desert margin convective hazards:
1. Convective Dust Storms (Andhi) with mineral particulate explosion and downdraft cooling.
2. Violent Gale Windstorm Bursts with squall-line kinetic power density.
3. Arid Extreme Heatwaves (Loo) with hyper-elevated Vapor Pressure Deficit (VPD).
4. Baseline Arid Diurnal radiative heating.

Truth-in-advertising safeguard: Monte Carlo fractions are uncalibrated conditional simulation
fractions over physical prior distributions, NOT certified public weather warnings.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
import numpy as np

from ml.national.jaipur_engine import (
    calculate_air_density,
    calculate_vapor_pressure_deficit,
    calculate_wind_power_density,
    classify_wind_storm,
    evaluate_andhi_dust_storm,
    evaluate_arid_heat_stress,
    JaipurAridWindEngine,
)

# Ground-truth research atmospheric vectors for Jaipur & Arid Northwest
JAIPUR_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "andhi_dust_storm": {
        "scenario_id": "jaipur_andhi_dust_storm",
        "title": "Severe Pre-Monsoon Convective Dust Storm (Andhi)",
        "location": "Jaipur (26.82°N, 75.81°E, 382m DEM)",
        "climate_zone": "BSh (Hot Semi-Arid)",
        "meteorological_context": (
            "Intense pre-monsoon convective downdraft generating violent gust fronts (>90 km/h), "
            "massive desert crust lofting (PM10 > 1,500 ug/m3), evaporative cold-pool cooling (-11.5°C), "
            "and severe barometric plunge."
        ),
        "readings": {
            "temperature_c": 30.5,
            "relative_humidity_pct": 22.0,
            "pressure_hpa": 971.2,
            "pm25_ug_m3": 240.0,
            "pm10_ug_m3": 1650.0,
            "wind_speed_mps": 25.5,
        },
        "perturbation": {
            "pressure_drop_hpa": 6.5,
            "temp_drop_c": 11.5,
        },
        "expected_hazard": "ANDHI_DUST_STORM_ACTIVE",
        "expected_alert_level": "SEVERE_WINDSTORM_WARNING",
    },
    "extreme_gale_burst": {
        "scenario_id": "jaipur_extreme_gale_burst",
        "title": "Extreme Dry Squall & Gale Windstorm Burst",
        "location": "Jaipur Aerodrome / Sanganer (26.82°N, 75.80°E)",
        "climate_zone": "BSh (Hot Semi-Arid)",
        "meteorological_context": (
            "Violent convective dry microburst with sustained winds exceeding 31 m/s (111 km/h, Beaufort 11), "
            "gust factors exceeding 1.4x (155+ km/h), generating catastrophic kinetic power density (>16,000 W/m2)."
        ),
        "readings": {
            "temperature_c": 36.0,
            "relative_humidity_pct": 28.0,
            "pressure_hpa": 968.5,
            "pm25_ug_m3": 85.0,
            "pm10_ug_m3": 450.0,
            "wind_speed_mps": 31.0,
        },
        "perturbation": {
            "pressure_drop_hpa": 7.8,
            "temp_drop_c": 4.2,
        },
        "expected_hazard": "EXTREME_GALE_BURST_EMERGENCY",
        "expected_alert_level": "EXTREME_GALE_BURST_EMERGENCY",
    },
    "loo_heatwave": {
        "scenario_id": "jaipur_loo_heatwave",
        "title": "Hyper-Arid Extreme Heatwave (Loo)",
        "location": "Jaipur Urban Core (26.92°N, 75.83°E)",
        "climate_zone": "BSh (Hot Semi-Arid)",
        "meteorological_context": (
            "Peak summer afternoon insolation causing extreme surface heating (47.8°C), hyper-arid relative "
            "humidity (10.5%), and extreme Vapor Pressure Deficit (>9.5 kPa) causing acute desert heat stress."
        ),
        "readings": {
            "temperature_c": 47.8,
            "relative_humidity_pct": 10.5,
            "pressure_hpa": 973.0,
            "pm25_ug_m3": 65.0,
            "pm10_ug_m3": 180.0,
            "wind_speed_mps": 7.2,
        },
        "perturbation": {
            "pressure_drop_hpa": 0.5,
            "temp_drop_c": 0.0,
        },
        "expected_hazard": "EXTREME_LOO_HEATWAVE_EMERGENCY",
        "expected_alert_level": "CALM_OR_MODERATE",
    },
    "calm_arid_diurnal": {
        "scenario_id": "jaipur_calm_arid_diurnal",
        "title": "Nominal Arid Fair-Weather Diurnal Cycle",
        "location": "Jaipur Baseline Station (26.8242°N, 75.8122°E)",
        "climate_zone": "BSh (Hot Semi-Arid)",
        "meteorological_context": (
            "Nominal post-sunrise arid warming with light thermal wind, moderate coarse particulate "
            "background, and nominal diurnal pressure trends."
        ),
        "readings": {
            "temperature_c": 28.5,
            "relative_humidity_pct": 28.0,
            "pressure_hpa": 978.5,
            "pm25_ug_m3": 35.0,
            "pm10_ug_m3": 85.0,
            "wind_speed_mps": 3.8,
        },
        "perturbation": {
            "pressure_drop_hpa": 0.0,
            "temp_drop_c": 0.0,
        },
        "expected_hazard": "NORMAL_ARID_CONDITIONS",
        "expected_alert_level": "CALM_OR_MODERATE",
    },
}


def simulate_arid_wind_hazards(
    readings: Dict[str, float],
    draws: int = 1024,
    seed: int = 20261105,
    pressure_drop_hpa: float = 0.0,
    temp_drop_c: float = 0.0,
) -> Dict[str, Any]:
    """Execute bounded Monte Carlo simulation over arid windstorm and dust hazards.
    
    Draws perturbations from synthetic atmospheric priors to estimate conditional exceedance
    fractions for:
    1. Severe Windstorm (> 20 m/s / 72 km/h)
    2. Violent Gale Burst (> 28 m/s / 100 km/h)
    3. Andhi Dust Storm Trigger (Composite index >= 0.55)
    4. Extreme Loo Heatwave (Temp >= 43°C & RH <= 25%)
    """
    if draws < 64 or draws > 4096:
        raise ValueError("draws must be between 64 and 4096")

    rng = np.random.default_rng(seed)
    base_t = float(readings.get("temperature_c", 32.0))
    base_rh = float(readings.get("relative_humidity_pct", 25.0))
    base_p = float(readings.get("pressure_hpa", 975.0))
    base_pm25 = float(readings.get("pm25_ug_m3", 45.0))
    base_pm10 = float(readings.get("pm10_ug_m3", 120.0))
    base_wind = float(readings.get("wind_speed_mps", 4.5))

    # Perturbation distributions modeling atmospheric turbulence
    wind_draws = np.maximum(0.0, base_wind + rng.normal(0.0, base_wind * 0.18, draws))
    pm10_draws = np.maximum(5.0, base_pm10 + rng.normal(0.0, base_pm10 * 0.22, draws))
    pm25_draws = np.maximum(2.0, base_pm25 + rng.normal(0.0, base_pm25 * 0.15, draws))
    t_draws = base_t + rng.normal(0.0, 1.2, draws)
    rh_draws = np.clip(base_rh + rng.normal(0.0, 3.5, draws), 2.0, 98.0)
    p_draws = base_p + rng.normal(0.0, 1.5, draws)

    # Threshold exceedance counters
    severe_wind_count = int(np.sum(wind_draws >= 20.0))
    gale_burst_count = int(np.sum(wind_draws >= 28.0))
    loo_heatwave_count = int(np.sum((t_draws >= 43.0) & (rh_draws <= 25.0)))

    # Andhi index draws
    coarse_ratios = pm10_draws / pm25_draws
    wind_scores = np.clip((wind_draws - 10.0) / 15.0, 0.0, 1.0)
    pm10_scores = np.clip((pm10_draws - 200.0) / 1000.0, 0.0, 1.0)
    ratio_scores = np.clip((coarse_ratios - 2.5) / 3.0, 0.0, 1.0)
    rh_scores = np.clip((40.0 - rh_draws) / 30.0, 0.0, 1.0)
    downdraft_val = (max(0.0, temp_drop_c) / 8.0) + (max(0.0, pressure_drop_hpa) / 5.0)
    andhi_scores = (
        0.30 * wind_scores +
        0.30 * pm10_scores +
        0.15 * ratio_scores +
        0.10 * rh_scores +
        0.15 * min(1.0, downdraft_val)
    )
    andhi_active_count = int(np.sum(andhi_scores >= 0.55))

    def stats(count: int) -> Dict[str, float]:
        frac = count / draws
        se = math.sqrt(frac * (1.0 - frac) / draws) if draws > 0 else 0.0
        return {"fraction": round(frac, 4), "standard_error": round(se, 4)}

    engine = JaipurAridWindEngine()
    deterministic = engine.predict_jaipur_forecast(
        readings,
        pressure_drop_hpa=pressure_drop_hpa,
        temp_drop_c=temp_drop_c
    )

    return {
        "status": "SUCCESS",
        "draws": draws,
        "seed": seed,
        "deterministic_forecast": deterministic,
        "simulation_fractions": {
            "severe_windstorm_exceedance": stats(severe_wind_count),
            "violent_gale_burst_exceedance": stats(gale_burst_count),
            "andhi_dust_storm_active": stats(andhi_active_count),
            "loo_heatwave_active": stats(loo_heatwave_count),
        },
        "truth_in_advertising_notice": (
            "Conditional Monte Carlo fractions derived from physical perturbation priors. "
            "Values are research simulation indicators, not certified municipal disaster alarms."
        )
    }


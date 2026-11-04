#!/usr/bin/env python3
"""Evaluate INDRA Machine Learning Model & Hazard Scenarios on Real Mandi API & Research Vectors.

Covers:
1. Live Mandi API Observation (+6h forecast inference via india_mandi_tabular_v2).
2. Cloudburst Research Vector (IMD convective threshold exceedance, severe downdraft & washout).
3. Snowstorm / Himalayan Blizzard Research Vector (Western Disturbance sub-zero gale).
4. Rain Burst / Monsoon Deluge Research Vector (Intense precipitation burst & runoff trigger).

Literature Citations:
- Singh & Thapliyal (2022), MAUSAM 73(1): 100 mm/h convective threshold definition.
- Shekhar et al. (2010), Cold Reg. Sci. Tech.: Western Disturbance winter gale and sub-zero blizzard.
- Dahal & Hasegawa (2008), Geomorphology: Himalayan intensity-duration empirical rainfall trigger.
- IMD Monsoon Criteria: Extreme localized rain burst (30-50+ mm/h) and rapid barometric trough.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ml.himachal.hazard_scenarios import HazardScenarios, simulate
from ml.himachal.weather_categories import WeatherCategories, CATEGORIES, episode_features
from ml.india_mandi.tabular_v2 import TabularV2
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS

MANDI_OBS_PATH = ROOT / "ml/data/himachal/mandi_api/2026-09-25_2026-10-24/observations.csv"
OUTPUT_JSON = ROOT / "ml/reports/research_hazards_and_mandi_api_evaluation.json"


def build_research_vectors():
    """Build 7-hour 6-channel episodes based on documented research literature."""
    
    # 1. Cloudburst: IMD criteria (100 mm/h convective threshold, rapid pressure drop, cold downdraft, PM washout)
    # Citation: Singh & Thapliyal (2022) MAUSAM; Das et al. (2020)
    cb = np.zeros((1, 7, 6))
    for i in range(6):
        # 6 hours prior: steady moistening, pressure gradual drop from 930.0 to 927.5 hPa
        cb[0, i] = [22.0 - i * 0.4, 70.0 + i * 4.0, 930.0 - i * 0.5, 32.0 - i * 1.0, 55.0 - i * 2.0, 3.0 + i * 1.5]
    # Current (Hour 7): intense cold downdraft (17.5°C, dt=-2.5°C <= -2.0), RH 96%, 1h pressure plunge (925.0 hPa, dp=-2.5 hPa <= -1.5), gust 14.5 m/s, PM rain washout
    cb[0, 6] = [17.5, 96.0, 925.0, 10.0, 16.0, 14.5]

    # 2. Snowstorm: Western Disturbance blizzard (Sub-zero cold, saturation, deep trough, gale winds)
    # Citation: Shekhar et al. (2010) Cold Regions Sci. Tech.; Dimri et al. (2015) Rev. Geophys.
    sn = np.zeros((1, 7, 6))
    for i in range(6):
        # 6 hours prior: sub-zero drop, barometric drop as Western Disturbance arrives
        sn[0, i] = [-1.0 - i * 0.6, 82.0 + i * 2.0, 880.0 - i * 0.8, 18.0, 28.0, 6.0 + i * 1.2]
    # Current (Hour 7): -5.0°C, RH 94%, pressure drop -6.0 hPa (874.0 hPa), wind 13.5 m/s, PM clean air
    sn[0, 6] = [-5.0, 94.0, 874.0, 8.0, 12.0, 13.5]

    # 3. Rain Burst: Monsoon flash downpour (High temperature, saturation, rapid cooling, high gust, PM washout)
    # Citation: Bhan et al. (2015); IMD heavy rainfall burst criteria
    rb = np.zeros((1, 7, 6))
    for i in range(6):
        rb[0, i] = [24.0, 78.0 + i * 2.0, 928.0 - i * 0.6, 30.0, 50.0, 5.0 + i * 1.0]
    # Current (Hour 7): 20.0°C (rapid -4.0°C cooling), RH 92%, pressure drop -3.6 hPa (924.4 hPa), gust 11.5 m/s, PM washout
    rb[0, 6] = [20.0, 92.0, 924.4, 12.0, 20.0, 11.5]

    return {
        "cloudburst": cb,
        "snowstorm": sn,
        "rain_burst": rb,
    }


def evaluate_mandi_api():
    """Run TabularV2 forecast and hazard analysis on actual Mandi API observations."""
    if not MANDI_OBS_PATH.exists():
        raise FileNotFoundError(f"Missing Mandi observation archive: {MANDI_OBS_PATH}")

    df = pd.read_csv(MANDI_OBS_PATH, parse_dates=["timestamp_utc"])
    model = TabularV2()
    preds = model.predict(df)

    latest_obs = df.iloc[-1]
    latest_pred = preds.iloc[-1]

    # Extract last 7 hours for pattern & hazard engines
    mandi_last7 = df.iloc[-7:][RAW_SENSOR_COLUMNS].to_numpy(float)
    mandi_ep = mandi_last7[None, :, :]

    wc = WeatherCategories()
    feat = episode_features(mandi_ep)
    scores = wc.scores(feat)[0]
    category_matches = {
        cat: {
            "score": float(scores[i]),
            "threshold": float(wc.thresholds[i]),
            "matched": bool(scores[i] >= wc.thresholds[i]),
        }
        for i, cat in enumerate(CATEGORIES.keys())
    }

    sim_res = simulate(mandi_ep, draws=2048)
    hazard_fractions = {
        family: {
            "cloudburst_pct": float(sim_res[family]["fraction"][0, 0] * 100),
            "flash_flood_pct": float(sim_res[family]["fraction"][0, 1] * 100),
            "landslide_pct": float(sim_res[family]["fraction"][0, 2] * 100),
        }
        for family in ["drier", "central", "wetter"]
    }

    forecast_outputs = {}
    for c in RAW_SENSOR_COLUMNS:
        forecast_outputs[c] = {
            "observed_current": float(latest_obs[c]),
            "forecast_plus_6h": float(latest_pred["forecast_" + c]),
            "delta": float(latest_pred["forecast_" + c] - latest_obs[c]),
        }

    return {
        "timestamp_utc": str(latest_obs["timestamp_utc"]),
        "forecast_valid_utc": str(latest_pred["forecast_timestamp_utc"]),
        "model_id": str(latest_pred["model_id"]),
        "model_status": str(latest_pred["status"]),
        "forecast_channels": forecast_outputs,
        "weather_categories": category_matches,
        "hazard_simulations": hazard_fractions,
    }


def evaluate_research_scenarios():
    """Evaluate WeatherCategories and HazardScenarios on research-grounded atmospheric vectors."""
    vectors = build_research_vectors()
    wc = WeatherCategories()
    results = {}

    for name, ep in vectors.items():
        feat = episode_features(ep)
        scores = wc.scores(feat)[0]
        category_matches = {
            cat: {
                "score": float(scores[i]),
                "threshold": float(wc.thresholds[i]),
                "matched": bool(scores[i] >= wc.thresholds[i]),
            }
            for i, cat in enumerate(CATEGORIES.keys())
        }

        sim_res = simulate(ep, draws=2048)
        hazard_fractions = {
            family: {
                "cloudburst_pct": float(sim_res[family]["fraction"][0, 0] * 100),
                "flash_flood_pct": float(sim_res[family]["fraction"][0, 1] * 100),
                "landslide_pct": float(sim_res[family]["fraction"][0, 2] * 100),
            }
            for family in ["drier", "central", "wetter"]
        }

        # Vector summary
        cur = ep[0, -1]
        results[name] = {
            "current_vector": {
                "temperature_c": float(cur[0]),
                "relative_humidity_pct": float(cur[1]),
                "pressure_hpa": float(cur[2]),
                "pm25_ug_m3": float(cur[3]),
                "pm10_ug_m3": float(cur[4]),
                "wind_speed_mps": float(cur[5]),
            },
            "weather_categories": category_matches,
            "hazard_simulations": hazard_fractions,
        }

    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_JSON, help="Output path for JSON report")
    args = parser.parse_args()

    print("=" * 70)
    print("  INDRA RESEARCH HAZARDS & MANDI API MODEL EVALUATION")
    print("=" * 70)

    # 1. Mandi API evaluation
    print("\n▶ [1/2] Evaluating Mandi live observation dataset with TabularV2...")
    mandi_results = evaluate_mandi_api()
    print(f"  • Observation Time: {mandi_results['timestamp_utc']}")
    print(f"  • Model Status:     {mandi_results['model_status']} (ID: {mandi_results['model_id']})")
    print(f"  • 6h Forecast Temp: {mandi_results['forecast_channels']['temperature_c']['observed_current']:.1f}°C -> {mandi_results['forecast_channels']['temperature_c']['forecast_plus_6h']:.1f}°C ({mandi_results['forecast_channels']['temperature_c']['delta']:+.1f}°C)")
    print(f"  • 6h Forecast RH:   {mandi_results['forecast_channels']['relative_humidity_pct']['observed_current']:.1f}% -> {mandi_results['forecast_channels']['relative_humidity_pct']['forecast_plus_6h']:.1f}% ({mandi_results['forecast_channels']['relative_humidity_pct']['delta']:+.1f}%)")
    print(f"  • Central Family Hazards: Cloudburst {mandi_results['hazard_simulations']['central']['cloudburst_pct']:.2f}%, Flash-Flood {mandi_results['hazard_simulations']['central']['flash_flood_pct']:.2f}%, Landslide {mandi_results['hazard_simulations']['central']['landslide_pct']:.2f}%")

    # 2. Research scenarios
    print("\n▶ [2/2] Evaluating Cloudburst, Snowstorm & Rain Burst Research Vectors...")
    research_results = evaluate_research_scenarios()

    for name in ["cloudburst", "snowstorm", "rain_burst"]:
        r = research_results[name]
        v = r["current_vector"]
        matched_cats = [c for c, data in r["weather_categories"].items() if data["matched"]]
        print(f"\n  • [{name.upper()}] Vector (T={v['temperature_c']}°C, RH={v['relative_humidity_pct']}%, P={v['pressure_hpa']}hPa, W={v['wind_speed_mps']}m/s)")
        print(f"    Matched Categories: {matched_cats}")
        print(f"    Simulated Central Hazards: Cloudburst {r['hazard_simulations']['central']['cloudburst_pct']:.2f}%, Flash-Flood {r['hazard_simulations']['central']['flash_flood_pct']:.2f}%, Landslide {r['hazard_simulations']['central']['landslide_pct']:.2f}%")

    # Save output JSON
    payload = {
        "metadata": {
            "evaluation_timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
            "methodology": "Research-grounded synthetic atmospheric vectors and real Mandi observation dataset",
            "safety_boundary": "Uncalibrated conditional Monte Carlo simulation fractions and pattern proxies; not real public hazard warnings or event probabilities.",
        },
        "mandi_live_observation": mandi_results,
        "research_scenarios": research_results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2))
    print(f"\n✓ Saved evaluation artifact to: {args.output}")


if __name__ == "__main__":
    main()

"""Research-informed synthetic scenarios, NOT calibrated event probabilities.

Monte Carlo fractions are conditional on invented, documented rain/soil/catchment
priors. They cannot establish real cloudburst, flood or landslide accuracy.
Only past six-channel measurements enter inference; simulated future rain and
latent hydrology generate outcomes, never masquerading as observed labels.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

from ml.himachal.weather_categories import BOUNDS, episode_features
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "ml/configs/himalayan_synthetic_scenarios_v1.json"
TARGETS = {
    "cloudburst": "Cloudburst rainfall threshold",
    "flash_flood": "Flash-flood runoff scenario",
    "landslide": "Landslide rainfall trigger",
}


def rainfall_strength(x, config):
    """Assumed surface-weather link; coefficients are not literature estimates."""
    x = np.asarray(x, float)
    t, rh, _, _, _, wind, dt, _, _, _, _, _, dp6 = x.T
    c = config["rain_link"]
    return expit(
        c["intercept"]
        + c["humidity"] * (rh - 70) / 20
        + c["pressure_fall"] * np.clip(-dp6 / 3, -2, 3)
        + c["wind"] * np.clip(wind / 10, 0, 3)
        + c["cooling"] * np.clip(-dt / 3, -2, 3)
    ) * expit((t - 1) / 2)  # Assumed liquid phase fraction, not snow detection.


def event_outcomes(
    rain, wetness, storage, dry_c, capacity, area, tc, susceptible, config
):
    """Derive three synthetic outcomes from native half-hour rainfall mm/h.

    Rational Method conversion: (mm/h)*(km^2) = (1/3.6) m^3/s.
    Landslide output is threshold exceedance on assumed susceptible terrain.
    It is not the USGS TRIGRS slope-stability model.
    """
    rain = np.asarray(rain, float)
    if rain.shape[-1] != 12 or not np.isfinite(rain).all() or (rain < 0).any():
        raise ValueError("Twelve finite nonnegative half-hour rates required")
    accumulated = np.cumsum(rain * 0.5, axis=-1)
    moisture = np.clip(wetness[..., None] + accumulated / storage[..., None], 0, 1)
    runoff_c = (
        dry_c[..., None]
        + (config["latent_ranges"]["wet_runoff_coefficient"] - dry_c[..., None])
        * moisture
    )
    cloud = ((rain[..., :-1] + rain[..., 1:]) * 0.5).max(-1) >= config[
        "cloudburst_threshold_mm_in_1h"
    ]
    flood = np.zeros(rain.shape[:-1], bool)
    for ticks in (1, 2, 4):  # Average rain over each assumed concentration time.
        mean = np.stack(
            [rain[..., i : i + ticks].mean(-1) for i in range(13 - ticks)], -1
        )
        runoff = (1 / 3.6) * runoff_c[..., ticks - 1 :] * mean * area[..., None]
        flood |= (tc == ticks * 0.5) & (runoff.max(-1) >= capacity * area)
    trigger = np.zeros_like(flood)
    for hours in config["landslide_duration_hours"]:
        ticks = 2 * hours
        means = np.stack(
            [rain[..., i : i + ticks].mean(-1) for i in range(13 - ticks)], -1
        )
        threshold = (
            config["landslide_id_coefficient"]
            * hours ** config["landslide_id_exponent"]
        )
        # Wetness correction is an explicit assumption, not Dahal's fitted law.
        threshold = threshold * (1.4 - 0.7 * moisture[..., ticks - 1 :])
        trigger |= (means >= threshold).any(-1)
    return np.stack([cloud, flood, trigger & susceptible], -1)


def simulate(episodes, *, seed=20261021, draws=2048, config=None, retain=False):
    """Generate paired latent worlds under three unweighted assumption families."""
    config = config or json.loads(CONFIG.read_text())
    episodes = np.asarray(episodes, float)
    x = episode_features(episodes)
    if ((episodes < BOUNDS[:, 0]) | (episodes > BOUNDS[:, 1])).any() or (
        episodes[:, :, 3] > episodes[:, :, 4]
    ).any():
        raise ValueError("Episode outside synthetic six-channel domain")
    if type(draws) is not int or not 32 <= draws <= 8192 or len(x) > 256:
        raise ValueError(
            "Bounded simulation requires 32..8192 draws and <=256 episodes"
        )
    r = np.random.default_rng(seed)
    shape = (len(x), draws)
    c = config["rain_link"]
    strength = rainfall_strength(x, config)[:, None]
    active = r.random(shape) < strength
    base = np.exp(
        c["log_rate_intercept"]
        + c["log_rate_strength"] * strength
        + c["log_rate_sigma"] * r.normal(size=shape)
    )
    ar = np.zeros(shape)
    rain = []
    for _ in range(12):
        ar = c["temporal_ar"] * ar + np.sqrt(1 - c["temporal_ar"] ** 2) * r.normal(
            size=shape
        )
        rain.append(base * np.exp(0.45 * ar) * active)
    rain = np.stack(rain, -1)
    lr = config["latent_ranges"]
    wet_u, capacity_u, susceptibility_u = r.random((3, *shape))
    storage = r.uniform(*lr["soil_storage_mm"], shape)
    dry_c = r.uniform(*lr["dry_runoff_coefficient"], shape)
    area = r.uniform(*lr["catchment_area_km2"], shape)
    tc = r.choice(lr["concentration_time_hours"], shape)
    families = {}
    for name, f in config["families"].items():
        wet = f["soil_wetness"][0] + np.ptp(f["soil_wetness"]) * wet_u
        capacity = (
            f["capacity_m3_s_km2"][0] + np.ptp(f["capacity_m3_s_km2"]) * capacity_u
        )
        scaled_rain = np.minimum(rain * f["rain_multiplier"], c["rain_rate_cap_mm_h"])
        outcomes = event_outcomes(
            scaled_rain,
            wet,
            storage,
            dry_c,
            capacity,
            area,
            tc,
            susceptibility_u < f["susceptible_fraction"],
            config,
        )
        fraction = outcomes.mean(1)
        families[name] = {
            "fraction": fraction,
            "mc_standard_error": np.sqrt(fraction * (1 - fraction) / draws),
        }
        if retain:
            families[name].update(
                rain_mm_h=scaled_rain,
                outcomes=outcomes,
                soil_wetness=wet,
                storage_mm=storage,
                dry_runoff_coefficient=dry_c,
                capacity_m3_s_km2=capacity,
                catchment_area_km2=area,
                concentration_time_hours=tc,
                susceptible=susceptibility_u < f["susceptible_fraction"],
            )
    return families


class HazardScenarios:
    """Dashboard adapter: deterministic scenarios with no alert/probability promotion."""

    def __init__(self, config_path=CONFIG):
        raw = Path(config_path).read_bytes()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self.implementation_sha256 = hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest()
        self.config = json.loads(raw)
        if (
            self.config["id"] != "himalayan_synthetic_scenarios_v1"
            or self.config["field_validated"] is not False
        ):
            raise ValueError("Invalid synthetic scenario identity")

    def predict(self, history, cadence):
        """Require exact, complete native history; never interpolate missing inputs."""
        result = {
            "model_id": self.config["id"],
            "config_sha256": self.sha256,
            "implementation_sha256": self.implementation_sha256,
            "status": "UNAVAILABLE",
            "evidence": "SYNTHETIC_ASSUMPTION_MODEL",
            "score_kind": "CONDITIONAL_SIMULATION_FRACTION",
            "horizon_hours": 6,
            "field_validated": False,
            "calibrated": False,
            "probability": None,
            "public_alerts_enabled": False,
            "targets": [],
            "missing_features": [],
            "reason": "Six complete hours of readings are needed.",
        }
        if type(cadence) is not int or cadence < 1 or cadence > 3600 or 3600 % cadence:
            raise ValueError("Native cadence must divide one hour")
        if not history:
            return result
        frame = pd.DataFrame(history)
        required = {"timestamp", *RAW_SENSOR_COLUMNS}
        if not required.issubset(frame.columns):
            result["missing_features"] = sorted(required - set(frame.columns))
            return result
        timestamps = pd.to_datetime(frame.timestamp, utc=True, errors="coerce")
        if timestamps.isna().any() or timestamps.duplicated().any():
            raise ValueError("Unique valid timestamps required")
        frame = frame.assign(timestamp=timestamps).set_index("timestamp").sort_index()
        end = frame.index[-1]
        if not all((end.value - t.value) % (cadence * 10**9) == 0 for t in frame.index):
            result["reason"] = "History must follow the declared native cadence."
            return result
        expected = pd.date_range(
            end - pd.Timedelta(hours=6), end, freq=pd.Timedelta(seconds=cadence)
        )
        native = frame.reindex(expected)[RAW_SENSOR_COLUMNS].apply(
            pd.to_numeric, errors="coerce"
        )
        if not np.isfinite(native.to_numpy()).all():
            result["missing_features"] = ["six_complete_hours_of_native_measurements"]
            return result
        values = native.to_numpy()
        if ((values < BOUNDS[:, 0]) | (values > BOUNDS[:, 1])).any() or (
            values[:, 3] > values[:, 4]
        ).any():
            result.update(
                status="OUTSIDE_SYNTHETIC_DOMAIN",
                reason="Readings fall outside the simulation domain.",
            )
            return result
        hourly = native.loc[
            pd.date_range(end - pd.Timedelta(hours=6), end, freq="h")
        ].to_numpy()[None]
        identity = hashlib.sha256(
            hourly.astype("<f8").tobytes() + self.sha256.encode()
        ).digest()
        seed = int.from_bytes(identity[:8], "little")
        runs = simulate(
            hourly, seed=seed, draws=self.config["draws"], config=self.config
        )
        for j, (key, name) in enumerate(TARGETS.items()):
            fractions = {k: float(v["fraction"][0, j]) for k, v in runs.items()}
            result["targets"].append(
                dict(
                    id=key,
                    name=name,
                    **{key + "_risk_uncal": fractions["central"]},
                    scenario_fraction=fractions["central"],
                    assumption_range=[min(fractions.values()), max(fractions.values())],
                    families=fractions,
                    probability=None,
                    mc_standard_error=float(runs["central"]["mc_standard_error"][0, j]),
                )
            )
        result.update(
            status="SYNTHETIC_SCENARIOS_ONLY",
            reason="Fractions of simulated outcomes, conditional on assumed rainfall, soil and drainage.",
            observation_timestamp=end.isoformat(),
            forecast_timestamp=(end + pd.Timedelta(hours=6)).isoformat(),
            draws_per_family=self.config["draws"],
            seed=seed,
            unknown_drivers=[
                "actual_rainfall",
                "soil_wetness",
                "terrain_susceptibility",
                "catchment_capacity",
            ],
            range_kind="ASSUMPTION_SENSITIVITY_NOT_CONFIDENCE_INTERVAL",
        )
        return result

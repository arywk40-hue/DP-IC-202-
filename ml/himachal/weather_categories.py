"""Synthetic-trained current sensor-pattern categories, not event probabilities.

No independently observed event labels were used. Scores describe agreement
with engineering proxy categories; a non-match does not establish safe weather.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.data import sha256

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "ml/models/himachal_sensor_patterns_v1"
SCHEMA = "indra_synthetic_sensor_patterns_v1"
CATEGORIES = {
    "rain": "Rain-like pattern",
    "rainstorm": "Rainstorm pattern",
    "snowstorm": "Snowstorm pattern",
    "heatwave_like": "Heat stress / heatwave-like",
    "fog": "Fog-like pattern",
    "frost": "Frost-like pattern",
    "dust_storm": "Dust storm pattern",
    "smoke": "Smoke / pollution pattern",
    "wildfire_weather": "Hot / dry / windy pattern",
    "cloudburst_like": "Cloudburst-like sensor pattern",
}
FEATURES = [
    *RAW_SENSOR_COLUMNS,
    *[c + "_delta_1h" for c in RAW_SENSOR_COLUMNS],
    "pressure_hpa_delta_6h",
]
BOUNDS = np.array(
    [[-25, 50], [5, 100], [550, 1050], [0, 700], [1, 1500], [0, 35]], float
)


def episode_features(values):
    """Seven exact hourly snapshots, six channels in canonical order."""
    a = np.asarray(values, float)
    if a.ndim != 3 or a.shape[1:] != (7, 6) or not np.isfinite(a).all():
        raise ValueError("Complete seven-hour six-channel episodes required")
    return np.column_stack([a[:, -1], a[:, -1] - a[:, -2], a[:, -1, 2] - a[:, 0, 2]])


def proxy_labels(x):
    """Engineering definitions for synthetic learning, NOT IMD hazard definitions."""
    t, rh, _, pm25, pm10, w, dt, _, dp, d25, d10, _, p6 = np.asarray(x).T
    wash = (d25 <= -5) & (d10 <= -10)
    labels = [
        (rh >= 85) & (p6 <= -1.5) & (t > 3) & wash,
        (rh >= 80) & (p6 <= -3) & (dt <= -3) & (w >= 10) & (t > 3),
        (t <= 1) & (rh >= 85) & (w >= 9) & (p6 <= -3),
        t >= 35,
        (rh >= 95) & (w < 1.5) & (t <= 25),
        (t <= 0) & (w < 2),
        (w >= 8) & (pm10 >= 250) & (pm25 / np.maximum(pm10, 1) <= 0.35) & (rh < 40),
        (pm25 >= 150) & (pm25 / np.maximum(pm10, 1) >= 0.7) & (rh < 60),
        (t >= 30) & (rh <= 25) & (w >= 5),
        (rh >= 90) & (dp <= -1.5) & (dt <= -2) & (w >= 10) & wash,
    ]
    return np.column_stack(labels).astype(int)


def synthetic_episodes(n, seed):
    """Sample independently seeded episodes and overlapping proxy categories."""
    r = np.random.default_rng(seed)
    z = r.integers(0, 11, n)
    z[r.random(n) < 0.3] = 0  # Broad counterexamples, not just separated prototypes.
    cur = np.column_stack(
        [
            r.uniform(-15, 44, n),
            r.uniform(10, 99, n),
            r.uniform(650, 1020, n),
            r.lognormal(np.log(35), 0.7, n),
            np.zeros(n),
            r.uniform(0.1, 15, n),
        ]
    )
    cur[:, 4] = cur[:, 3] + r.lognormal(np.log(30), 0.7, n)
    d1 = r.normal(0, [1, 4, 0.5, 8, 12, 1], (n, 6))
    d6 = r.normal(0, [3, 12, 2, 20, 30, 3], (n, 6))
    for k in range(1, 11):
        mask = z == k
        count = int(mask.sum())

        def uniform(low, high, count=count):
            return r.uniform(low, high, count)

        if k in (1, 2, 3, 10):
            cur[mask, 0] = uniform(-10, 0.8) if k == 3 else uniform(8, 28)
            cur[mask, 1] = uniform(85 if k in (1, 3) else 80 if k == 2 else 90, 100)
            cur[mask, 3] = uniform(8, 35)
            cur[mask, 4] = cur[mask, 3] + uniform(10, 35)
            cur[mask, 5] = uniform(2, 7) if k == 1 else uniform(9 if k == 3 else 10, 25)
            d6[mask, 2] = -uniform(3, 10)
            d1[mask, 3] = -uniform(8, 40)
            d1[mask, 4] = -uniform(15, 70)
            d1[mask, 0] = -uniform(3, 8) if k in (2, 10) else uniform(-1, 1)
            d1[mask, 2] = -uniform(1.7, 4) if k == 10 else uniform(-1.3, 0.2)
        elif k == 4:
            cur[mask, 0] = uniform(35, 47)
            cur[mask, 1] = uniform(10, 75)
        elif k == 5:
            cur[mask, 0] = uniform(0, 20)
            cur[mask, 1] = uniform(96, 100)
            cur[mask, 5] = uniform(0.05, 1.2)
        elif k == 6:
            cur[mask, 0] = uniform(-12, -0.2)
            cur[mask, 5] = uniform(0.05, 1.8)
        elif k == 7:
            cur[mask, 1] = uniform(10, 35)
            cur[mask, 5] = uniform(9, 25)
            cur[mask, 4] = uniform(300, 1100)
            cur[mask, 3] = cur[mask, 4] * uniform(0.1, 0.3)
        elif k == 8:
            cur[mask, 1] = uniform(15, 55)
            cur[mask, 3] = uniform(170, 500)
            cur[mask, 4] = cur[mask, 3] / uniform(0.75, 0.98)
        elif k == 9:
            cur[mask, 0] = uniform(30, 45)
            cur[mask, 1] = uniform(10, 24)
            cur[mask, 5] = uniform(6, 15)
    # Smooth bridge from the six-hour baseline to the one-hour lag and current.
    episodes = np.empty((n, 7, 6))
    for tick in range(6):
        a = tick / 5
        episodes[:, tick] = (
            cur
            - (1 - a) * d6
            - a * d1
            + r.normal(0, [0.15, 0.5, 0.05, 1, 2, 0.1], (n, 6)) * np.sin(np.pi * a)
        )
    episodes[:, -1] = cur
    episodes = np.round(np.clip(episodes, BOUNDS[:, 0], BOUNDS[:, 1]), 1)
    episodes[:, :, 4] = np.maximum(episodes[:, :, 4], episodes[:, :, 3])
    x = episode_features(episodes)
    return episodes, x, proxy_labels(x)


def neural_scores(state, x):
    """Safe NumPy forward pass; no pickled estimators or executable artifacts."""
    v = (np.asarray(x) - state["mean"]) / state["std"]
    for i in range(3):
        v = v @ state[f"w{i}"] + state[f"b{i}"]
        v = np.maximum(v, 0) if i < 2 else expit(v)
    return v


class WeatherCategories:
    """Versioned synthetic model with missing-history and domain abstention."""

    def __init__(self, directory=MODEL):
        import lightgbm as lgb

        self.directory = Path(directory)
        self.profile = json.loads((self.directory / "profile.json").read_text())
        p = self.profile
        if (
            p.get("schema_version") != SCHEMA
            or p.get("features") != FEATURES
            or p.get("categories") != list(CATEGORIES)
            or p.get("field_validated") is not False
        ):
            raise ValueError("Weather category contract mismatch")
        required = {"neural.npz", *[name + ".txt" for name in CATEGORIES]}
        if set(p.get("files", {})) != required:
            raise ValueError("Incomplete category model manifest")
        for name, digest in p["files"].items():
            if sha256(self.directory / name) != digest:
                raise ValueError("Category artifact checksum mismatch")
        self.trees = [
            lgb.Booster(model_file=str(self.directory / (name + ".txt")))
            for name in CATEGORIES
        ]
        if any(m.feature_name() != FEATURES for m in self.trees):
            raise ValueError("Category feature order mismatch")
        with np.load(self.directory / "neural.npz", allow_pickle=False) as a:
            self.state = {k: a[k] for k in a.files}
        shapes = {
            "mean": (13,),
            "std": (13,),
            "w0": (13, 64),
            "b0": (64,),
            "w1": (64, 32),
            "b1": (32,),
            "w2": (32, 10),
            "b2": (10,),
        }
        if (
            set(self.state) != set(shapes)
            or any(
                v.shape != shapes[k] or not np.isfinite(v).all()
                for k, v in self.state.items()
            )
            or (self.state["std"] <= 0).any()
        ):
            raise ValueError("Invalid category neural arrays")
        self.weights = np.asarray(p["tree_weights"])
        self.thresholds = np.asarray(p["thresholds"])
        if (
            self.weights.shape != (10,)
            or self.thresholds.shape != (10,)
            or not np.isfinite([self.weights, self.thresholds]).all()
            or (self.weights < 0).any()
            or (self.weights > 1).any()
            or (self.thresholds <= 0).any()
            or (self.thresholds >= 1).any()
        ):
            raise ValueError("Invalid category selection")
        self.sha256 = sha256(self.directory / "profile.json")

    def scores(self, x):
        x = np.asarray(x, float)
        if x.ndim != 2 or x.shape[1] != len(FEATURES) or not np.isfinite(x).all():
            raise ValueError("Complete category features required")
        tree = np.column_stack([m.predict(x, num_threads=2) for m in self.trees])
        return tree * self.weights + neural_scores(self.state, x) * (1 - self.weights)

    def predict(self, history, cadence):
        """Classify last observed conditions using six hours of complete native history."""
        if type(cadence) is not int or not 1 <= cadence <= 3600 or 3600 % cadence:
            raise ValueError("Native cadence must divide one hour")
        result = {
            "model_id": "himachal_sensor_patterns_v1",
            "profile_sha256": self.sha256,
            "task": "CURRENT_SENSOR_PATTERN_CLASSIFICATION",
            "training_evidence": "SYNTHETIC_ENGINEERING_PROXY_LABELS",
            "score_kind": "SYNTHETIC_PATTERN_SCORE_NOT_EVENT_PROBABILITY",
            "field_validated": False,
            "calibrated": False,
            "probability": None,
            "horizon_hours": 0,
            "categories": [],
            "matched": [],
            "summary": "Insufficient history",
            "status": "UNAVAILABLE",
            "missing_features": [],
            "public_alerts_enabled": False,
        }
        if not history:
            return result
        frame = pd.DataFrame(history).copy()
        frame["timestamp"] = pd.to_datetime(frame.timestamp, utc=True)
        frame = frame.sort_values("timestamp")
        if frame.timestamp.duplicated().any():
            raise ValueError("Duplicate classification timestamps")
        end = frame.timestamp.iloc[-1]
        expected = pd.date_range(
            end - pd.Timedelta(hours=6), end, freq=pd.Timedelta(seconds=cadence)
        )
        native = frame.set_index("timestamp").reindex(expected)
        if native[RAW_SENSOR_COLUMNS].isna().any().any():
            result["missing_features"] = ["six_complete_hours_of_native_measurements"]
            return result
        hourly = native.loc[
            pd.date_range(end - pd.Timedelta(hours=6), end, freq="h"),
            RAW_SENSOR_COLUMNS,
        ].to_numpy(float)
        x = episode_features(hourly[None])
        if ((hourly < BOUNDS[:, 0]) | (hourly > BOUNDS[:, 1])).any() or (
            hourly[:, 3] > hourly[:, 4]
        ).any():
            # Domain checks are numerical; inconsistent particulate ratios do not imply a hazard.
            result["status"] = "OUTSIDE_SYNTHETIC_DOMAIN"
            result["summary"] = "Outside the synthetic training domain"
            return result
        lo = np.asarray(self.profile["feature_min"])
        hi = np.asarray(self.profile["feature_max"])
        if ((x < lo) | (x > hi)).any():
            result["status"] = "OUTSIDE_SYNTHETIC_DOMAIN"
            result["summary"] = "Outside the synthetic training domain"
            return result
        scores = self.scores(x)[0]
        result["categories"] = [
            {
                "id": k,
                "name": name,
                "score": float(s),
                "threshold": float(t),
                "matched": bool(s >= t),
            }
            for (k, name), s, t in zip(CATEGORIES.items(), scores, self.thresholds)
        ]
        result["matched"] = [c["id"] for c in result["categories"] if c["matched"]]
        result["status"] = "SYNTHETIC_PATTERN_SCORES_ONLY"
        result["summary"] = (
            "Multiple sensor patterns matched"
            if len(result["matched"]) > 1
            else next(
                (c["name"] for c in result["categories"] if c["matched"]),
                "No trained extreme pattern matched",
            )
        )
        return result

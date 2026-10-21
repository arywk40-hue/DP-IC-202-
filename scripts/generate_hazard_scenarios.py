"""Generate synthetic hazard scenarios, not observed events or accuracy claims."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from ml.himachal.hazard_scenarios import TARGETS, HazardScenarios, simulate
from ml.himachal.weather_categories import FEATURES, synthetic_episodes
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.data import sha256


def generate(episodes=2048, draws=128, seed=20261021):
    """Keep each parent episode and all its latent worlds in one atomic bundle."""
    if not 32 <= episodes <= 10000:
        raise ValueError("Choose 32..10000 parent episodes")
    history, features, _ = synthetic_episodes(episodes, seed)
    engine = HazardScenarios()
    pieces = {}
    for start in range(0, episodes, 64):
        runs = simulate(
            history[start : start + 64], seed=seed + start + 1, draws=draws, retain=True
        )
        for family, arrays in runs.items():
            for key, array in arrays.items():
                pieces.setdefault(f"{family}_{key}", []).append(array)
    arrays = {k: np.concatenate(v) for k, v in pieces.items()}
    episode_id = np.array(
        [hashlib.sha256(row.astype("<f8").tobytes()).hexdigest() for row in history]
    )
    if len(set(episode_id)) != episodes:
        raise ValueError("Duplicate parent episode")
    local = ROOT / "data/himachal/hazard_scenarios_v1"
    local.mkdir(parents=True, exist_ok=True)
    dataset = local / "scenarios.npz"
    np.savez_compressed(
        dataset, history=history, features=features, episode_id=episode_id, **arrays
    )
    # Fresh parent episodes and independent random worlds test Monte Carlo convergence.
    fresh, _, _ = synthetic_episodes(64, seed + 100000)
    a = simulate(fresh, seed=seed + 200000, draws=4096)
    b = simulate(fresh, seed=seed + 300000, draws=4096)
    differences = np.concatenate(
        [np.abs(a[k]["fraction"] - b[k]["fraction"]).ravel() for k in a]
    )
    families = {
        f: {
            "synthetic_outcome_fraction": {
                k: float(arrays[f + "_outcomes"][:, :, j].mean())
                for j, k in enumerate(TARGETS)
            },
            "mean_conditional_fraction": arrays[f + "_fraction"].mean(0).tolist(),
        }
        for f in engine.config["families"]
    }
    report = {
        "model_id": engine.config["id"],
        "config_sha256": engine.sha256,
        "generator_sha256": sha256(ROOT / "ml/himachal/hazard_scenarios.py"),
        "generator_files": {
            name: sha256(ROOT / name)
            for name in [
                "ml/himachal/hazard_scenarios.py",
                "ml/himachal/weather_categories.py",
                "scripts/generate_hazard_scenarios.py",
            ]
        },
        "numpy_version": np.__version__,
        "parent_sampling": "Oversampled engineered weather regimes; not representative of Mandi climate frequencies.",
        "dataset_sha256": sha256(dataset),
        "dataset_path": str(dataset.relative_to(ROOT)),
        "parent_episodes": episodes,
        "draws_per_parent_per_family": draws,
        "assumption_families": list(families),
        "synthetic_future_worlds": episodes * draws * len(families),
        "horizon_hours": 6,
        "native_simulation_step_minutes": 30,
        "seed": seed,
        "physical_channels": RAW_SENSOR_COLUMNS,
        "past_only_features": FEATURES,
        "targets": list(TARGETS),
        "label_evidence": "SIMULATED_OUTCOMES_NOT_OBSERVED_EVENTS",
        "observed_event_labels": 0,
        "field_validated": False,
        "calibrated_event_probabilities": False,
        "accuracy": None,
        "accuracy_reason": "No independent observed labels; simulation prevalence is not accuracy.",
        "split_policy": "No classifier fitted. For later ML, split parent episode IDs before expanding latent worlds; never split worlds from one history across train/test.",
        "families": families,
        "fresh_seed_convergence": {
            "parent_episodes": 64,
            "draws_each": 4096,
            "seeds": [seed + 200000, seed + 300000],
            "mean_absolute_fraction_difference": float(differences.mean()),
            "maximum_absolute_fraction_difference": float(differences.max()),
            "meaning": "Numerical simulation consistency only, not event forecasting skill.",
        },
        "mean_assumption_range_width": (
            arrays["wetter_fraction"] - arrays["drier_fraction"]
        )
        .mean(0)
        .tolist(),
    }
    out = ROOT / "reports/hazard_scenarios_v1"
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )
    (out / "examples.json").write_text(
        json.dumps(
            [
                {
                    "episode_id": str(episode_id[i]),
                    "six_hour_history": history[i].tolist(),
                    "central_fractions": arrays["central_fraction"][i].tolist(),
                    "drier_fractions": arrays["drier_fraction"][i].tolist(),
                    "wetter_fractions": arrays["wetter_fraction"][i].tolist(),
                    "evidence": "FULLY_SYNTHETIC",
                }
                for i in range(5)
            ],
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                k: report[k]
                for k in [
                    "parent_episodes",
                    "synthetic_future_worlds",
                    "families",
                    "fresh_seed_convergence",
                    "accuracy",
                ]
            },
            indent=2,
        )
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=2048)
    parser.add_argument("--draws", type=int, default=128)
    parser.add_argument("--seed", type=int, default=20261021)
    args = parser.parse_args()
    generate(args.episodes, args.draws, args.seed)

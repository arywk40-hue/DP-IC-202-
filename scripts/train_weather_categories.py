"""Fit/test synthetic sensor-pattern models; never claim real hazard accuracy."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import json

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    hamming_loss,
    roc_auc_score,
)
from sklearn.neural_network import MLPClassifier
from threadpoolctl import threadpool_limits

from ml.himachal.weather_categories import (
    CATEGORIES,
    FEATURES,
    MODEL,
    SCHEMA,
    WeatherCategories,
    neural_scores,
    synthetic_episodes,
)
from ml.six_sensor_forecast.data import sha256


def main():
    if MODEL.exists():
        raise ValueError("Preserve existing model version; choose a new model path")
    data = [
        synthetic_episodes(n, seed)
        for n, seed in [(16000, 101), (4000, 202), (4000, 404)]
    ]
    (_, x, y), (_, vx, vy), (_, tx, ty) = data
    MODEL.mkdir(parents=True)
    files = {}
    trees = []
    with threadpool_limits(limits=2):
        for j, name in enumerate(CATEGORIES):
            m = lgb.LGBMClassifier(
                n_estimators=180,
                num_leaves=15,
                max_depth=5,
                learning_rate=0.06,
                n_jobs=2,
                random_state=42,
                verbosity=-1,
            )
            m.fit(
                pd.DataFrame(x, columns=FEATURES),
                y[:, j],
                eval_set=[(pd.DataFrame(vx, columns=FEATURES), vy[:, j])],
                callbacks=[lgb.early_stopping(20, verbose=False)],
            )
            m.booster_.save_model(str(MODEL / (name + ".txt")))
            files[name + ".txt"] = sha256(MODEL / (name + ".txt"))
            trees.append(m)
        mean = x.mean(0)
        std = x.std(0)
        std = np.where(std > 1e-12, std, 1.0)
        net = MLPClassifier(
            hidden_layer_sizes=(64, 32),
            max_iter=120,
            early_stopping=True,
            n_iter_no_change=12,
            random_state=42,
            batch_size=256,
            alpha=0.005,
        )
        net.fit((x - mean) / std, y)
    state = {
        "mean": mean,
        "std": std,
        **{f"w{i}": a for i, a in enumerate(net.coefs_)},
        **{f"b{i}": a for i, a in enumerate(net.intercepts_)},
    }
    np.savez_compressed(MODEL / "neural.npz", **state)
    files["neural.npz"] = sha256(MODEL / "neural.npz")
    tree_v = np.column_stack(
        [m.predict_proba(pd.DataFrame(vx, columns=FEATURES))[:, 1] for m in trees]
    )
    net_v = neural_scores(state, vx)
    weights = []
    thresholds = []
    for j in range(len(CATEGORIES)):
        _, w, t = max(
            (
                f1_score(
                    vy[:, j],
                    (w * tree_v[:, j] + (1 - w) * net_v[:, j]) >= t,
                    zero_division=0,
                ),
                w,
                t,
            )
            for w in [0, 0.25, 0.5, 0.75, 1]
            for t in [0.35, 0.5, 0.65]
        )
        weights.append(w)
        thresholds.append(t)
    profile = {
        "schema_version": SCHEMA,
        "categories": list(CATEGORIES),
        "features": FEATURES,
        "field_validated": False,
        "training_evidence": "SYNTHETIC_ENGINEERING_PROXY_LABELS",
        "tree_weights": weights,
        "thresholds": thresholds,
        "files": files,
        "feature_min": (
            x.min(0)
            - 0.2 * np.maximum(x.ptp(0) if hasattr(x, "ptp") else np.ptp(x, axis=0), 1)
        ).tolist(),
        "feature_max": (x.max(0) + 0.2 * np.maximum(np.ptp(x, axis=0), 1)).tolist(),
        "split": "INDEPENDENT_SYNTHETIC_SEVEN_HOUR_EPISODES_SEEDS_101_202_404",
        "rows_by_role": {"train": 16000, "validation": 4000, "test": 4000},
        "proxy_definition_source": "ml/himachal/weather_categories.py:proxy_labels",
        "neural_architecture": [13, 64, 32, 10],
        "real_event_labels": 0,
        "calibrated_event_probabilities": False,
    }
    (MODEL / "profile.json").write_text(json.dumps(profile, indent=2) + "\n")
    engine = WeatherCategories()
    pred = engine.scores(tx)
    tree_t = np.column_stack(
        [m.predict_proba(pd.DataFrame(tx, columns=FEATURES))[:, 1] for m in trees]
    )
    net_t = neural_scores(state, tx)

    def metric(p, t):
        return {
            "exact_match": float(accuracy_score(ty, p >= t)),
            "macro_f1": float(f1_score(ty, p >= t, average="macro", zero_division=0)),
            "hamming_loss": float(hamming_loss(ty, p >= t)),
            "classification_report": classification_report(
                ty,
                p >= t,
                target_names=list(CATEGORIES),
                output_dict=True,
                zero_division=0,
            ),
        }

    report = {
        "evidence": "SYNTHETIC_PROXY_RECOVERY_NOT_OBSERVED_WEATHER_ACCURACY",
        "profile_sha256": engine.sha256,
        "rows_by_role": profile["rows_by_role"],
        "split": profile["split"],
        "real_event_labels": 0,
        "models": {
            "lightgbm": metric(tree_t, 0.5),
            "mlp": metric(net_t, 0.5),
            "selected_blend": metric(pred, thresholds),
        },
        "per_category_auc": {
            k: float(roc_auc_score(ty[:, j], pred[:, j]))
            for j, k in enumerate(CATEGORIES)
        },
        "weights_selected_on": "VALIDATION_ONLY",
        "test_reused_for_selection": False,
        "field_validated": False,
        "synthetic_label_prevalence": {
            k: float(y[:, j].mean()) for j, k in enumerate(CATEGORIES)
        },
    }
    out = ROOT / "reports/weather_features_v1"
    out.mkdir(parents=True, exist_ok=True)
    (out / "classification_results.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )
    local = ROOT / "data/himachal/weather_patterns_v1"
    local.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        local / "synthetic_episodes.npz",
        **{
            f"{role}_{key}": a
            for role, entry in zip(["train", "validation", "test"], data)
            for key, a in zip(["episodes", "features", "labels"], entry)
        },
    )
    print(
        json.dumps(
            {
                k: {m: r[m] for m in ["exact_match", "macro_f1", "hamming_loss"]}
                for k, r in report["models"].items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

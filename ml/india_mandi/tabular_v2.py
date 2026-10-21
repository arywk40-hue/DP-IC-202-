"""Versioned Mandi tabular ensemble; expanded-source fitting is offline only."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, eye, hstack, vstack

from ml.india_mandi.hybrid import ROOT, Hybrid, bounded, blend as legacy_blend
from ml.india_mandi.neural import SCHEMA, fit_candidate, forward, load_artifact
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.data import sha256
from ml.six_sensor_forecast.features import build_features, future_targets, split_masks

MODEL_ID = "india_mandi_tabular_v2"
DEFAULT_MODEL = ROOT / "ml/models" / MODEL_ID
FAMILIES = ["legacy_hybrid", "lightgbm", "mlp_v2", "persistence"]


def convex_weights(predictions, truth):
    """Minimize validation MAE on a nonnegative unit simplex, per target."""
    y = np.asarray(truth, float)
    if y.ndim != 2 or y.shape[1] != 6 or len(y) < 2 or not np.isfinite(y).all():
        raise ValueError("Complete validation labels required")
    if set(predictions) != set(FAMILIES) or any(
        p.shape != y.shape or not np.isfinite(p).all() for p in predictions.values()
    ):
        raise ValueError("Matching finite candidate validation predictions required")
    heads = {}
    for j, target in enumerate(RAW_SENSOR_COLUMNS):
        p = np.column_stack([predictions[k][:, j] for k in FAMILIES])
        n, k = p.shape
        constraints = vstack(
            [hstack([csr_matrix(p), -eye(n)]), hstack([-csr_matrix(p), -eye(n)])]
        ).tocsr()
        solution = linprog(
            np.r_[np.zeros(k), np.ones(n) / n],
            A_ub=constraints,
            b_ub=np.r_[y[:, j], -y[:, j]],
            A_eq=csr_matrix(np.r_[np.ones(k), np.zeros(n)][None, :]),
            b_eq=[1.0],
            bounds=(0, None),
            method="highs",
        )
        if not solution.success:
            raise ValueError("Validation simplex solver failed")
        w = np.clip(solution.x[:k], 0, 1)
        w /= w.sum()
        heads[target] = dict(
            weights=dict(zip(FAMILIES, w.tolist())),
            validation_mae=float(np.abs(p @ w - y[:, j]).mean()),
        )
    return dict(
        family_order=FAMILIES,
        selection="CHRONOLOGICAL_VALIDATION_MAE_ONLY",
        heads=heads,
    )


def combine(candidates, weights):
    """Blend numerical endpoints; retain physical ranges."""
    return bounded(
        np.column_stack(
            [
                sum(
                    weights["heads"][c]["weights"][k] * candidates[k][:, j]
                    for k in FAMILIES
                )
                for j, c in enumerate(RAW_SENSOR_COLUMNS)
            ]
        )
    )


def dataset(config):
    """Load immutable expanded source and purge six-hour target boundaries."""
    root = ROOT / config["data"]
    manifest = json.loads((root / "dataset_manifest.json").read_text())
    if (
        manifest.get("country_code") != "IN"
        or manifest.get("evidence_kind") != "MODELED_GRID_RETROSPECTIVE"
        or sha256(root / "observations.csv") != manifest["observations_sha256"]
    ):
        raise ValueError("Matching India modeled source required")
    frame, features = build_features(pd.read_csv(root / "observations.csv"))
    truth = future_targets(frame, 6)
    masks = split_masks(
        frame,
        6,
        config["validation_start"],
        config["test_start"],
        [],
        temporal_only=True,
    )
    good = np.isfinite(features.to_numpy()).all(axis=1) & np.isfinite(
        truth.to_numpy()
    ).all(axis=1)
    return frame, features, truth, {k: v & good for k, v in masks.items()}, manifest


class TabularV2:
    """Hash-checked gateway model; no training or checkpoint loading in requests."""

    def __init__(self, directory=DEFAULT_MODEL):
        import lightgbm as lgb

        self.directory = Path(directory).resolve()
        self.profile = json.loads((self.directory / "profile.json").read_text())
        p = self.profile
        if (
            p.get("schema_version") != "indra_mandi_tabular_profile_v2"
            or p.get("id") != MODEL_ID
            or p.get("sensors") != RAW_SENSOR_COLUMNS
            or p.get("horizon_hours") != 6
            or p.get("history_hours") != 24
            or p.get("field_validated") is not False
            or p.get("country") != "IN"
        ):
            raise ValueError("Incompatible tabular v2 profile")
        for relative, checksum in p["files"].items():
            path = (self.directory / relative).resolve()
            if not path.is_relative_to(self.directory) or sha256(path) != checksum:
                raise ValueError("Tabular v2 artifact checksum/path mismatch")
        required = {
            "ensemble_weights.json",
            "neural/model.json",
            "neural/weights.npz",
            "online_scaler.npz",
            *[f"lightgbm/{c}.txt" for c in RAW_SENSOR_COLUMNS],
        }
        if not required <= set(p["files"]):
            raise ValueError("Tabular v2 artifact missing from checksum manifest")
        self.weights = json.loads(
            (self.directory / "ensemble_weights.json").read_text()
        )
        if self.weights["family_order"] != FAMILIES or set(
            self.weights["heads"]
        ) != set(RAW_SENSOR_COLUMNS):
            raise ValueError("Tabular v2 blend order mismatch")
        for head in self.weights["heads"].values():
            if set(head["weights"]) != set(FAMILIES):
                raise ValueError("Incomplete blend head")
            w = np.array([head["weights"][k] for k in FAMILIES])
            if not np.isfinite(w).all() or (w < 0).any() or not np.isclose(w.sum(), 1):
                raise ValueError("Invalid convex weights")
        self.legacy = Hybrid()
        if self.legacy.profile_sha256 != p["legacy_profile_sha256"]:
            raise ValueError("Legacy component profile changed")
        self.neural, meta = load_artifact(self.directory / "neural")
        if (
            meta["features"] != p["features"]
            or meta["source_sha256"] != p["source_sha256"]
        ):
            raise ValueError("Neural source/features mismatch")
        self.boosters = {
            c: lgb.Booster(model_file=str(self.directory / f"lightgbm/{c}.txt"))
            for c in RAW_SENSOR_COLUMNS
        }
        if any(b.feature_name() != p["features"] for b in self.boosters.values()):
            raise ValueError("LightGBM feature order mismatch")
        self.profile_sha256 = sha256(self.directory / "profile.json")

    def candidates(self, features, current):
        if (
            features.columns.tolist() != self.profile["features"]
            or current.columns.tolist() != RAW_SENSOR_COLUMNS
        ):
            raise ValueError("Tabular v2 feature order mismatch")
        x, now = features.to_numpy(float), current.to_numpy(float)
        if not np.isfinite(x).all() or not np.isfinite(now).all():
            raise ValueError("Complete inputs required")
        boosted = bounded(
            now
            + np.column_stack(
                [
                    self.boosters[c].predict(features, num_threads=2)
                    for c in RAW_SENSOR_COLUMNS
                ]
            )
        )
        return dict(
            legacy_hybrid=legacy_blend(
                self.legacy.components.predict(features, current), self.legacy.weights
            ),
            lightgbm=boosted,
            mlp_v2=forward(self.neural, x, now),
            persistence=now,
        )

    def predict(self, observations):
        frame, features = build_features(observations)
        now = frame[RAW_SENSOR_COLUMNS]
        valid = np.isfinite(now.to_numpy()).all(axis=1)
        complete = valid & np.isfinite(features.to_numpy()).all(axis=1)
        output = np.full((len(frame), 6), np.nan)
        output[valid] = now.loc[valid].to_numpy()
        if complete.any():
            output[complete] = combine(
                self.candidates(features.loc[complete], now.loc[complete]), self.weights
            )
        result = frame[["location_id", "timestamp_utc"]].copy()
        result["forecast_timestamp_utc"] = frame.timestamp_utc + pd.Timedelta(hours=6)
        result["status"] = np.where(
            complete,
            "HYBRID_READY",
            np.where(valid, "WARMING_UP_PERSISTENCE", "MISSING_CURRENT_SENSOR"),
        )
        result["model_id"] = np.where(
            complete,
            MODEL_ID,
            np.where(valid, "persistence_six_sensor_v1", "unavailable"),
        )
        for j, c in enumerate(RAW_SENSOR_COLUMNS):
            result["forecast_" + c] = output[:, j]
        return result


def train(config_path):
    """Fit expanded-data LightGBM/MLP; freeze validation blends before test scoring."""
    import lightgbm as lgb
    from threadpoolctl import threadpool_limits
    from ml.india_mandi.benchmark import metric

    cfg = json.loads(Path(config_path).read_text())
    if (
        cfg.get("schema_version") != "indra_mandi_pipeline_v2"
        or cfg.get("field_validated") is not False
    ):
        raise ValueError("Versioned modeled-data configuration required")
    output, reports = (
        (ROOT / cfg["models"]).resolve(),
        (ROOT / cfg["reports"]).resolve(),
    )
    if not output.is_relative_to(ROOT / "ml/models") or not reports.is_relative_to(
        ROOT / "reports"
    ):
        raise ValueError(
            "Versioned model/report outputs must remain inside the repository"
        )
    if output.exists():
        raise ValueError("Version exists; do not overwrite trained artifacts")
    frame, features, labels, masks, manifest = dataset(cfg)
    if any(m.sum() < 100 for m in masks.values()):
        raise ValueError("Insufficient chronological cohorts")
    x, now, y = (
        features.to_numpy(float),
        frame[RAW_SENSOR_COLUMNS].to_numpy(float),
        labels.to_numpy(float),
    )
    residual = y - now
    output.mkdir(parents=True)
    (output / "lightgbm").mkdir()
    (output / "neural").mkdir()
    choices = {}
    for j, c in enumerate(RAW_SENSOR_COLUMNS):
        trials = []
        for leaves in cfg["lightgbm_leaves"]:
            learner = lgb.LGBMRegressor(
                objective="regression_l1",
                num_leaves=leaves,
                max_depth=-1,
                n_estimators=cfg["lightgbm_rounds"],
                learning_rate=cfg["lightgbm_learning_rate"],
                min_child_samples=40,
                reg_lambda=2.0,
                random_state=cfg["seed"],
                n_jobs=cfg["threads"],
                verbosity=-1,
            )
            learner.fit(
                features.loc[masks["train"]],
                residual[masks["train"], j],
                eval_set=[
                    (
                        features.loc[masks["validation"]],
                        residual[masks["validation"], j],
                    )
                ],
                eval_metric="l1",
                callbacks=[lgb.early_stopping(40, verbose=False)],
            )
            predicted = now[masks["validation"], j] + learner.predict(
                features.loc[masks["validation"]]
            )
            trials.append(
                (
                    float(np.abs(predicted - y[masks["validation"], j]).mean()),
                    leaves,
                    learner,
                )
            )
        loss, leaves, winner = min(trials, key=lambda item: item[0])
        winner.booster_.save_model(str(output / f"lightgbm/{c}.txt"))
        choices[c] = dict(
            leaves=leaves, best_iteration=winner.best_iteration_, validation_mae=loss
        )
        print("LightGBM", c, choices[c], flush=True)
    neural_cfg = dict(
        alpha=0.01,
        batch_size=256,
        learning_rate=0.001,
        seed=cfg["seed"],
        max_epochs=cfg["mlp_epochs"],
        patience=cfg["mlp_patience"],
        minimum_improvement=1e-5,
        residual_blend_candidates=[0, 0.25, 0.5, 0.75, 1],
    )
    with threadpool_limits(limits=cfg["threads"]):
        state, architecture = fit_candidate(
            x,
            residual,
            now,
            y,
            masks["train"],
            masks["validation"],
            neural_cfg,
            cfg["mlp_hidden"],
        )
    np.savez_compressed(output / "neural/weights.npz", **state)
    meta = dict(
        schema_version=SCHEMA,
        artifact="weights.npz",
        artifact_sha256=sha256(output / "neural/weights.npz"),
        features=features.columns.tolist(),
        targets=RAW_SENSOR_COLUMNS,
        architecture=architecture,
        source_sha256=manifest["observations_sha256"],
        country="IN",
        horizon_hours=6,
        normalization="TRAINING_ONLY_FEATURE_AND_RESIDUAL_SCALING",
        config_sha256=sha256(Path(config_path)),
    )
    (output / "neural/model.json").write_text(json.dumps(meta, indent=2) + "\n")
    # Fixed train-only scaler for the separate incremental residual learner.
    np.savez_compressed(
        output / "online_scaler.npz",
        mean=state["x_mean"],
        std=state["x_std"],
        residual_scale=state["y_std"],
    )
    legacy = Hybrid()

    # Candidate construction here mirrors the checked runtime, without loading an unfinished profile.
    def predict(mask):
        xx, current = features.loc[mask], frame.loc[mask, RAW_SENSOR_COLUMNS]
        return dict(
            legacy_hybrid=legacy_blend(
                legacy.components.predict(xx, current), legacy.weights
            ),
            lightgbm=bounded(
                current.to_numpy()
                + np.column_stack(
                    [
                        lgb.Booster(
                            model_file=str(output / f"lightgbm/{c}.txt")
                        ).predict(xx, num_threads=cfg["threads"])
                        for c in RAW_SENSOR_COLUMNS
                    ]
                )
            ),
            mlp_v2=forward(state, xx.to_numpy(float), current.to_numpy()),
            persistence=current.to_numpy(),
        )

    val = predict(masks["validation"])
    weights = convex_weights(val, y[masks["validation"]])
    (output / "ensemble_weights.json").write_text(json.dumps(weights, indent=2) + "\n")
    files = [
        "ensemble_weights.json",
        "neural/model.json",
        "neural/weights.npz",
        "online_scaler.npz",
        *[f"lightgbm/{c}.txt" for c in RAW_SENSOR_COLUMNS],
    ]
    profile = dict(
        schema_version="indra_mandi_tabular_profile_v2",
        id=MODEL_ID,
        display_name="Mandi tabular ensemble v2",
        family="LightGBM + residual neural + retained hybrid + persistence",
        sensors=RAW_SENSOR_COLUMNS,
        features=features.columns.tolist(),
        horizon_hours=6,
        history_hours=24,
        field_validated=False,
        country="IN",
        source_sha256=manifest["observations_sha256"],
        legacy_profile_sha256=legacy.profile_sha256,
        files={f: sha256(output / f) for f in files},
        config_sha256=sha256(Path(config_path)),
    )
    (output / "profile.json").write_text(json.dumps(profile, indent=2) + "\n")
    runtime = TabularV2(output)
    results = {}
    for role, mask in {
        **masks,
        "new_date_extension": masks["future_test"]
        & (frame.timestamp_utc >= pd.Timestamp(cfg["extension_start"])).to_numpy(),
    }.items():
        candidates = (
            val
            if role == "validation"
            else runtime.candidates(
                features.loc[mask], frame.loc[mask, RAW_SENSOR_COLUMNS]
            )
        )
        candidates["selected_v2"] = combine(candidates, weights)
        results[role] = {
            name: {
                c: metric(y[mask, j], v[:, j], now[mask, j])
                for j, c in enumerate(RAW_SENSOR_COLUMNS)
            }
            for name, v in candidates.items()
        }
    reports.mkdir(parents=True, exist_ok=True)
    result = dict(
        profile_id=MODEL_ID,
        data_rows=len(frame),
        rows_by_role={k: int(v.sum()) for k, v in masks.items()},
        source_start=manifest["coverage_start_utc"],
        source_end=manifest["coverage_end_utc"],
        source_sha256=manifest["observations_sha256"],
        lightgbm_choices=choices,
        neural_architecture=architecture,
        blend=weights,
        metrics=results,
        field_validated=False,
        test_status="REUSED_TEST_PLUS_NEW_DATE_EXTENSION_NO_RETUNING",
        tabpfn="SEPARATE_BOUNDED_LOCAL_COMPARISON",
        online_learning="SEPARATE_DELAYED_LABEL_SHADOW_SGD",
        source_kind="RETROSPECTIVE_MANDI_MODELED_GRID",
        profile_sha256=runtime.profile_sha256,
    )
    (reports / "results.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n"
    )
    return result


def evaluate(config_path):
    """Retest frozen v2 components without fitting or selecting any weights."""
    from datetime import datetime, timezone
    from ml.india_mandi.benchmark import metric

    cfg = json.loads(Path(config_path).read_text())
    engine = TabularV2(ROOT / cfg["models"])
    frame, features, truth, masks, manifest = dataset(cfg)
    if (
        manifest["observations_sha256"] != engine.profile["source_sha256"]
        or sha256(Path(config_path)) != engine.profile["config_sha256"]
    ):
        raise ValueError("Evaluation must use the frozen v2 source and configuration")
    partitions = {
        **masks,
        "new_date_extension": masks["future_test"]
        & (frame.timestamp_utc >= pd.Timestamp(cfg["extension_start"])).to_numpy(),
    }
    results = {}
    for role in ("validation", "future_test", "new_date_extension"):
        mask = partitions[role]
        current = frame.loc[mask, RAW_SENSOR_COLUMNS]
        candidates = engine.candidates(features.loc[mask], current)
        candidates["selected_v2"] = combine(candidates, engine.weights)
        results[role] = {
            name: {
                c: metric(
                    truth.loc[mask, c].to_numpy(), values[:, j], current[c].to_numpy()
                )
                for j, c in enumerate(RAW_SENSOR_COLUMNS)
            }
            for name, values in candidates.items()
        }
    receipt = dict(
        profile_id=engine.profile["id"],
        profile_sha256=engine.profile_sha256,
        executed_at_utc=datetime.now(timezone.utc).isoformat(),
        trained_or_retuned=False,
        source_sha256=manifest["observations_sha256"],
        field_validated=False,
        metrics=results,
    )
    path = ROOT / cfg["reports"] / "evaluation_latest.json"
    path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    return receipt

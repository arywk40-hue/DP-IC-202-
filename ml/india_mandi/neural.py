"""Offline six-channel residual neural benchmarks, preserving saved XGB heads.

Native history is represented by the same 66 causal features as the existing
teacher. Epoch-wise partial_fit is an offline optimizer, not a live-learning
service. No event labels, synthetic weather or additional sensors are used.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import platform
import time

import numpy as np
import pandas as pd
import sklearn
from sklearn.neural_network import MLPRegressor
from threadpoolctl import threadpool_limits

from ml.india_mandi.benchmark import arrays, evaluate, metric
from ml.india_mandi.data import ROOT, load_config
from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.data import sha256
from ml.six_sensor_forecast.features import build_features

SCHEMA = "indra_mandi_residual_mlp_v1"


def scale_fit(x, residual):
    """Call with training rows only; no validation/test preprocessing fit."""
    if x.ndim != 2 or residual.ndim != 2 or residual.shape != (len(x), 6) or len(x) < 2:
        raise ValueError("Nonempty matching six-target training arrays required")
    if not np.isfinite(x).all() or not np.isfinite(residual).all():
        raise ValueError("Complete causal history and observed future targets required")
    scales = {}
    for prefix, values in (("x", x), ("y", residual)):
        scales[prefix+"_mean"] = values.mean(axis=0)
        std = values.std(axis=0)
        scales[prefix+"_std"] = np.where(std > 1e-12, std, 1.)
    return scales


def bounded(values):
    low, high = np.array([PHYSICAL_RANGES[c] for c in RAW_SENSOR_COLUMNS]).T
    return np.clip(values, low, high)


def fit_candidate(x, residual, current, truth, train_mask, val_mask, cfg, hidden):
    """Explicit chronological validation; sklearn random early stopping is off."""
    train_x, train_y = x[train_mask], residual[train_mask]
    if not np.any(val_mask) or np.any(train_mask & val_mask):
        raise ValueError("Distinct nonempty train/validation partitions required")
    scales = scale_fit(train_x, train_y)
    normalized = (train_x-scales["x_mean"])/scales["x_std"]
    y = (train_y-scales["y_mean"])/scales["y_std"]
    val_x = (x[val_mask]-scales["x_mean"])/scales["x_std"]
    learner = MLPRegressor(hidden_layer_sizes=tuple(hidden), activation="relu", solver="adam",
        alpha=cfg["alpha"], batch_size=cfg["batch_size"], learning_rate_init=cfg["learning_rate"],
        random_state=cfg["seed"], early_stopping=False, shuffle=True)
    best, best_loss, stall = None, float("inf"), 0
    trace = []
    for epoch in range(1, cfg["max_epochs"]+1):
        # All batches are drawn solely from the training partition.
        learner.partial_fit(normalized, y)
        predicted = bounded(current[val_mask]+learner.predict(val_x)*scales["y_std"]+scales["y_mean"])
        loss = float(np.mean(np.abs(predicted-truth[val_mask])/scales["y_std"]))
        if not np.isfinite(loss):
            raise ValueError("Nonfinite validation objective")
        trace.append(dict(epoch=epoch, normalized_validation_mae=loss))
        if loss < best_loss-cfg["minimum_improvement"]:
            best_loss, stall = loss, 0
            best = dict(epoch=epoch, coefs=copy.deepcopy(learner.coefs_), biases=copy.deepcopy(learner.intercepts_))
        else:
            stall += 1
        if stall >= cfg["patience"]:
            break
    state = {**scales, "weights": np.ones(6)}
    for i, (w, b) in enumerate(zip(best["coefs"], best["biases"])):
        state[f"w{i}"], state[f"b{i}"] = w, b
    # Use the unbounded learned residual, not the already clipped endpoint.
    raw = residual_forward(state, x[val_mask])
    weights = []
    for j in range(6):
        weights.append(min(cfg["residual_blend_candidates"], key=lambda weight:
            np.mean(np.abs(truth[val_mask, j]-np.clip(current[val_mask,j]+raw[:,j]*weight, *PHYSICAL_RANGES[RAW_SENSOR_COLUMNS[j]])))))
    state["weights"] = np.asarray(weights, dtype=float)
    return state, dict(hidden_layers=hidden, selected_epoch=best["epoch"], epochs_run=len(trace),
        normalized_validation_mae=best_loss, validation_trace=trace,
        residual_weights=state["weights"].tolist(), parameter_count=sum(a.size for key,a in state.items() if key.startswith(("w", "b")) and key != "weights"))


def residual_forward(state, x):
    values = (np.asarray(x, dtype=float)-state["x_mean"])/state["x_std"]
    layers = len([k for k in state if k.startswith("b")])
    for i in range(layers):
        values = values @ state[f"w{i}"] + state[f"b{i}"]
        if i < layers-1:
            values = np.maximum(values, 0)
    return values*state["y_std"]+state["y_mean"]


def forward(state, x, current, *, apply_weights=True):
    return bounded(current+residual_forward(state, x)*(state["weights"] if apply_weights else 1))


def load_artifact(directory):
    directory = Path(directory)
    report = json.loads((directory/"model.json").read_text())
    path = (directory/report["artifact"]).resolve()
    if (report.get("schema_version") != SCHEMA or not path.is_relative_to(directory.resolve())
            or report["targets"] != RAW_SENSOR_COLUMNS or sha256(path) != report["artifact_sha256"]):
        raise ValueError("Neural artifact contract/hash mismatch")
    if len(report["features"]) != 66 or len(set(report["features"])) != 66:
        raise ValueError("Expected 66 ordered causal six-channel features")
    dims = [66, *report["architecture"]["hidden_layers"], 6]
    if len(dims) > 5 or any(type(d) is not int or not 1 <= d <= 256 for d in dims):
        raise ValueError("Neural architecture resource bounds exceeded")
    with np.load(path, allow_pickle=False) as data:
        state = {k: data[k] for k in data.files}
    expected = dict(x_mean=(66,), x_std=(66,), y_mean=(6,), y_std=(6,), weights=(6,))
    for i, (a,b) in enumerate(zip(dims,dims[1:])):
        expected[f"w{i}"], expected[f"b{i}"] = (a,b), (b,)
    if set(state) != set(expected) or any(state[k].shape != shape or not np.isfinite(state[k]).all() for k,shape in expected.items()):
        raise ValueError("Neural array shape/finite contract mismatch")
    if (state["x_std"] <= 0).any() or (state["y_std"] <= 0).any() or not ((state["weights"] >= 0) & (state["weights"] <= 1)).all():
        raise ValueError("Invalid scaling/blend state")
    return state, report


def predict(directory, features, current):
    state, report = load_artifact(directory)
    if features.columns.tolist() != report["features"] or current.columns.tolist() != RAW_SENSOR_COLUMNS or len(features) != len(current):
        raise ValueError("Neural inference column order/rows mismatch")
    x, now = features.to_numpy(float), current.to_numpy(float)
    valid = np.isfinite(x).all(axis=1) & np.isfinite(now).all(axis=1)
    out = np.full((len(x),6), np.nan)
    out[valid] = forward(state, x[valid], now[valid])
    return out


def predict_observations(observations, directory):
    """Six-channel hourly CSV interface with explicit missing-history status."""
    frame, features = build_features(observations)
    values = predict(directory, features, frame[RAW_SENSOR_COLUMNS])
    result = frame[["location_id", "timestamp_utc"]].copy()
    result["forecast_timestamp_utc"] = frame.timestamp_utc+pd.Timedelta(hours=6)
    complete = np.isfinite(values).all(axis=1)
    current_ok = np.isfinite(frame[RAW_SENSOR_COLUMNS].to_numpy()).all(axis=1)
    result["status"] = np.where(complete, "OFFLINE_RESEARCH_ONLY", np.where(current_ok, "INCOMPLETE_HISTORY", "MISSING_CURRENT_SENSOR"))
    for j,target in enumerate(RAW_SENSOR_COLUMNS):
        result["forecast_"+target] = values[:,j]
    return result


def run(path, *, train=False):
    cfg_path = Path(path)
    cfg = json.loads(cfg_path.read_text())
    if cfg.get("schema_version") != "indra_mandi_neural_benchmark_v1" or cfg.get("deployment_approved") is not False or cfg.get("online_learning_enabled") is not False:
        raise ValueError("Offline research configuration required")
    if not 1 <= cfg["max_epochs"] <= 200 or not 1 <= cfg["patience"] <= cfg["max_epochs"] or not 1 <= cfg["threads"] <= 8:
        raise ValueError("Bounded training configuration required")
    if (cfg["architectures"] != [[32], [64,32]] or cfg["residual_blend_candidates"] != [0,.25,.5,.75,1]
            or not 1 <= cfg["batch_size"] <= 4096 or not np.isfinite(cfg["learning_rate"]) or not 0 < cfg["learning_rate"] <= .1
            or not np.isfinite(cfg["alpha"]) or cfg["alpha"] < 0):
        raise ValueError("Versioned architecture/scaling/blend configuration required")
    base = load_config(ROOT/cfg["base_config"])
    frame, features, truth, masks, manifest = arrays(base)
    x = features.to_numpy(float)
    current, y = frame[RAW_SENSOR_COLUMNS].to_numpy(float), truth.to_numpy(float)
    residual = y-current
    output, reports = (ROOT/cfg["models_output"]).resolve(), (ROOT/cfg["reports_output"]).resolve()
    if not output.is_relative_to(ROOT/"ml/models") or not reports.is_relative_to(ROOT/"reports") or output == Path(base["models"]):
        raise ValueError("Separate repository research model/report output required")
    if train and output.exists():
        raise ValueError("Versioned output already exists; evaluate it or choose a new experiment ID")
    baseline = evaluate(base)
    results = copy.deepcopy(baseline["results"])
    # The same complete-history rows and exact +6h targets are used throughout.
    partitions = {**masks, "fresh_future_test": masks["future_test"] & (frame.timestamp_utc >= pd.Timestamp(base["fresh_test_start"])).to_numpy()}
    candidates = {}
    if train:
        output.mkdir(parents=True)
    with threadpool_limits(limits=cfg["threads"]):
        for hidden in cfg["architectures"]:
            if not 1 <= len(hidden) <= 3 or any(type(v) is not int or not 1 <= v <= 256 for v in hidden):
                raise ValueError("Bounded hidden layers required")
            name = "residual_mlp_"+"_".join(map(str,hidden))
            directory = output/name
            if train:
                started = time.perf_counter()
                state, architecture = fit_candidate(x, residual, current, y, masks["train"], masks["validation"], cfg, hidden)
                directory.mkdir()
                artifact = directory/"weights.npz"
                np.savez_compressed(artifact, **state)
                metadata = dict(schema_version=SCHEMA, artifact=artifact.name, artifact_sha256=sha256(artifact),
                    features=features.columns.tolist(), targets=RAW_SENSOR_COLUMNS, architecture=architecture,
                    horizon_hours=6, source_sha256=manifest["observations_sha256"], config_sha256=sha256(cfg_path),
                    base_config_sha256=base["_config_sha256"], fit_seconds=time.perf_counter()-started,
                    country="IN", evidence="MODELED_GRID_RETROSPECTIVE", deployment_approved=False,
                    normalization="TRAIN_ONLY_FEATURE_AND_TARGET_RESIDUAL_MEAN_STD",
                    architecture_family="Shared multi-output residual feed-forward neural network with causal history features",
                    prediction="physical_clip(current + validation_weight * inverse_scaled_network_residual)",
                    feature_history_hours=24, online_learning_enabled=False,
                    selection="Chronological validation for epoch and per-target blend; no random validation split",
                    source_dates={k:baseline["source_period"][k] for k in ("start","end")},
                    software=dict(python=platform.python_version(), numpy=np.__version__, sklearn=sklearn.__version__))
                (directory/"model.json").write_text(json.dumps(metadata,indent=2,allow_nan=False)+"\n")
            started = time.perf_counter()
            predicted = predict(directory, features, frame[RAW_SENSOR_COLUMNS])
            _, metadata = load_artifact(directory)
            if metadata["config_sha256"] != sha256(cfg_path) or metadata["source_sha256"] != manifest["observations_sha256"]:
                raise ValueError("Frozen experiment/source mismatch")
            for j, target in enumerate(RAW_SENSOR_COLUMNS):
                for role, mask in partitions.items():
                    results[target][role][name] = metric(y[mask,j], predicted[mask,j], current[mask,j])
            candidates[name] = dict(architecture=metadata["architecture"], artifact_sha256=metadata["artifact_sha256"],
                artifact_bytes=(directory/metadata["artifact"]).stat().st_size,
                offline_fit_seconds=metadata["fit_seconds"], host_batch_inference_and_scoring_seconds=time.perf_counter()-started,
                inference_rows=len(features), host_latency_is_not_esp32_latency=True)
            print(f"{name}: epochs={metadata['architecture']['epochs_run']}, parameters={metadata['architecture']['parameter_count']}",flush=True)
    selected = {t:min(results[t]["validation"], key=lambda n:results[t]["validation"][n]["mae"]) for t in RAW_SENSOR_COLUMNS}
    receipt = dict(schema_version="indra_mandi_architecture_comparison_v1", results=results, candidates=candidates,
        validation_selected_heads=selected, source_sha256=manifest["observations_sha256"],
        source_period=baseline["source_period"], rows_by_role={k:int(v.sum()) for k,v in partitions.items()},
        original_test_exposure_note=base["test_exposure_note"],
        test_status="REUSED_RETROSPECTIVE_BENCHMARK_NOT_NEW_UNSEEN_FIELD_TEST",
        evidence="MODELED_GRID_RETROSPECTIVE", field_accuracy="NOT_ESTABLISHED", china_data_or_weights_used=False,
        online_learning_enabled=False, hazard_accuracy="NOT_EVALUATED_NO_INDEPENDENT_LABELS", deployment_approved=False)
    reports.mkdir(parents=True,exist_ok=True)
    (reports/"results.json").write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n")
    lines=["# Mandi numerical forecast architecture comparison", "", "Retrospective modeled-grid benchmark; not observed station accuracy or hazard validation.",
        "All models use the same complete-history rows, chronological splits and exact +6h targets. All new preprocessing fits training rows only.",
        "Neural heads share two alternatives: 66 → 32 → 6 and 66 → 64 → 32 → 6, ReLU hidden layers, residual outputs, train-only scaling and validation-selected persistence blends.",
        "The 66 features come from six channels and up to 24 hours of causal history. No coordinates, time-of-day or new physical channels are learned inputs.", "",
        "MAE in each channel's physical units; lower is better. Choices are made on validation, not on this test table.", "",
        "| Target | Persistence | XGB student | XGB history teacher | Ridge | MLP 32 | MLP 64/32 | Validation choice | Choice test MAE |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |"]
    for target in RAW_SENSOR_COLUMNS:
        row=results[target]["future_test"]
        names=["persistence","student","teacher","temporal_ridge","residual_mlp_32","residual_mlp_64_32"]
        lines.append("| "+target+" | "+" | ".join(f"{row[n]['mae']:.4f}" for n in names)+f" | {selected[target]} | {row[selected[target]]['mae']:.4f} |")
    lines += ["", "Rows by split: `"+json.dumps(receipt["rows_by_role"])+"`.", "",
        "The September/October evaluation period has been examined in earlier project work. Reusing it is an architecture diagnostic, not a newly untouched accuracy test. A future monitored holdout is still required.",
        "Current dashboard/ESP32 weights are preserved. Neural candidates are isolated research artifacts, with no promotion, on-device export or live-learning worker.",
        "Epoch-wise partial_fit here is offline training; it does not mean the deployed system learns from incoming readings.",
        "Rain/snowstorm/cloudburst event labels, calibrated probabilities and physical board/radio validation are still missing.",
        "Source attribution: Open-Meteo, ECMWF IFS and CAMS global. PM and weather are different modeled grids; pressure is grid surface pressure.", ""]
    (reports/"REPORT.md").write_text("\n".join(lines))
    return receipt

"""Weather-conditioned synthetic PM, with explicit flags and no event labels.

This backcasts simulated pollution into missing historical API positions. It
cannot recover actual old PM, emission changes, disasters or forecast accuracy.
Only the pre-validation training reference is used to fit the generator.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

WEATHER = ["temperature_c", "relative_humidity_pct", "pressure_hpa", "wind_speed_mps"]


def conditions(frame):
    """Four available weather channels plus calendar phase; no PM as input."""
    t = pd.DatetimeIndex(pd.to_datetime(frame.timestamp_utc, utc=True)).tz_convert(
        "Asia/Kolkata"
    )
    x = frame[WEATHER].astype(float).copy()
    hour = t.hour + t.minute / 60
    for name, phase in [("hour", hour / 24), ("season", t.dayofyear / 365.2425)]:
        x[name + "_sin"] = np.sin(2 * np.pi * phase)
        x[name + "_cos"] = np.cos(2 * np.pi * phase)
    if not np.isfinite(x.to_numpy()).all():
        raise ValueError(
            "Synthetic PM requires complete real/modelled weather, not fabricated weather"
        )
    return x


def draw_joint(log_mean, innovations, phi, seed):
    """Paired log-space innovations and AR memory preserve variability/dependence."""
    mean = np.asarray(log_mean, float)
    innovations = np.asarray(innovations, float)
    phi = np.asarray(phi, float)
    if (
        mean.ndim != 2
        or mean.shape[1] != 2
        or innovations.ndim != 2
        or innovations.shape[1] != 2
        or len(innovations) < 2
        or phi.shape != (2,)
    ):
        raise ValueError("Two-channel joint PM simulation arrays required")
    if (
        not all(np.isfinite(v).all() for v in (mean, innovations, phi))
        or (np.abs(phi) >= 1).any()
    ):
        raise ValueError("Finite stable simulation required")
    rng = np.random.default_rng(seed)
    state = np.zeros(2)
    out = []
    for mu in mean:
        state = phi * state + innovations[rng.integers(len(innovations))]
        fine, coarse = np.expm1(np.clip(mu + state, 0, np.log1p(5000)))
        out.append((fine, min(5000, fine + coarse)))
    return np.asarray(out)


def fit_and_generate(reference, source, fit_before, seed=42, rounds=150):
    """Fit training-only conditional log-PM models; preserve every available PM."""
    import lightgbm as lgb

    ref = reference.copy()
    ref["timestamp_utc"] = pd.to_datetime(ref.timestamp_utc, utc=True)
    cutoff = pd.Timestamp(fit_before)
    if cutoff.tzinfo is None:
        raise ValueError("Timezone-aware training cutoff required")
    source = source.copy()
    source["timestamp_utc"] = pd.to_datetime(source.timestamp_utc, utc=True)
    source = source.sort_values("timestamp_utc").reset_index(drop=True)
    if source.empty or source.timestamp_utc.max() >= cutoff:
        raise ValueError(
            "Generate missing training-era data only; do not fabricate validation/test labels"
        )
    for frame in (source, ref):
        if frame.timestamp_utc.isna().any() or frame.timestamp_utc.duplicated().any():
            raise ValueError("Unique finite timestamps required")
        if "location_id" in frame and frame.location_id.nunique() != 1:
            raise ValueError("One location per generator required")
    if not source.timestamp_utc.diff().iloc[1:].eq(pd.Timedelta(hours=1)).all():
        raise ValueError("Consecutive hourly source required for temporal simulation")
    for name in ("pm25_ug_m3", "pm10_ug_m3"):
        if not source[name].dropna().between(0, 5000).all():
            raise ValueError("Existing PM must be finite and physically bounded")
    ref = ref.loc[ref.timestamp_utc < cutoff].sort_values("timestamp_utc")
    if (
        ref.empty
        or len(ref) < 100
        or not np.isfinite(ref[["pm25_ug_m3", "pm10_ug_m3"]].to_numpy()).all()
    ):
        raise ValueError("Complete particulate training reference required")
    x = conditions(ref)
    y = np.log1p(
        np.column_stack(
            [
                np.maximum(ref.pm25_ug_m3.to_numpy(), 0),
                np.maximum(ref.pm10_ug_m3.to_numpy() - ref.pm25_ug_m3.to_numpy(), 0),
            ]
        )
    )
    models = []
    fitted = []
    for j in range(2):
        model = lgb.LGBMRegressor(
            n_estimators=rounds,
            num_leaves=15,
            min_child_samples=40,
            learning_rate=0.04,
            reg_lambda=2.0,
            random_state=seed,
            n_jobs=2,
            verbosity=-1,
        )
        model.fit(x, y[:, j])
        models.append(model)
        fitted.append(model.predict(x))
    residual = y - np.column_stack(fitted)
    adjacent = ref.timestamp_utc.diff().eq(pd.Timedelta(hours=1)).to_numpy()[1:]
    previous, next_ = residual[:-1][adjacent], residual[1:][adjacent]
    if len(previous) < 2:
        raise ValueError("Consecutive training history required for temporal variation")
    phi = np.clip(
        np.sum(previous * next_, axis=0)
        / np.maximum(np.sum(previous**2, axis=0), 1e-12),
        0,
        0.97,
    )
    innovations = next_ - previous * phi
    xx = conditions(source)
    mean = np.column_stack([model.predict(xx) for model in models])
    simulated = draw_joint(mean, innovations, phi, seed)
    a = source.pm25_ug_m3.isna()
    b = source.pm10_ug_m3.isna()
    coarse = np.maximum(simulated[:, 1] - simulated[:, 0], 0)
    # If one particulate channel already exists, keep it exactly as supplied.
    simulated[~a & b, 1] = np.minimum(
        5000, source.loc[~a & b, "pm25_ug_m3"].to_numpy() + coarse[~a & b]
    )
    ratio = simulated[:, 0] / np.maximum(simulated[:, 1], 1e-12)
    simulated[a & ~b, 0] = source.loc[a & ~b, "pm10_ug_m3"].to_numpy() * ratio[a & ~b]
    source.loc[a, "pm25_ug_m3"] = simulated[a, 0]
    source.loc[b, "pm10_ug_m3"] = simulated[b, 1]
    source["pm25_is_synthetic"] = a
    source["pm10_is_synthetic"] = b
    source["evidence_kind"] = np.where(
        a | b, "SYNTHETIC_PM_WITH_MODELED_WEATHER", "MODELED_API_VALUES"
    )
    return (
        source,
        models,
        {
            "seed": seed,
            "fit_rows": len(ref),
            "fit_last_time_utc": ref.timestamp_utc.max().isoformat(),
            "fit_before": cutoff.isoformat(),
            "features": x.columns.tolist(),
            "ar_phi": phi.tolist(),
            "joint_innovation_covariance": np.cov(innovations, rowvar=False).tolist(),
            "synthetic_pm25_rows": int(a.sum()),
            "synthetic_pm10_rows": int(b.sum()),
            "method": "LIGHTGBM_LOG_FINE_AND_COARSE_PM_WITH_PAIRED_AR_INNOVATIONS",
            "purpose": "SIMULATION_OR_OPTIONAL_AUGMENTATION_NOT_OBSERVED_HISTORICAL_PM",
        },
    )


def audit(original, generated):
    """Verify provenance/physical invariants; diagnostics do not measure accuracy."""
    from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS

    original = original.sort_values("timestamp_utc").reset_index(drop=True)
    generated = generated.sort_values("timestamp_utc").reset_index(drop=True)
    if len(original) != len(generated) or not pd.DatetimeIndex(
        pd.to_datetime(original.timestamp_utc, utc=True)
    ).equals(pd.DatetimeIndex(pd.to_datetime(generated.timestamp_utc, utc=True))):
        raise ValueError("Synthetic generation must preserve original timestamps")
    if not np.array_equal(original[WEATHER].to_numpy(), generated[WEATHER].to_numpy()):
        raise ValueError("Original weather values changed")
    diagnostics = {}
    for name, flag in [
        ("pm25_ug_m3", "pm25_is_synthetic"),
        ("pm10_ug_m3", "pm10_is_synthetic"),
    ]:
        missing = original[name].isna().to_numpy()
        if not np.array_equal(missing, generated[flag].to_numpy()):
            raise ValueError(
                "Synthetic flags must identify exactly the originally missing values"
            )
        if not np.array_equal(
            original.loc[~missing, name].to_numpy(),
            generated.loc[~missing, name].to_numpy(),
        ):
            raise ValueError("Existing PM values changed")
        values = generated[name]
        if not values.between(0, 5000).all():
            raise ValueError("Generated PM outside physical bounds")
        diagnostics[name] = {
            "min": float(values.min()),
            "median": float(values.median()),
            "p95": float(values.quantile(0.95)),
            "max": float(values.max()),
            "std": float(values.std()),
            "lag1_correlation": float(values.autocorr()),
        }
    if not np.isfinite(generated[RAW_SENSOR_COLUMNS].to_numpy()).all():
        raise ValueError("Incomplete generated six-channel data")
    filled = generated.pm25_is_synthetic | generated.pm10_is_synthetic
    inconsistent = int(
        (
            generated.loc[filled, "pm25_ug_m3"] > generated.loc[filled, "pm10_ug_m3"]
        ).sum()
    )
    if inconsistent:
        raise ValueError("Synthetic fine PM exceeds total PM10")
    return {
        "rows": len(generated),
        "six_channel_complete_rows": len(generated),
        "weather_values_preserved": True,
        "existing_pm_values_preserved": True,
        "missing_before": {
            k: int(original[k].isna().sum()) for k in RAW_SENSOR_COLUMNS
        },
        "missing_after": {
            k: int(generated[k].isna().sum()) for k in RAW_SENSOR_COLUMNS
        },
        "synthetic_pm_rows": int(filled.sum()),
        "original_complete_pm_rows": int((~filled).sum()),
        "synthetic_pm_order_violations": inconsistent,
        "diagnostics": diagnostics,
        "interpretation": "PROVENANCE_AND_SIMULATION_QA_ONLY_NOT_REALISM_OR_FORECAST_ACCURACY",
    }

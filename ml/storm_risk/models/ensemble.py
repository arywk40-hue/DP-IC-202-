"""Training-only base fits and calibration-only simplex blending."""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from ml.storm_risk.data.splits import inner_split
from ml.storm_risk.models.mlp_model import fit_mlp
from ml.storm_risk.models.ridge_model import fit_ridge, score_ridge
from ml.storm_risk.models.xgb_model import fit_xgb

NAMES = ['ridge', 'xgb', 'mlp']


def fit_base(frame: pd.DataFrame, features: list[str], cfg: dict, audit: list) -> tuple[dict, list[str]]:
    """Reject other roles before preprocessing or model fitting."""
    if not frame.split.eq('train').all():
        raise ValueError('Base fitting accepts only train rows')
    fit, validation = inner_split(frame, cfg)
    if fit.label.nunique() != 2:
        raise ValueError('NOT_READY: inner training needs both confirmed classes')
    scaler = StandardScaler().fit(fit[features])
    x = pd.DataFrame(scaler.transform(fit[features]), index=fit.index, columns=features)
    vx = pd.DataFrame(scaler.transform(validation[features]), index=validation.index, columns=features)
    audit.append(dict(stage='base_fit', role='train', row_ids=fit.index.tolist(), validation_row_ids=validation.index.tolist(),
        maximum_fit_time=fit.time.max().isoformat(), maximum_fit_target=fit.target_time.max().isoformat(),
        inner_validation_start=validation.time.min().isoformat()))
    with warnings.catch_warnings(record=True) as caught, threadpool_limits(limits=cfg['models']['xgb']['n_jobs']):
        warnings.simplefilter('always')
        models = dict(ridge=fit_ridge(x, fit.label, cfg), xgb=fit_xgb(x, fit.label, vx, validation.label, cfg),
            mlp=fit_mlp(x, fit.label, cfg))
    notes = sorted({str(w.message) for w in caught})
    if validation.label.nunique() != 2:
        notes.append('INNER_VALIDATION_HAS_ONLY_ONE_CLASS')
    return dict(models=models, scaler=scaler, features=features), notes


def base_scores(bundle: dict, frame: pd.DataFrame, cfg: dict) -> np.ndarray:
    """Apply the frozen scaler/feature order to an arbitrary inference partition."""
    x = pd.DataFrame(bundle['scaler'].transform(frame[bundle['features']]), index=frame.index, columns=bundle['features'])
    models = bundle['models']
    return np.column_stack([score_ridge(models['ridge'], x, cfg['models']['ridge']['variant']),
        models['xgb'].predict_proba(x)[:, 1], models['mlp'].predict_proba(x)[:, 1]])


def fit_weights(scores: np.ndarray, frame: pd.DataFrame, cfg: dict, audit: list) -> np.ndarray:
    """Select nonnegative simplex coefficients on calib rows, never test rows."""
    if frame.empty or not frame.split.eq('calib').all():
        raise ValueError('Ensemble fitting accepts only nonempty calib rows')
    n = round(1 / cfg['ensemble']['simplex_step'])
    candidates = [np.array([a, b, n - a - b], dtype=float) / n for a in range(n + 1) for b in range(n - a + 1)]
    y = frame.label.to_numpy()
    weights = min(candidates, key=lambda w: (float(np.mean((scores @ w - y) ** 2)), int(np.count_nonzero(w)), tuple(w)))
    audit.append(dict(stage='ensemble_fit', role='calib', row_ids=frame.index.tolist()))
    return weights

"""Active six-channel numerical hybrid; validation-selected, no hazard heads.

All learned components come from the frozen India/Mandi modeled cohort. Missing
history uses explicitly named persistence; no compact-XGBoost default is hidden
behind the hybrid interface. Six physical channels produce six +6h endpoints.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from ml.india_mandi.neural import forward, load_artifact
from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.data import sha256
from ml.six_sensor_forecast.features import build_features

ROOT = Path(__file__).resolve().parents[2]
PROFILE_ID = 'india_mandi_hybrid_6h_v1'
DEFAULT_MODEL = ROOT / 'ml/models' / PROFILE_ID
FAMILIES = ['neural', 'xgb_history', 'ridge_history']


def bounded(values: np.ndarray) -> np.ndarray:
    """Enforce the existing six-channel physical software contract."""
    low, high = np.array([PHYSICAL_RANGES[c] for c in RAW_SENSOR_COLUMNS]).T
    return np.clip(values, low, high)


def select_blend(candidates: dict[str, np.ndarray], truth: np.ndarray, step: float) -> dict:
    """Accept validation arrays only; fit per-target neural choice and MAE blend."""
    truth = np.asarray(truth, float)
    if truth.ndim != 2 or truth.shape[1] != 6 or len(truth) < 2 or not np.isfinite(truth).all():
        raise ValueError('Complete six-target validation rows required')
    if not 0 < step <= 1 or not np.isclose(1 / step, round(1 / step)):
        raise ValueError('Simplex step must divide one')
    if any(np.asarray(v).shape != truth.shape or not np.isfinite(v).all() for v in candidates.values()):
        raise ValueError('Matching finite validation component predictions required')
    neural = [n for n in candidates if n.startswith('residual_mlp_')]
    if not neural or not {'xgb_history', 'ridge_history'} <= set(candidates):
        raise ValueError('Neural, history-XGBoost and ridge families required')
    n = round(1 / step)
    simplex = [np.array([a, b, n - a - b], float) / n for a in range(n + 1) for b in range(n - a + 1)]
    heads = {}
    for j, target in enumerate(RAW_SENSOR_COLUMNS):
        chosen = min(neural, key=lambda name: float(np.abs(candidates[name][:, j] - truth[:, j]).mean()))
        matrix = np.column_stack([candidates[chosen][:, j], candidates['xgb_history'][:, j], candidates['ridge_history'][:, j]])
        weights = min(simplex, key=lambda w: (float(np.abs(matrix @ w - truth[:, j]).mean()), int(np.count_nonzero(w)), tuple(w)))
        heads[target] = dict(neural=chosen, weights=dict(zip(FAMILIES, weights.tolist())),
            validation_mae=float(np.abs(matrix @ weights - truth[:, j]).mean()))
    return dict(schema_version='indra_mandi_hybrid_weights_v1', family_order=FAMILIES, heads=heads,
        selection='CHRONOLOGICAL_VALIDATION_MAE_ONLY', validation_rows=len(truth), simplex_step=step)


class Components:
    """Load hash-checked frozen Mandi components once per batch/runtime."""
    def __init__(self, base: Path, neural: dict[str, Path], *, threads: int = 2):
        self.base = Path(base)
        self.report = json.loads((self.base / 'training_report.json').read_text())
        r = self.report
        if (r.get('model_country') != 'IN' or r.get('china_data_or_weights_used') is not False
                or r['sensor_profile'] != RAW_SENSOR_COLUMNS or r['horizon_hours'] != 6):
            raise ValueError('India-trained complete six-channel model required')
        self.features = r['architecture']['teacher_features']
        self.boosters = {}
        for target in RAW_SENSOR_COLUMNS:
            item = r['models'][target]
            path = (self.base / item['teacher_file']).resolve()
            if not path.is_relative_to(self.base.resolve()) or sha256(path) != item['teacher_sha256']:
                raise ValueError('History-XGBoost component checksum mismatch')
            model = xgb.Booster(params={'nthread': threads})
            model.load_model(path)
            self.boosters[target] = model
        ridge = json.loads((self.base / 'ridge_report.json').read_text())
        path = (self.base / ridge['artifact']).resolve()
        if (ridge['features'] != self.features or ridge['targets'] != RAW_SENSOR_COLUMNS
                or not path.is_relative_to(self.base.resolve()) or sha256(path) != ridge['sha256']):
            raise ValueError('Ridge component checksum/feature mismatch')
        with np.load(path, allow_pickle=False) as saved:
            self.ridge = {k: saved[k] for k in saved.files}
        expected = dict(mean=(66,), std=(66,), coefficients=(6, 66), intercepts=(6,))
        if (set(self.ridge) != set(expected) or any(self.ridge[k].shape != s or not np.isfinite(self.ridge[k]).all() for k, s in expected.items())
                or (self.ridge['std'] <= 0).any()):
            raise ValueError('Invalid ridge arrays')
        self.neural = {}
        for name, directory in neural.items():
            state, metadata = load_artifact(directory)
            if (metadata['features'] != self.features or metadata['source_sha256'] != r['source']['observations_sha256']
                    or metadata.get('country') != 'IN'):
                raise ValueError('Neural feature/source/country mismatch')
            self.neural[name] = state

    def predict(self, features: pd.DataFrame, current: pd.DataFrame) -> dict[str, np.ndarray]:
        """Predict complete 66-feature histories with each frozen family."""
        if features.columns.tolist() != self.features or current.columns.tolist() != RAW_SENSOR_COLUMNS:
            raise ValueError('Hybrid feature order mismatch')
        x, now = features.to_numpy(float), current.to_numpy(float)
        if not np.isfinite(x).all() or not np.isfinite(now).all():
            raise ValueError('Complete finite hybrid inputs required')
        matrix = xgb.DMatrix(features, feature_names=self.features)
        boosted = np.column_stack([now[:, j] + self.report['models'][t]['teacher_weight'] * self.boosters[t].predict(matrix)
            for j, t in enumerate(RAW_SENSOR_COLUMNS)])
        ridge = self.ridge
        linear = now + ((x - ridge['mean']) / ridge['std']) @ ridge['coefficients'].T + ridge['intercepts']
        return {**{name: forward(state, x, now) for name, state in self.neural.items()},
                'xgb_history': bounded(boosted), 'ridge_history': bounded(linear)}


def blend(candidates: dict[str, np.ndarray], weights: dict) -> np.ndarray:
    """Blend endpoint predictions, never incompatible parameter matrices."""
    output = []
    for j, target in enumerate(RAW_SENSOR_COLUMNS):
        head = weights['heads'][target]
        output.append(sum(head['weights'][family] * candidates[head['neural'] if family == 'neural' else family][:, j]
            for family in FAMILIES))
    return bounded(np.column_stack(output))


class Hybrid:
    """Versioned gateway predictor with explicit missing-current/history states."""
    def __init__(self, directory: Path = DEFAULT_MODEL, *, component_root: Path = ROOT):
        self.directory, root = Path(directory), Path(component_root).resolve()
        self.profile = json.loads((self.directory / 'profile.json').read_text())
        p = self.profile
        if (p.get('schema_version') != 'indra_mandi_hybrid_profile_v1' or p.get('id') != PROFILE_ID
                or p.get('sensors') != RAW_SENSOR_COLUMNS or p.get('horizon_hours') != 6 or p.get('history_hours') != 24
                or p.get('country') != 'IN' or p.get('field_validated') is not False or p.get('warmup_fallback') != 'persistence'):
            raise ValueError('Incompatible hybrid profile')
        if type(p['threads']) is not int or not 1 <= p['threads'] <= 8:
            raise ValueError('Bounded hybrid runtime thread count required')
        for relative, checksum in p['component_hashes'].items():
            path = (root / relative).resolve()
            if not path.is_relative_to(root / 'ml/models') or sha256(path) != checksum:
                raise ValueError('Hybrid component checksum/path mismatch')
        path = (self.directory / p['weights_file']).resolve()
        if not path.is_relative_to(self.directory.resolve()) or sha256(path) != p['weights_sha256']:
            raise ValueError('Hybrid blend checksum/path mismatch')
        self.weights = json.loads(path.read_text())
        if (self.weights.get('schema_version') != 'indra_mandi_hybrid_weights_v1'
                or self.weights.get('family_order') != FAMILIES or set(self.weights['heads']) != set(RAW_SENSOR_COLUMNS)):
            raise ValueError('Invalid hybrid blend contract')
        for head in self.weights['heads'].values():
            if head['neural'] not in p['neural_candidates'] or set(head['weights']) != set(FAMILIES):
                raise ValueError('Invalid hybrid head selection')
            values = np.array([head['weights'][k] for k in FAMILIES], float)
            if not np.isfinite(values).all() or (values < 0).any() or not np.isclose(values.sum(), 1):
                raise ValueError('Invalid convex hybrid coefficients')
        base = (root / p['base_model']).resolve()
        neural = {n: (root / v).resolve() for n, v in p['neural_candidates'].items()}
        directories = [base, *neural.values()]
        if any(not d.is_relative_to(root / 'ml/models') for d in directories):
            raise ValueError('Hybrid component directory outside model root')
        required = [base / name for name in ('training_report.json', 'ridge_report.json')]
        for directory in neural.values():
            required.append(directory / 'model.json')
        for path in required:
            if str(path.relative_to(root)) not in p['component_hashes']:
                raise ValueError('Hybrid component metadata missing from checksum manifest')
        teacher_report = json.loads((base / 'training_report.json').read_text())
        ridge_report = json.loads((base / 'ridge_report.json').read_text())
        arrays = [base / ridge_report['artifact'], *[base / m['teacher_file'] for m in teacher_report['models'].values()]]
        arrays += [d / json.loads((d / 'model.json').read_text())['artifact'] for d in neural.values()]
        if any(not path.resolve().is_relative_to(root / 'ml/models') or str(path.resolve().relative_to(root)) not in p['component_hashes'] for path in arrays):
            raise ValueError('Hybrid learned weights missing from checksum manifest')
        self.components = Components(base, neural, threads=p['threads'])
        self.profile_sha256 = sha256(self.directory / 'profile.json')

    def predict(self, observations: pd.DataFrame) -> pd.DataFrame:
        """Use the hybrid on full histories and persistence only during warm-up."""
        frame, features = build_features(observations)
        now = frame[RAW_SENSOR_COLUMNS]
        current_ok = np.isfinite(now.to_numpy()).all(axis=1)
        complete = current_ok & np.isfinite(features.to_numpy()).all(axis=1)
        values = np.full((len(frame), 6), np.nan)
        values[current_ok] = now.loc[current_ok].to_numpy()
        if complete.any():
            values[complete] = blend(self.components.predict(features.loc[complete], now.loc[complete]), self.weights)
        result = frame[['location_id', 'timestamp_utc']].copy()
        result['forecast_timestamp_utc'] = frame.timestamp_utc + pd.Timedelta(hours=6)
        result['status'] = np.where(complete, 'HYBRID_READY', np.where(current_ok, 'WARMING_UP_PERSISTENCE', 'MISSING_CURRENT_SENSOR'))
        result['model_id'] = np.where(complete, PROFILE_ID, np.where(current_ok, 'persistence_six_sensor_v1', 'unavailable'))
        for j, target in enumerate(RAW_SENSOR_COLUMNS):
            result['forecast_' + target] = values[:, j]
        return result

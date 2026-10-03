"""Current-time six-target spatial ensemble. No query-node sensor inputs.

Models stay in memory; no pickle loading. Caller supplies authenticated,
QC-approved simultaneous snapshots. Error bands are empirical, not guarantees.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS, PHYSICAL_RANGES


def coordinates(lat, lon):
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError) as exc:
        raise ValueError('Invalid coordinates') from exc
    if not math.isfinite(lat + lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError('Invalid coordinates')
    return lat, lon


def snapshot_features(nodes, latitude, longitude, timestamp):
    """Haversine distances; per-channel missing values; colocated nodes averaged."""
    lat, lon = coordinates(latitude, longitude)
    stamp = pd.Timestamp(timestamp)
    if pd.isna(stamp) or stamp.tzinfo is None:
        raise ValueError('Explicit timezone required')
    if not isinstance(nodes, list) or len(nodes) > 256:
        raise ValueError('Expected at most 256 nodes')
    distances, readings = [], []
    for node in nodes:
        try:
            a, b = coordinates(node['latitude'], node['longitude'])
            time = pd.Timestamp(node['timestamp_utc'])
            if pd.isna(time) or time.tzinfo is None or time != stamp:
                continue  # Offline/stale snapshots cannot supply present features.
            phi, dphi, dlon = np.radians([a, a-lat, b-lon])
            h = np.sin(dphi/2)**2 + np.cos(np.radians(lat))*np.cos(phi)*np.sin(dlon/2)**2
            distances.append(6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(h, 0, 1))))
            values = []
            for name in RAW_SENSOR_COLUMNS:
                try:
                    value = float(node.get(name, np.nan))
                except (TypeError, ValueError):
                    value = np.nan
                lo, hi = PHYSICAL_RANGES[name]
                values.append(value if np.isfinite(value) and lo <= value <= hi else np.nan)
            readings.append(values)
        except (KeyError, TypeError, ValueError):
            continue
    baseline = np.full(6, np.nan)
    spread, nearest = baseline.copy(), baseline.copy()
    counts = np.zeros(6, dtype=int)
    values = np.asarray(readings, dtype=float).reshape(-1, 6)
    d = np.asarray(distances)
    for i in range(6):
        valid = np.isfinite(values[:, i])
        counts[i] = valid.sum()
        if not valid.any():
            continue
        distances_i, v = d[valid], values[valid, i]
        nearest[i] = distances_i.min()
        exact = distances_i < 1e-6
        weights = exact.astype(float) if exact.any() else (distances_i.min()/distances_i)**2
        weights /= weights.sum()
        baseline[i] = weights @ v
        spread[i] = np.sqrt(weights @ (v-baseline[i])**2)
    phi, lam = np.radians([lat, lon])
    hour = stamp.tz_convert('UTC').hour + stamp.minute/60
    day = stamp.dayofyear
    context = [np.cos(phi)*np.cos(lam), np.cos(phi)*np.sin(lam), np.sin(phi),
               np.sin(2*np.pi*hour/24), np.cos(2*np.pi*hour/24),
               np.sin(2*np.pi*day/365.25), np.cos(2*np.pi*day/365.25)]
    return np.r_[baseline, spread, nearest, context], baseline, counts


class SpatialEnsemble:
    def __init__(self, seed=42):
        self.seed = seed
        self.heads = {}

    def fit(self, x, y, validation_x, validation_y):
        """Caller must isolate stations/time. Second validation half calibrates bands."""
        x, y, vx, vy = map(lambda a: np.asarray(a, dtype=float), (x, y, validation_x, validation_y))
        if x.ndim != 2 or x.shape[1] != 25 or vx.ndim != 2 or vx.shape[1] != 25:
            raise ValueError('Expected 25 neighbor/context features')
        if y.shape != (len(x), 6) or vy.shape != (len(vx), 6):
            raise ValueError('Expected six observed targets')
        self.heads = {}
        midpoint = len(vx)//2
        for i, name in enumerate(RAW_SENSOR_COLUMNS):
            lo, hi = PHYSICAL_RANGES[name]
            train = np.isfinite(y[:, i]) & np.isfinite(x[:, i]) & (y[:, i] >= lo) & (y[:, i] <= hi)
            valid = np.isfinite(vy[:, i]) & np.isfinite(vx[:, i]) & (vy[:, i] >= lo) & (vy[:, i] <= hi)
            selection = valid & (np.arange(len(vx)) < midpoint)
            calibration = valid & (np.arange(len(vx)) >= midpoint)
            if train.sum() < 20 or selection.sum() < 10 or calibration.sum() < 10:
                continue  # IDW remains available without a fitted head.
            scale = max(float(np.std(y[train, i])), 1e-3)
            target = (y[train, i]-x[train, i])/scale
            models = {
                'boosting': HistGradientBoostingRegressor(max_iter=60, max_leaf_nodes=15, random_state=self.seed),
                'neural_net': make_pipeline(SimpleImputer(keep_empty_features=True), StandardScaler(),
                    MLPRegressor(hidden_layer_sizes=(16, 8), max_iter=150, random_state=self.seed)),
            }
            predictions = {'idw': vx[:, i].copy()}
            failures = {}
            for kind, model in list(models.items()):
                try:
                    model.fit(x[train], target)
                    pred = np.clip(vx[:, i] + scale*model.predict(vx), lo, hi)
                    if not np.isfinite(pred[valid]).all():
                        raise ValueError('Nonfinite model prediction')
                    predictions[kind] = pred
                except Exception as exc:
                    failures[kind] = type(exc).__name__
                    del models[kind]
            errors = {kind: np.mean(np.abs(pred[selection]-vy[selection, i])) for kind, pred in predictions.items()}
            inverse = {kind: 1/max(float(error), 1e-6) for kind, error in errors.items()}
            weights = {kind: value/sum(inverse.values()) for kind, value in inverse.items()}
            blended = sum(weights[kind]*pred for kind, pred in predictions.items())
            band = float(np.quantile(np.abs(blended[calibration]-vy[calibration, i]), .9))
            self.heads[name] = dict(models=models, scale=scale, weights=weights, p90=band,
                lower=np.nanmin(x[train], axis=0), upper=np.nanmax(x[train], axis=0), failures=failures)
        return self

    def predict(self, nodes, latitude, longitude, timestamp):
        x, baseline, counts = snapshot_features(nodes, latitude, longitude, timestamp)
        result = {'status': 'EXPERIMENTAL_CURRENT_TIME_INTERPOLATION', 'targets': {}}
        for i, name in enumerate(RAW_SENSOR_COLUMNS):
            if not np.isfinite(baseline[i]):
                result['targets'][name] = dict(prediction=None, absolute_error_p90=None, status='UNAVAILABLE', models=[])
                continue
            head = self.heads.get(name)
            predictions = {'idw': baseline[i]}
            failed = []
            ood = False
            if head is not None:
                # Envelope check is deliberately conservative, not an OOD probability.
                # Less disagreement / closer nodes is not an adverse shift.
                # Cyclic time features have a known domain, not a fitted envelope.
                ood = bool(not np.isfinite(x).all()
                    or np.any((x[:6] < head['lower'][:6]) | (x[:6] > head['upper'][:6]))
                    or np.any(x[6:18] > head['upper'][6:18])
                    or np.any((x[18:21] < head['lower'][18:21]) | (x[18:21] > head['upper'][18:21])))
                if not ood and counts[i] > 1:
                    for kind, model in head['models'].items():
                        try:
                            pred = float(baseline[i] + head['scale']*model.predict(x.reshape(1, -1))[0])
                            if not np.isfinite(pred):
                                raise ValueError('Nonfinite prediction')
                            predictions[kind] = np.clip(pred, *PHYSICAL_RANGES[name])
                        except Exception:
                            failed.append(kind)
            weights = head['weights'] if head else {'idw': 1.}
            total = sum(weights[kind] for kind in predictions)
            value = sum(weights[kind]*pred for kind, pred in predictions.items())/total
            degraded = head is None or ood or counts[i] < 2 or len(predictions) != 3
            result['targets'][name] = dict(prediction=float(value),
                absolute_error_p90=None if degraded else head['p90'],
                status='DEGRADED_IDW_OR_PARTIAL' if degraded else 'ENSEMBLE',
                models=list(predictions), failed_models=failed, out_of_distribution=ood,
                contributing_nodes=int(counts[i]))
        return result

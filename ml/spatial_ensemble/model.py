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
    day = stamp.tz_convert('UTC').dayofyear
    context = [np.cos(phi)*np.cos(lam), np.cos(phi)*np.sin(lam), np.sin(phi),
               np.sin(2*np.pi*hour/24), np.cos(2*np.pi*hour/24),
               np.sin(2*np.pi*day/365.25), np.cos(2*np.pi*day/365.25)]
    return np.r_[baseline, spread, nearest, context], baseline, counts


class SpatialEnsemble:
    def __init__(self, seed=42, extended_features=False, max_distance_km=None, refuse_outside=True):
        self.seed = seed
        self.extended_features = extended_features
        if max_distance_km is not None:
            max_distance_km = float(max_distance_km)
            if not math.isfinite(max_distance_km) or max_distance_km <= 0:
                raise ValueError('Positive finite maximum distance required')
        self.max_distance_km = max_distance_km
        self.refuse_outside = refuse_outside
        self.heads = {}

    def fit(self, x, y, validation_x, validation_y):
        """Caller must isolate stations/time. Second validation half calibrates bands."""
        x, y, vx, vy = map(lambda a: np.asarray(a, dtype=float), (x, y, validation_x, validation_y))
        width = 33 if self.extended_features else 25
        if x.ndim != 2 or x.shape[1] != width or vx.ndim != 2 or vx.shape[1] != width:
            raise ValueError(f'Expected {width} neighbor/context features')
        # Core-only labels use [T, RH, station pressure, wind]; PM heads are masked.
        def masked_labels(labels):
            if labels.ndim == 2 and labels.shape[1] == 4:
                padded = np.full((len(labels), 6), np.nan)
                padded[:, [0, 1, 2, 5]] = labels
                return padded
            return labels
        y, vy = masked_labels(y), masked_labels(vy)
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
            # Each target masks absent channels. PM never gates the four core heads.
            candidates = [j for j in range(width) if j not in [3,4,9,10,15,16] or name in ['pm25_ug_m3','pm10_ug_m3']]
            active = np.array([j for j in candidates if np.isfinite(x[train, j]).any()], dtype=int)
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
                    model.fit(x[train][:, active], target)
                    pred = np.clip(vx[:, i] + scale*model.predict(vx[:, active]), lo, hi)
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
                lower=np.nanmin(x[train], axis=0), upper=np.nanmax(x[train], axis=0), failures=failures, active=active)
        return self

    def predict(self, nodes, latitude, longitude, timestamp, query_elevation_m=None, query_slope_deg=None, background=None):
        if self.extended_features:
            from ml.spatial_ensemble.network import named_features
            x, baseline, counts = named_features(nodes, latitude, longitude, timestamp, query_elevation_m, query_slope_deg, background)
        else:
            x, baseline, counts = snapshot_features(nodes, latitude, longitude, timestamp)
        from ml.spatial_ensemble.network import guard
        geometry = guard(nodes, latitude, longitude, timestamp, self.max_distance_km or 20)
        if self.max_distance_km is not None and not geometry['allowed'] and self.refuse_outside:
            return {'status':'REFUSED_NETWORK_GEOMETRY', 'geometry':geometry, 'targets':{name:dict(prediction=None, absolute_error_p90=None, status='REFUSED', models=[]) for name in RAW_SENSOR_COLUMNS}}
        result = {'status': 'EXPERIMENTAL_CURRENT_TIME_INTERPOLATION', 'targets': {}, 'geometry': geometry}
        for i, name in enumerate(RAW_SENSOR_COLUMNS):
            if not np.isfinite(baseline[i]):
                result['targets'][name] = dict(prediction=None, absolute_error_p90=None, status='UNAVAILABLE', models=[])
                continue
            valid_nodes = []
            for node in nodes:
                if not isinstance(node, dict):continue
                try:
                    value = float(node.get(name, np.nan))
                    if np.isfinite(value) and PHYSICAL_RANGES[name][0] <= value <= PHYSICAL_RANGES[name][1]:valid_nodes.append(node)
                except (ValueError, TypeError):pass
            target_geometry = guard(valid_nodes, latitude, longitude, timestamp, self.max_distance_km or 20)
            if self.max_distance_km is not None and self.refuse_outside and not target_geometry['allowed']:
                result['targets'][name] = dict(prediction=None, absolute_error_p90=None, status='REFUSED_TARGET_NETWORK_GEOMETRY', models=[], geometry=target_geometry)
                continue
            head = self.heads.get(name)
            predictions = {'idw': baseline[i]}
            failed = []
            ood = False
            if head is not None:
                # Envelope check is deliberately conservative, not an OOD probability.
                # Less disagreement / closer nodes is not an adverse shift.
                # Cyclic time features have a known domain, not a fitted envelope.
                active = head.get('active', np.arange(len(x)))
                finite = np.isfinite(x[active])
                checked = active[active < 21]
                values = x[checked]
                upper = head['upper'][checked]
                lower = head['lower'][checked]
                # Spread/distance can improve below the fitted lower bound.
                min_check = (checked < 6) | (checked >= 18)
                ood = bool(not finite.all() or np.any(values > upper)
                    or np.any(values[min_check] < lower[min_check]))
                if len(x) > 25:
                    terrain = active[active >= 25]
                    ood = ood or bool(np.any(x[terrain] < head['lower'][terrain]) or np.any(x[terrain] > head['upper'][terrain]))
                if not ood and counts[i] > 1:
                    for kind, model in head['models'].items():
                        try:
                            pred = float(baseline[i] + head['scale']*model.predict(x[active].reshape(1, -1))[0])
                            if not np.isfinite(pred):
                                raise ValueError('Nonfinite prediction')
                            predictions[kind] = np.clip(pred, *PHYSICAL_RANGES[name])
                        except Exception:
                            failed.append(kind)
            weights = head['weights'] if head else {'idw': 1.}
            total = sum(weights[kind] for kind in predictions)
            value = sum(weights[kind]*pred for kind, pred in predictions.items())/total
            degraded = not target_geometry['allowed'] or head is None or ood or counts[i] < 2 or len(predictions) != 3
            result['targets'][name] = dict(prediction=float(value),
                # Historical row quantiles were never independently checked.
                # Only EpisodeBands may authorize a nominal serving interval.
                absolute_error_p90=None,
                calibration_status='UNCHECKED_LEGACY_ROW_QUANTILE',
                status='DEGRADED_IDW_OR_PARTIAL' if degraded else 'ENSEMBLE',
                models=list(predictions), failed_models=failed, out_of_distribution=ood,
                contributing_nodes=int(counts[i]), geometry=target_geometry)
        return result

"""Multi-node spatial heatmap: per-feature and per-event interpolation."""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from ml.event_classifier.predict import EventPredictor
from ml.six_sensor_forecast.contract import PHYSICAL_RANGES

from ml.event_classifier.features import (
    ALL_EVENT_FEATURE_COLS,
    EVENT_NAMES,
    RAW_FEATURE_COLS,
    build_features,
)

NodeReading = dict[str, float]


def _idw_interpolate(
    node_xy: np.ndarray,
    node_values: np.ndarray,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    power: float = 2.0,
) -> np.ndarray:
    rows, cols = grid_x.shape
    result = np.zeros((rows, cols), dtype=np.float64)
    eps = 1e-10

    for r in range(rows):
        for c in range(cols):
            gx, gy = grid_x[r, c], grid_y[r, c]
            dists = np.sqrt((node_xy[:, 0] - gx) ** 2 + (node_xy[:, 1] - gy) ** 2)
            if np.any(dists < eps):
                result[r, c] = node_values[np.argmin(dists)]
            else:
                weights = 1.0 / dists ** power
                result[r, c] = np.dot(weights, node_values) / weights.sum()
    return result.astype(np.float32)


def _kriging_available() -> bool:
    try:
        import pykrige  # noqa: F401
        return True
    except ImportError:
        return False


def _ok_interpolate(
    node_xy: np.ndarray,
    node_values: np.ndarray,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    variogram_model: str = "spherical",
) -> np.ndarray:
    from pykrige.ok import OrdinaryKriging  # type: ignore

    ok = OrdinaryKriging(
        node_xy[:, 0],
        node_xy[:, 1],
        node_values,
        variogram_model=variogram_model,
        verbose=False,
        enable_plotting=False,
    )
    z, _ = ok.execute("grid", np.unique(grid_x[0]), np.unique(grid_y[:, 0]))
    return z.astype(np.float32)


def interpolate_feature(
    node_xy: np.ndarray,
    node_values: np.ndarray,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    prefer_kriging: bool = True,
) -> tuple[np.ndarray, str]:
    n_nodes = len(node_xy)
    if prefer_kriging and n_nodes >= 3 and _kriging_available():
        try:
            value = np.asarray(_ok_interpolate(node_xy, node_values, grid_x, grid_y))
            if value.shape != grid_x.shape or not np.isfinite(value).all():
                raise ValueError("Nonfinite or incomplete kriging result")
            return value, "kriging"
        except Exception as exc:
            warnings.warn(f"Kriging failed ({exc}); falling back to IDW.", RuntimeWarning)
    return _idw_interpolate(node_xy, node_values, grid_x, grid_y), "IDW"


def _timestamp(value):
    stamp = pd.Timestamp(value)
    if pd.isna(stamp) or stamp.tzinfo is None:
        raise ValueError('Use explicit timezone-aware timestamps')
    return stamp.tz_convert('UTC')


class HeatmapBuilder:
    """Planar coordinates in one common local projection; all nodes simultaneous.

    Event inputs require a `history` list of exactly seven hourly observation
    dictionaries, ending at each node's timestamp. Missing history yields NaNs.
    """
    def __init__(self, grid_shape=(50, 50), grid_extent=(0., 1., 0., 1.),
                 model_dir: Path | None = None, prefer_kriging=True,
                 allow_extrapolation=False):
        if (len(grid_shape) != 2 or any(not isinstance(n, int) or n < 2 for n in grid_shape)
                or np.prod(grid_shape) > 10000):
            raise ValueError('Grid must be 2D, at least 2x2 and at most 10000 cells')
        if (len(grid_extent) != 4 or not np.isfinite(grid_extent).all()
                or grid_extent[0] >= grid_extent[1] or grid_extent[2] >= grid_extent[3]):
            raise ValueError('Invalid grid extent')
        self.grid_shape = grid_shape
        self.prefer_kriging = prefer_kriging
        self.allow_extrapolation = allow_extrapolation
        self.grid_x, self.grid_y = np.meshgrid(
            np.linspace(grid_extent[0], grid_extent[1], grid_shape[1]),
            np.linspace(grid_extent[2], grid_extent[3], grid_shape[0]))
        self.predictor = EventPredictor(model_dir) if model_dir is not None else None

    def _validate_nodes(self, nodes):
        if len(nodes) < 2:
            raise ValueError('At least two sensor nodes are required')
        xy = np.array([[n['x'], n['y']] for n in nodes], dtype=float)
        if not np.isfinite(xy).all() or len(np.unique(xy, axis=0)) != len(nodes):
            raise ValueError('Coordinates must be finite and distinct')
        times = [_timestamp(n['timestamp_utc']) for n in nodes]
        if any(t != times[0] for t in times):
            raise ValueError('Node observations must have the same timestamp')
        return xy

    def _support(self, xy):
        query = np.column_stack([self.grid_x.ravel(), self.grid_y.ravel()])
        centered = xy - xy[0]
        if len(xy) >= 3 and np.linalg.matrix_rank(centered) == 2:
            from scipy.spatial import Delaunay
            supported = Delaunay(xy).find_simplex(query, tol=1e-10) >= 0
        else:
            direction = centered[np.argmax(np.linalg.norm(centered, axis=1))]
            length = np.linalg.norm(direction)
            direction /= length
            positions = centered @ direction
            offset = query - xy[0]
            along = offset @ direction
            distance = np.linalg.norm(offset - along[:, None] * direction, axis=1)
            supported = ((distance <= max(length, 1.) * 1e-8)
                         & (along >= positions.min()-1e-8) & (along <= positions.max()+1e-8))
        return supported.reshape(self.grid_shape)

    def _interpolate(self, xy, values):
        valid = np.isfinite(values)
        if valid.sum() < 2:
            return np.full(self.grid_shape, np.nan, dtype=np.float32), 'unavailable'
        selected = xy[valid]
        result, method = interpolate_feature(selected, values[valid], self.grid_x,
                                             self.grid_y, self.prefer_kriging)
        if not self.allow_extrapolation:
            result[~self._support(selected)] = np.nan
        return result, method

    def feature_heatmaps(self, nodes):
        xy = self._validate_nodes(nodes)
        maps = np.full((6, *self.grid_shape), np.nan, dtype=np.float32)
        methods = {}
        for i, name in enumerate(RAW_FEATURE_COLS):
            values = np.array([n.get(name, np.nan) for n in nodes], dtype=float)
            low, high = PHYSICAL_RANGES[name]
            values[(values < low) | (values > high)] = np.nan
            maps[i], methods[name] = self._interpolate(xy, values)
            maps[i][(maps[i] < low) | (maps[i] > high)] = np.nan
        return maps, methods

    def _history(self, node, identity):
        rows = node.get('history', [])
        if not rows:
            return None
        if len(rows) != 7:
            raise ValueError('Event history must contain exactly seven hourly readings')
        times = [_timestamp(row['timestamp_utc']) for row in rows]
        if times[-1] != _timestamp(node['timestamp_utc']) or any(
                times[i] - times[i-1] != pd.Timedelta(hours=1) for i in range(1, 7)):
            raise ValueError('History must be consecutive and end at the node timestamp')
        raw = np.array([[row.get(c, np.nan) for c in RAW_FEATURE_COLS] for row in rows], dtype=float)
        snapshot = np.array([node.get(c, np.nan) for c in RAW_FEATURE_COLS], dtype=float)
        if not np.array_equal(raw[-1], snapshot, equal_nan=True):
            raise ValueError('Snapshot differs from last historical reading')
        for i, name in enumerate(RAW_FEATURE_COLS):
            low, high = PHYSICAL_RANGES[name]
            if not np.isfinite(raw[:, i]).all() or ((raw[:, i] < low) | (raw[:, i] > high)).any():
                return None
        frame = pd.DataFrame(raw, columns=RAW_FEATURE_COLS)
        frame['timestamp_utc'] = times
        frame['location_id'] = str(identity)
        return frame

    def event_heatmaps_strategy_a(self, nodes):
        if self.predictor is None:
            raise ValueError('An event model is required')
        xy = self._validate_nodes(nodes)
        features = np.full((len(nodes), 17), np.nan, dtype=np.float32)
        for i, node in enumerate(nodes):
            frame = self._history(node, i)
            if frame is not None:
                _, derived = build_features(frame)
                features[i] = derived[ALL_EVENT_FEATURE_COLS].iloc[-1]
        scores = self.predictor.predict_features(features)
        maps = np.full((12, *self.grid_shape), np.nan, dtype=np.float32)
        methods = {}
        for i, name in enumerate(EVENT_NAMES):
            maps[i], methods[name] = self._interpolate(xy, scores[:, i])
            maps[i] = np.clip(maps[i], 0, 1)
        return maps, methods

    def event_heatmaps_strategy_b(self, nodes):
        if self.predictor is None:
            raise ValueError('An event model is required')
        self._validate_nodes(nodes)
        histories = [self._history(node, i) for i, node in enumerate(nodes)]
        maps = np.full((12, *self.grid_shape), np.nan, dtype=np.float32)
        if any(frame is None for frame in histories):
            return maps, {name: 'unavailable_history' for name in EVENT_NAMES}
        # Interpolate all seven time slices, then derive history at each cell.
        # This is deliberately different from interpolating derived features.
        slices = []
        for hour in range(7):
            time_nodes = [dict(x=node['x'], y=node['y'], **frame.iloc[hour].to_dict())
                          for node, frame in zip(nodes, histories)]
            values, _ = self.feature_heatmaps(time_nodes)
            slices.append(values.reshape(6, -1).T)
        values = np.stack(slices)  # hour, cell, channel
        cells = values.shape[1]
        frame = pd.DataFrame(values.transpose(1, 0, 2).reshape(-1, 6), columns=RAW_FEATURE_COLS)
        frame['location_id'] = np.repeat(np.arange(cells).astype(str), 7)
        frame['timestamp_utc'] = np.tile(histories[0].timestamp_utc.to_numpy(), cells)
        prediction = self.predictor.predict(frame)
        latest = prediction.groupby('location_id', sort=False).tail(1)
        order = latest.location_id.astype(int).to_numpy()
        flat = np.full((cells, 12), np.nan, dtype=np.float32)
        flat[order] = latest[EVENT_NAMES].to_numpy()
        maps = flat.T.reshape(12, *self.grid_shape)
        return maps, {name: ('interpolate_history_then_classify' if trained else 'untrained')
                      for name, trained in zip(EVENT_NAMES, self.predictor.trained_mask)}

    def run(self, nodes, strategy='A'):
        if strategy not in ('A', 'B', 'both'):
            raise ValueError('Strategy must be A, B or both')
        xy = self._validate_nodes(nodes)
        result = {'n_nodes': len(nodes), 'strategy': strategy,
                  'status': 'EXPERIMENTAL_SPATIAL_RULE_ESTIMATE',
                  'timestamp_utc': _timestamp(nodes[0]['timestamp_utc']).isoformat(),
                  'support_mask': self._support(xy),
                  'extrapolation_enabled': self.allow_extrapolation,
                  'score_meaning': 'uncalibrated current-time rule match, not a future hazard probability'}
        result['feature_maps'], result['feature_methods'] = self.feature_heatmaps(nodes)
        if self.predictor is not None:
            result['trained_event_mask'] = self.predictor.trained_mask.copy()
            if strategy in ('A', 'both'):
                result['event_maps'], result['event_methods'] = self.event_heatmaps_strategy_a(nodes)
            if strategy in ('B', 'both'):
                b, methods = self.event_heatmaps_strategy_b(nodes)
                result['event_maps_b' if strategy == 'both' else 'event_maps'] = b
                result['event_methods_b' if strategy == 'both' else 'event_methods'] = methods
            if strategy == 'both':
                difference = np.abs(result['event_maps'] - result['event_maps_b'])
                result['strategy_mean_absolute_difference'] = {
                    name: float(d[np.isfinite(d)].mean()) if np.isfinite(d).any() else None
                    for name, d in zip(EVENT_NAMES, difference)}
        return result


def main():
    """Export grid arrays and an explicit validity/provenance manifest."""
    import argparse
    import json
    from ml.six_sensor_forecast.data import sha256
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='JSON: nodes with timestamp, x/y, six channels and optional history')
    parser.add_argument('--model', type=Path, default=Path('ml/models/uci_beijing_event_rules_6sensor'))
    parser.add_argument('--strategy', choices=['A', 'B', 'both'], default='A')
    parser.add_argument('--grid-size', type=int, default=25)
    parser.add_argument('--extent', nargs=4, type=float, required=True, metavar=('XMIN', 'XMAX', 'YMIN', 'YMAX'))
    parser.add_argument('--allow-extrapolation', action='store_true')
    parser.add_argument('--idw-only', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text())
    builder = HeatmapBuilder((args.grid_size, args.grid_size), tuple(args.extent), args.model,
                             not args.idw_only, args.allow_extrapolation)
    result = builder.run(payload['nodes'], args.strategy)
    arrays = {k: v for k, v in result.items() if isinstance(v, np.ndarray)}
    arrays.update(grid_x=builder.grid_x, grid_y=builder.grid_y)
    manifest = {k: v for k, v in result.items() if not isinstance(v, np.ndarray)}
    manifest.update(input_sha256=sha256(args.input),
                    source_provenance=payload.get('provenance', 'UNSPECIFIED'),
                    event_names=EVENT_NAMES, feature_names=RAW_FEATURE_COLS,
                    valid_cells={k: int(np.isfinite(v).sum()) for k, v in arrays.items() if k.endswith('maps') or k=='event_maps_b'},
                    array_file='maps.npz')
    args.output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output/'maps.npz', **arrays)
    (args.output/'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False)+'\n')
    print(args.output/'manifest.json')


if __name__ == '__main__':
    main()

"""N distinct neighbouring cells, each counted once in a trailing time window."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
import xarray as xr


def confirm_neighbours(score_grid: xr.DataArray, threshold: float, radius_deg: float, n_min: int, window_hours: int) -> np.ndarray:
    """Confirm current exceedances from past/current neighbours, never future hours."""
    if not 0 <= threshold <= 1 or radius_deg <= 0 or n_min < 1 or window_hours < 1:
        raise ValueError('Invalid spatial confirmation parameters')
    data = score_grid.transpose('time', 'lat', 'lon')
    times = pd.DatetimeIndex(data.time.values)
    if not times.is_unique or not times.is_monotonic_increasing:
        raise ValueError('Unique ordered grid hours required')
    lat, lon = np.meshgrid(data.lat.values, data.lon.values, indexing='ij')
    points = np.column_stack([lat.ravel(), lon.ravel()])
    tree = cKDTree(points)
    neighbours = [[j for j in group if j != i] for i, group in enumerate(tree.query_ball_point(points, radius_deg))]
    values = np.asarray(data.values).reshape(len(times), -1)
    result = np.zeros_like(values, dtype=bool)
    for t, stamp in enumerate(times):
        start = times.searchsorted(stamp - pd.Timedelta(hours=window_hours - 1))
        exceeded = (values[start:t + 1] > threshold).any(axis=0)
        for i, peers in enumerate(neighbours):
            result[t, i] = bool(values[t, i] > threshold and np.count_nonzero(exceeded[peers]) >= n_min)
    return result.reshape(data.shape)


def confirm_frame(frame: pd.DataFrame, scores: np.ndarray, cfg: dict) -> np.ndarray:
    """Align a sparse cell-hour table to a bounded grid and restore row order."""
    if frame.empty:
        return np.zeros(0, dtype=bool)
    if frame.time.nunique() * frame.lat.nunique() * frame.lon.nunique() > cfg['limits']['max_rows']:
        raise ValueError('Confirmation grid exceeds configured budget')
    source = frame[['time', 'lat', 'lon']].copy()
    source['risk'] = scores
    grid = source.set_index(['time', 'lat', 'lon']).risk.to_xarray()
    args = cfg['confirmation']
    values = confirm_neighbours(grid, **args)
    confirmed = xr.DataArray(values, dims=('time', 'lat', 'lon'), coords={k: grid.coords[k] for k in ('time', 'lat', 'lon')})
    lookup = confirmed.to_series()
    return lookup.reindex(pd.MultiIndex.from_frame(source[['time', 'lat', 'lon']])).to_numpy(bool)

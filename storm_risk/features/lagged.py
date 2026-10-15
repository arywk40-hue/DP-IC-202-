"""Positive hourly shifts, exact windows and explicit incomplete-history drops."""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_lagged(frame: pd.DataFrame, columns: list[str], cfg: dict) -> tuple[pd.DataFrame, list[str], dict]:
    """Reindex each cell to real hours; gaps cannot shorten a lag."""
    history = cfg['features']['history_hours']
    if frame.empty:
        raise ValueError('No hourly rows for causal features')
    if len(frame) * len(columns) * (history + 4) > cfg['limits']['max_feature_values']:
        raise ValueError('Feature matrix exceeds configured budget; partition dates/region')
    blocks, dropped = [], 0
    for (lat, lon), group in frame.groupby(['lat', 'lon'], sort=True):
        group = group.sort_values('time')
        index = pd.date_range(group.time.min(), group.time.max(), freq='h')
        if len(index) > cfg['limits']['max_rows']:
            raise ValueError('Cell span exceeds configured hourly reindex budget')
        hourly = group.set_index('time')[columns].reindex(index)
        values = {}
        for name in columns:
            series = hourly[name]
            values[name] = series
            for lag in range(1, history + 1):
                values[f'{name}_lag{lag}'] = series.shift(lag)
            values[f'{name}_change{history}'] = series - series.shift(history)
            values[f'{name}_rollmax{history}'] = series.rolling(history, min_periods=history).max()
            values[f'{name}_rollmin{history}'] = series.rolling(history, min_periods=history).min()
        block = pd.DataFrame(values).loc[pd.DatetimeIndex(group.time)]
        valid = np.isfinite(block.to_numpy()).all(axis=1)
        dropped += int((~valid).sum())
        block = block.loc[valid].rename_axis('time').reset_index()
        block['lat'], block['lon'] = lat, lon
        blocks.append(block)
    names = list(values)
    result = pd.concat(blocks, ignore_index=True).sort_values(['time', 'lat', 'lon']).reset_index(drop=True)
    return result, names, dict(input_rows=len(frame), complete_rows=len(result), dropped_incomplete_history=dropped, history_hours=history)

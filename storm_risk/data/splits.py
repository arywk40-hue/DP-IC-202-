"""Date-only partitions with target-boundary purging."""
from __future__ import annotations

import numpy as np
import pandas as pd

from storm_risk.settings import utc


def assign_split(times: pd.Series, cfg: dict) -> pd.Series:
    """Assign outcomes/issue times using predeclared UTC boundaries."""
    start, train, calib, end = [utc(cfg['time'][k]) for k in ('start', 'train_end', 'calib_end', 'end')]
    return pd.Series(np.select([times.ge(start) & times.lt(train), times.ge(train) & times.lt(calib),
        times.ge(calib) & times.lt(end)], ['train', 'calib', 'test'], default='outside'), index=times.index)


def inner_split(frame: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep all cells at a timestamp together, with no future target crossing."""
    times = sorted(frame.time.unique())
    cut = int(len(times) * (1 - cfg['features']['inner_validation_fraction']))
    if not 1 <= cut < len(times):
        raise ValueError('Insufficient distinct training hours for inner validation')
    boundary = times[cut]
    train = frame.loc[(frame.time < boundary) & (frame.target_time < boundary)]
    if 'available_at' in train:
        train = train.loc[train.available_at.le(boundary)]
    validation = frame.loc[frame.time >= boundary]
    if train.empty or validation.empty:
        raise ValueError('Empty purged inner partition')
    return train, validation

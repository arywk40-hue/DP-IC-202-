"""Derived meteorological context; no additional physical channels."""
from __future__ import annotations

import numpy as np
import pandas as pd


def derive(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Use current temperature/dew point and wind components only."""
    result = frame.copy()
    result['dewpoint_depression'] = result.t2m - result.d2m
    result['wind_speed'] = np.hypot(result.u10, result.v10)
    result['wind_direction_sin'] = np.divide(-result.u10, result.wind_speed, out=np.zeros(len(result)), where=result.wind_speed > 0)
    result['wind_direction_cos'] = np.divide(-result.v10, result.wind_speed, out=np.zeros(len(result)), where=result.wind_speed > 0)
    result.loc[result.wind_speed.isna(), ['wind_direction_sin', 'wind_direction_cos']] = np.nan
    return result, ['dewpoint_depression', 'wind_speed', 'wind_direction_sin', 'wind_direction_cos']

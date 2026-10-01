"""Causal hourly features shared by training and batch inference."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS

LAGS = (1, 3, 6, 12, 24)
WINDOWS = (6, 24)


def validate_observations(frame: pd.DataFrame) -> pd.DataFrame:
    columns = ["timestamp_utc", "location_id", *RAW_SENSOR_COLUMNS]
    if set(frame.columns) != set(columns):
        raise ValueError(f"Forecast observations must contain exactly {columns}")
    frame = frame.copy()
    frame["timestamp_utc"] = pd.to_datetime(
        frame.timestamp_utc, utc=True, errors="raise"
    )
    if frame.timestamp_utc.isna().any() or frame.location_id.isna().any():
        raise ValueError("Missing timestamp or location")
    frame["location_id"] = frame.location_id.astype(str)
    if frame.location_id.str.strip().eq("").any():
        raise ValueError("Empty location")
    if frame.duplicated(["location_id", "timestamp_utc"]).any():
        raise ValueError("Duplicate station-hour")
    offsets = frame.timestamp_utc - frame.timestamp_utc.dt.floor("h")
    if offsets.groupby(frame.location_id).nunique().gt(1).any():
        raise ValueError("Forecast pipeline requires a consistent hourly grid per station")
    for column, (low, high) in PHYSICAL_RANGES.items():
        frame[column] = pd.to_numeric(frame[column], errors="raise")
        frame[column] = frame[column].where(frame[column].between(low, high))
    return frame.sort_values(["location_id", "timestamp_utc"]).reset_index(drop=True)


def build_features(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = validate_observations(frame)
    results = []
    # Reindex each station to real hours: a missing row must not turn a 2-hour
    # lag into a 1-hour lag. Restore only original rows after feature building.
    for _, group in frame.groupby("location_id", sort=False):
        observed = pd.DatetimeIndex(group.timestamp_utc)
        hourly = group.set_index("timestamp_utc")[RAW_SENSOR_COLUMNS].reindex(
            pd.date_range(observed.min(), observed.max(), freq="h")
        )
        features = {}
        for column in RAW_SENSOR_COLUMNS:
            values = hourly[column]
            features[column] = values
            for lag in LAGS:
                features[f"{column}_lag_{lag}h"] = values.shift(lag)
            features[f"{column}_delta_1h"] = values.diff()
            for window in WINDOWS:
                rolling = values.rolling(window, min_periods=window)
                features[f"{column}_mean_{window}h"] = rolling.mean()
                features[f"{column}_std_{window}h"] = rolling.std(ddof=0)
        results.append(pd.DataFrame(features).loc[observed].reset_index(drop=True))
    if not results:
        raise ValueError("No observations")
    return frame, pd.concat(results, ignore_index=True).astype(np.float32)


def future_targets(frame: pd.DataFrame, horizon_hours: int) -> pd.DataFrame:
    if horizon_hours < 1:
        raise ValueError("horizon_hours must be positive")
    future = frame[["location_id", "timestamp_utc", *RAW_SENSOR_COLUMNS]].copy()
    future["timestamp_utc"] -= pd.Timedelta(hours=horizon_hours)
    # Exact keyed join prevents labels bridging missing timestamps or stations.
    joined = frame[["location_id", "timestamp_utc"]].merge(
        future, on=["location_id", "timestamp_utc"], how="left", validate="one_to_one"
    )
    return joined[RAW_SENSOR_COLUMNS].astype(np.float32)


def split_masks(
    frame: pd.DataFrame,
    horizon_hours: int,
    validation_start: str,
    test_start: str,
    holdout_locations: list[str],
) -> dict[str, np.ndarray]:
    validation = pd.Timestamp(validation_start)
    test = pd.Timestamp(test_start)
    if validation.tzinfo is None or test.tzinfo is None or validation >= test:
        raise ValueError("Use ordered timezone-aware validation/test cutoffs")
    locations = set(frame.location_id.unique())
    if not holdout_locations or not set(holdout_locations) < locations:
        raise ValueError(
            "Holdout stations must be a nonempty proper subset of locations"
        )
    t = frame.timestamp_utc
    label_time = t + pd.Timedelta(hours=horizon_hours)
    geographic = frame.location_id.isin(holdout_locations)
    masks = {
        "train": ~geographic & (label_time < validation),
        "validation": ~geographic & (t >= validation) & (label_time < test),
        "future_test": ~geographic & (t >= test),
        "geographic_test": geographic & (t >= test),
    }
    if any(not mask.any() for mask in masks.values()):
        raise ValueError("Empty split; check dates and locations")
    return {name: mask.to_numpy() for name, mask in masks.items()}

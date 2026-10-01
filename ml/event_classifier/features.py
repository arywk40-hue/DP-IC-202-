"""Causal hourly features and 12-class event labels for training and batch inference."""

from __future__ import annotations

import warnings
import numpy as np
import pandas as pd

from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS

EVENT_NAMES: list[str] = [
    "light_moderate_rain",
    "severe_rainstorm_squall",
    "snowstorm_blizzard",
    "freezing_rain_sleet",
    "radiation_fog",
    "ground_frost",
    "extreme_heatwave",
    "wildfire_evaporative_risk",
    "dust_storm_haboob",
    "smoke_plume",
    "smog_inversion_trap",
    "cold_frontal_passage",
]

# Which of the 6 raw channels each event rule actively uses
EVENT_ACTIVE_CHANNELS: dict[str, list[str]] = {
    "light_moderate_rain":       ["temperature_c", "relative_humidity_pct", "pressure_hpa", "pm25_ug_m3", "pm10_ug_m3"],
    "severe_rainstorm_squall":   ["temperature_c", "relative_humidity_pct", "pressure_hpa", "pm25_ug_m3", "pm10_ug_m3", "wind_speed_mps"],
    "snowstorm_blizzard":        ["temperature_c", "relative_humidity_pct", "pressure_hpa", "pm25_ug_m3", "pm10_ug_m3", "wind_speed_mps"],
    "freezing_rain_sleet":       ["temperature_c", "relative_humidity_pct", "pressure_hpa"],
    "radiation_fog":             ["temperature_c", "relative_humidity_pct", "pm25_ug_m3", "pm10_ug_m3", "wind_speed_mps"],
    "ground_frost":              ["temperature_c", "relative_humidity_pct", "pressure_hpa", "wind_speed_mps"],
    "extreme_heatwave":          ["temperature_c", "relative_humidity_pct"],
    "wildfire_evaporative_risk": ["temperature_c", "relative_humidity_pct", "wind_speed_mps"],
    "dust_storm_haboob":         ["relative_humidity_pct", "pm25_ug_m3", "pm10_ug_m3", "wind_speed_mps"],
    "smoke_plume":               ["temperature_c", "relative_humidity_pct", "pm25_ug_m3", "pm10_ug_m3", "wind_speed_mps"],
    "smog_inversion_trap":       ["temperature_c", "pressure_hpa", "pm25_ug_m3", "pm10_ug_m3", "wind_speed_mps"],
    "cold_frontal_passage":      ["temperature_c", "relative_humidity_pct", "pressure_hpa", "wind_speed_mps"],
}

RAW_FEATURE_COLS = list(RAW_SENSOR_COLUMNS)

DERIVED_FEATURE_COLS = [
    "T_dew",
    "VPD",
    "HI",
    "PM_ratio",
    "dP_dt",
    "dP_6h",
    "dT_dt",
    "dPM25_dt",
    "dPM10_dt",
    "dRH_dt",
    "pm25_mono_6h",
]

ALL_EVENT_FEATURE_COLS = RAW_FEATURE_COLS + DERIVED_FEATURE_COLS


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
        raise ValueError(
            "Forecast pipeline requires a consistent hourly grid per station"
        )
    for column, (low, high) in PHYSICAL_RANGES.items():
        frame[column] = pd.to_numeric(frame[column], errors="raise")
        frame[column] = frame[column].where(frame[column].between(low, high))
    return frame.sort_values(["location_id", "timestamp_utc"]).reset_index(drop=True)


def _magnus_dew_point(T: np.ndarray, RH: np.ndarray) -> np.ndarray:
    rh_frac = np.clip(RH / 100.0, 1e-6, 1.0)
    gamma = np.log(rh_frac) + (17.625 * T) / (243.04 + T)
    return 243.04 * gamma / (17.625 - gamma)


def _noaa_heat_index(T: np.ndarray, RH: np.ndarray) -> np.ndarray:
    Tf = T * 9.0 / 5.0 + 32.0
    HI = (
        -42.379
        + 2.04901523 * Tf
        + 10.14333127 * RH
        - 0.22475541 * Tf * RH
        - 6.83783e-3 * Tf**2
        - 5.481717e-2 * RH**2
        + 1.22874e-3 * Tf**2 * RH
        + 8.5282e-4 * Tf * RH**2
        - 1.99e-6 * Tf**2 * RH**2
    )
    calculated = (HI - 32.0) * 5.0 / 9.0
    return np.where(Tf >= 80.0, calculated, T)


def _vpd_kpa(T: np.ndarray, RH: np.ndarray) -> np.ndarray:
    es = 0.6108 * np.exp(17.27 * T / (T + 237.3))
    ea = es * RH / 100.0
    return np.maximum(0.0, es - ea)


def _safe_ratio(a: np.ndarray, b: np.ndarray, fill: float = np.nan) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.where(b > 0, a / b, fill)


def derive_event_features(frame: pd.DataFrame) -> pd.DataFrame:
    frame = validate_observations(frame)
    results = []

    for _, group in frame.groupby("location_id", sort=False):
        observed = pd.DatetimeIndex(group.timestamp_utc)
        hourly = group.set_index("timestamp_utc")[RAW_SENSOR_COLUMNS].reindex(
            pd.date_range(observed.min(), observed.max(), freq="h")
        )

        T = hourly["temperature_c"].to_numpy(dtype=np.float64)
        RH = hourly["relative_humidity_pct"].to_numpy(dtype=np.float64)
        P = hourly["pressure_hpa"].to_numpy(dtype=np.float64)
        PM25 = hourly["pm25_ug_m3"].to_numpy(dtype=np.float64)
        PM10 = hourly["pm10_ug_m3"].to_numpy(dtype=np.float64)

        hourly["T_dew"] = _magnus_dew_point(T, RH)
        hourly["VPD"] = _vpd_kpa(T, RH)
        hourly["HI"] = _noaa_heat_index(T, RH)
        hourly["PM_ratio"] = _safe_ratio(PM25, PM10)

        dP = np.concatenate([[np.nan], np.diff(P)])
        dT = np.concatenate([[np.nan], np.diff(T)])
        dRH = np.concatenate([[np.nan], np.diff(RH)])
        dPM25 = np.concatenate([[np.nan], np.diff(PM25)])
        dPM10 = np.concatenate([[np.nan], np.diff(PM10)])

        dP_6h_arr = np.full(len(P), np.nan)
        dP_6h_arr[6:] = P[6:] - P[:-6]

        pm25_mono = np.zeros(len(PM25), dtype=np.float32)
        for i in range(6, len(PM25)):
            window = PM25[i-6:i+1]
            if np.all(np.isfinite(window)) and np.all(np.diff(window) > 0):
                pm25_mono[i] = 1.0

        hourly["dP_dt"] = dP
        hourly["dP_6h"] = dP_6h_arr
        hourly["dT_dt"] = dT
        hourly["dPM25_dt"] = dPM25
        hourly["dPM10_dt"] = dPM10
        hourly["dRH_dt"] = dRH
        hourly["pm25_mono_6h"] = pm25_mono

        results.append(hourly.loc[observed].reset_index())

    if not results:
        raise ValueError("No observations")

    return pd.concat(results, ignore_index=True)


def build_features(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns the original frame (validated) and a dataframe with all features."""
    frame_validated = validate_observations(frame)
    features_df = derive_event_features(frame)
    return frame_validated, features_df


def apply_event_labels(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    T = df["temperature_c"].to_numpy(dtype=np.float64)
    RH = df["relative_humidity_pct"].to_numpy(dtype=np.float64)
    P = df["pressure_hpa"].to_numpy(dtype=np.float64)
    PM25 = df["pm25_ug_m3"].to_numpy(dtype=np.float64)
    PM10 = df["pm10_ug_m3"].to_numpy(dtype=np.float64)
    W = df["wind_speed_mps"].to_numpy(dtype=np.float64)
    Td = df["T_dew"].to_numpy(dtype=np.float64)
    VPD = df["VPD"].to_numpy(dtype=np.float64)
    HI = df["HI"].to_numpy(dtype=np.float64)
    PM_r = df["PM_ratio"].to_numpy(dtype=np.float64)
    dP = df["dP_dt"].to_numpy(dtype=np.float64)
    dP6 = df["dP_6h"].to_numpy(dtype=np.float64)
    dT = df["dT_dt"].to_numpy(dtype=np.float64)
    dPM25 = df["dPM25_dt"].to_numpy(dtype=np.float64)
    dPM10 = df["dPM10_dt"].to_numpy(dtype=np.float64)
    dRH = df["dRH_dt"].to_numpy(dtype=np.float64)
    mono = df["pm25_mono_6h"].to_numpy(dtype=np.float64)

    complete = np.isfinite(df[ALL_EVENT_FEATURE_COLS].to_numpy(dtype=np.float64)).all(axis=1)

    def _f(cond: np.ndarray) -> np.ndarray:
        return np.where(complete, cond.astype(np.float32), np.nan)

    ev0 = (RH >= 85) & (dP6 <= -1.5) & (T > 3) & (dPM25 <= 0) & (dPM10 <= 0)
    df["light_moderate_rain"] = _f(ev0)

    ev1 = (dP6 <= -3.5) & (dT <= -3) & (T > 3) & (W >= 10) & (dPM25 <= 0) & (dPM10 <= 0)
    df["severe_rainstorm_squall"] = _f(ev1)

    ev2 = (dP6 <= -3.0) & (T <= 1) & (RH >= 85) & (W >= 9) & (dPM25 <= 0) & (dPM10 <= 0)
    df["snowstorm_blizzard"] = _f(ev2)

    ev3 = (dP < 0) & (RH >= 90) & (T >= -2) & (T <= 0.5)
    df["freezing_rain_sleet"] = _f(ev3)

    ev4 = ((T - Td) <= 2) & (RH >= 95) & (W < 1.5) & (PM25 > 80)
    df["radiation_fog"] = _f(ev4)

    ev5 = (T <= 0) & (Td <= 0) & (W < 2) & (dP >= 0)
    df["ground_frost"] = _f(ev5)

    ev6 = (T >= 35) | (HI >= 41)
    df["extreme_heatwave"] = _f(ev6)

    ev7 = (VPD >= 2.5) & (RH <= 25) & (W >= 5)
    df["wildfire_evaporative_risk"] = _f(ev7)

    ev8 = (W >= 8) & (PM_r <= 0.35) & (PM10 > 250) & (RH < 40)
    df["dust_storm_haboob"] = _f(ev8)

    ev9 = (PM25 > 150) & (PM_r >= 0.70) & (RH < 60) & (W > 1.5)
    df["smoke_plume"] = _f(ev9)

    ev10 = (W < 1.0) & (P >= 1010) & (PM25 > 120) & (mono == 1)
    df["smog_inversion_trap"] = _f(ev10)

    ev11 = (dT <= -4) & (dP >= 1.5) & (W >= 6) & (np.abs(dRH) >= 5)
    df["cold_frontal_passage"] = _f(ev11)

    return df


def split_masks(
    frame: pd.DataFrame,
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
    geographic = frame.location_id.isin(holdout_locations)
    masks = {
        "train": ~geographic & (t < validation),
        "validation": ~geographic & (t >= validation) & (t < test),
        "future_test": ~geographic & (t >= test),
        "geographic_test": geographic & (t >= test),
    }
    if any(not mask.any() for mask in masks.values()):
        raise ValueError("Empty split; check dates and locations")
    return {name: mask.to_numpy() for name, mask in masks.items()}

"""Causal native-cadence features; no satellite/reanalysis or hidden labels.

Hourly lags/statistics and meteorological equations reuse the existing packages.
Unsupported sub-hour tendencies remain missing, never interpolated from hours.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.event_classifier.features import _magnus_dew_point, _noaa_heat_index, _vpd_kpa, _safe_ratio
from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.features import MAX_HOURLY_ROWS, build_features as hourly_features

METADATA = ['timestamp_utc', 'available_at_utc', 'location_id', 'physical_site_id',
            'source_id', 'country_code', 'latitude', 'longitude', 'elevation_m',
            'elevation_datum', 'pressure_reference', 'climate_zone', 'interval_seconds']
GEO_FEATURES = ['latitude', 'longitude', 'elevation_m']


def utc(values):
    stamps = [pd.Timestamp(v) for v in values]
    if any(pd.isna(v) or v.tzinfo is None or v.utcoffset().total_seconds() != 0 for v in stamps):
        raise ValueError('Explicit UTC timestamps required')
    return pd.to_datetime(stamps, utc=True)


def build(frame, config):
    required = set(METADATA) | set(RAW_SENSOR_COLUMNS)
    if set(frame.columns) != required:
        raise ValueError(f'Sensor view has unexpected/missing columns: {set(frame.columns)^required}')
    if not len(frame):
        raise ValueError('Empty sensor observations')
    if len(frame) > MAX_HOURLY_ROWS:
        raise ValueError('Sensor observation resource budget exceeded')
    out = frame.copy()
    if not out.country_code.eq('IN').all() or not out.source_id.isin(config['allowed_sources']).all():
        raise ValueError('Non-Indian or unapproved source; China/external references are isolated')
    for name in ['location_id', 'physical_site_id', 'source_id']:
        if out[name].isna().any() or out[name].astype(str).str.strip().eq('').any():
            raise ValueError('Missing identity/provenance')
    out.timestamp_utc = utc(out.timestamp_utc)
    out.available_at_utc = utc(out.available_at_utc)
    if (out.available_at_utc < out.timestamp_utc).any():
        raise ValueError('Available before the completed observation window')
    if out.duplicated(['physical_site_id', 'timestamp_utc']).any():
        raise ValueError('Duplicate physical-site timestamp/alias')
    cadence = config['cadence_seconds']
    if not isinstance(cadence, int) or cadence < 1 or not out.interval_seconds.eq(cadence).all():
        raise ValueError('Declared native cadence mismatch')
    for name, bounds in [('latitude', (-90, 90)), ('longitude', (-180, 180))]:
        out[name] = pd.to_numeric(out[name], errors='raise')
        if not out[name].between(*bounds).all():
            raise ValueError('Invalid coordinates')
    out.elevation_m = pd.to_numeric(out.elevation_m, errors='raise')
    out.elevation_m = out.elevation_m.where(out.elevation_datum.eq('EGM96') & out.elevation_m.between(-500, 9000))
    for name, bounds in PHYSICAL_RANGES.items():
        out[name] = pd.to_numeric(out[name], errors='raise').where(lambda v: v.between(*bounds))
    out.pressure_hpa = out.pressure_hpa.where(out.pressure_reference.eq('station'))
    results = []
    for _, group in out.groupby('physical_site_id', sort=False):
        if group.location_id.nunique() != 1 or group.source_id.nunique() != 1:
            raise ValueError('Resolve physical-site aliases/providers before feature building')
        if group[['latitude', 'longitude', 'elevation_m']].nunique(dropna=True).gt(1).any():
            raise ValueError('Use fixed surveyed site coordinates/height; relocation needs a new physical site')
        group = group.sort_values('timestamp_utc')
        observed = pd.DatetimeIndex(group.timestamp_utc)
        span = (observed[-1] - observed[0]).total_seconds()
        if span / cadence + 1 > config['max_expanded_station_rows']:
            raise ValueError('Native-cadence expansion budget exceeded')
        ticks = (observed - observed[0]).total_seconds() / cadence
        if not np.equal(ticks, np.floor(ticks)).all():
            raise ValueError('Off-grid native-cadence timestamps')
        grid = pd.date_range(observed[0], observed[-1], freq=pd.Timedelta(seconds=cadence))
        native = group.set_index('timestamp_utc')[RAW_SENSOR_COLUMNS].reindex(grid)
        # Causal history may use a previous row only once actually available.
        availability = group.set_index('timestamp_utc').available_at_utc.reindex(grid)
        if (group.available_at_utc != group.timestamp_utc).any():
            # Exact aligned research windows only; don't backdate delayed packets.
            native.loc[availability > native.index] = np.nan
        values = {c: native[c] for c in RAW_SENSOR_COLUMNS}
        if cadence == 3600:
            legacy = group[['timestamp_utc', 'location_id', *RAW_SENSOR_COLUMNS]].copy()
            # Apply reference, range and availability masks before every reused lag.
            legacy[RAW_SENSOR_COLUMNS] = native.loc[observed].to_numpy()
            _, reused = hourly_features(legacy)
            for c in reused:
                values[c] = pd.Series(reused[c].to_numpy(), index=observed).reindex(grid)
        for minutes in config['windows_minutes']:
            seconds = minutes * 60
            supported = seconds >= cadence and seconds % cadence == 0
            steps = seconds // cadence if supported else 0
            for name in RAW_SENSOR_COLUMNS:
                v = native[name]
                contiguous = v.rolling(steps + 1, min_periods=steps + 1).count().eq(steps + 1) if supported else False
                values[f'{name}_delta_{minutes}min'] = (v - v.shift(steps)).where(contiguous) if supported else v * np.nan
                if supported and steps > 1:
                    roll = v.rolling(steps, min_periods=steps)
                    for metric in ['mean', 'std', 'min', 'max']:
                        values[f'{name}_{metric}_{minutes}min'] = (roll.std(ddof=0) if metric == 'std' else getattr(roll, metric)())
        # No rate from a stale/gapped endpoint; rates are per minute.
        for minutes in [10, 30, 60]:
            values[f'pressure_tendency_hpa_per_min_{minutes}min'] = values[f'pressure_hpa_delta_{minutes}min'] / minutes
        t, rh = native.temperature_c.to_numpy(), native.relative_humidity_pct.to_numpy()
        dew = np.where(rh > 0, _magnus_dew_point(t, rh), np.nan)
        values.update(dewpoint_c=dew, dewpoint_depression_c=t-dew,
                      vapor_pressure_deficit_kpa=_vpd_kpa(t, rh), heat_index_c=_noaa_heat_index(t, rh),
                      pm25_pm10_ratio=_safe_ratio(native.pm25_ug_m3.to_numpy(), native.pm10_ug_m3.to_numpy()))
        vapor_hpa = 6.112 * np.exp(17.625*t/(243.04+t)) * rh / 100
        values['absolute_humidity_estimate_g_m3'] = 216.7*vapor_hpa/(t+273.15)
        baseline_steps = 24*3600 // cadence
        values['pressure_anomaly_prior24h_hpa'] = native.pressure_hpa - native.pressure_hpa.shift(1).rolling(baseline_steps, min_periods=baseline_steps).mean()
        # Atmospheric variability is not an observed instantaneous gust.
        values['wind_variability_60min_mps'] = native.wind_speed_mps.rolling(max(2, 3600//cadence), min_periods=max(2, 3600//cadence)).std(ddof=0) if cadence < 3600 else native.wind_speed_mps*np.nan
        hour = grid.hour + grid.minute/60
        month = grid.month
        values.update(hour_sin=np.sin(2*np.pi*hour/24), hour_cos=np.cos(2*np.pi*hour/24),
                      month_sin=np.sin(2*np.pi*(month-1)/12), month_cos=np.cos(2*np.pi*(month-1)/12),
                      calendar_jjas_proxy=np.isin(month, [6, 7, 8, 9]).astype(float))
        f = pd.DataFrame(values, index=grid).loc[observed].replace([np.inf, -np.inf], np.nan).astype('float32')
        f = f.reset_index(drop=True)
        meta = group[METADATA].reset_index(drop=True)
        # Geographic features belong to their own declared runtime view.
        result = pd.concat([meta, f], axis=1)
        if result.columns.duplicated().any():
            raise ValueError('Duplicate feature names')
        results.append(result)
    return pd.concat(results, ignore_index=True)


def feature_columns(frame, geographical=False):
    # Reuse the old hourly names once: don't train on duplicate aliases.
    aliases = {f'{name}_delta_60min' for name in RAW_SENSOR_COLUMNS}
    aliases |= {f'{name}_{metric}_{minutes}min' for name in RAW_SENSOR_COLUMNS
                for metric in ['mean', 'std'] for minutes in [360, 1440]}
    hourly = 'temperature_c_lag_1h' in frame
    return [c for c in frame if c not in METADATA and (not hourly or c not in aliases)] + (GEO_FEATURES if geographical else [])

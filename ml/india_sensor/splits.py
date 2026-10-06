"""Whole-site buffered holdouts plus chronological history/target purging."""
import numpy as np
import pandas as pd

from ml.spatial_ensemble.national import region, splits
from ml.spatial_ensemble.episodes import episode_ids


def station_roles(stations, scope, cfg):
    if stations.physical_site_id.duplicated().any():
        raise ValueError('Resolve site aliases before splitting')
    if scope == 'temporal':
        return {r: sorted(stations.location_id) for r in ['train', 'validation', 'test']}
    if scope == 'himalaya_only':
        stations = stations[region(stations)].copy()
    if scope == 'himalaya_holdout':
        held = stations.loc[region(stations), 'location_id']
    elif scope in ['national', 'himalaya_only']:
        ids = np.random.default_rng(cfg['seed']).permutation(stations.location_id.to_numpy())
        held = ids[:max(3, len(ids)//5)]
    else:
        raise ValueError('Unknown geographic scope')
    train, validation, test = splits(stations, held, cfg['seed'], cfg['buffer_km'])
    if scope == 'himalaya_holdout':
        # Unknown heights inside the belt rectangle cannot quietly become
        # non-mountain fit/calibration sites in a geographic mountain holdout.
        uncertain = stations.latitude.between(28, 37) & stations.longitude.between(72, 90) & stations.elevation_m.isna()
        train -= set(stations.loc[uncertain, 'location_id'])
        validation -= set(stations.loc[uncertain, 'location_id'])
    return {'train': sorted(train), 'validation': sorted(validation), 'test': sorted(test)}


def row_roles(frame, roles, cfg):
    """Validation stations serve July/August selection and Sep/Oct calibration.

    Their history/targets do not overlap across those chronological roles.
    Training/test stations are wholly different; no random row split.
    """
    t = frame.timestamp_utc
    history = pd.Timedelta(minutes=cfg['history_minutes'])
    lead = pd.Timedelta(hours=cfg['forecast_hours'])
    v, c, test, end = [pd.Timestamp(cfg[k]) for k in ['validation_start', 'calibration_start', 'test_start', 'test_end']]
    # Predeclared global blocks reuse the existing episode utility. A boundary
    # block is dropped, not split between selection/calibration/test roles.
    # These are time proxies, not adjudicated storm identities.
    episode_start = pd.Timestamp('2024-01-01T00:00:00Z') + pd.to_timedelta(episode_ids(t)*72, unit='h')
    episode_end = episode_start + pd.Timedelta(hours=72)
    return {
        'train': frame.location_id.isin(roles['train']) & (t + lead < v) & (episode_end <= v),
        'validation': frame.location_id.isin(roles['validation']) & (t - history >= v) & (t + lead < c) & (episode_start >= v) & (episode_end <= c),
        'calibration': frame.location_id.isin(roles['validation']) & (t - history >= c) & (t + lead < test) & (episode_start >= c) & (episode_end <= test),
        'test': frame.location_id.isin(roles['test']) & (t - history >= test) & (t + lead < end) & (episode_start >= test) & (episode_end <= end),
    }

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from ml.storm_risk.data.era5_loader import load_era5
from ml.storm_risk.data.labels import read_events, read_labels
from ml.storm_risk.pipeline import merge_outcomes


def test_labels_require_records_and_monitored_zeros(config, tmp_path):
    records = pd.read_csv(config['paths']['events'])
    positive = records.index[records.type.eq(config['target']['name'])][0]
    records.loc[positive, 'source_2'] = ''
    records = records.iloc[:-1]
    path = tmp_path / 'events.csv'
    records.to_csv(path, index=False)
    events, excluded = read_events(path, config)
    assert len(excluded) == 1 and 'MISSING_SOURCE_2' in excluded.iloc[0].exclusion_reasons
    admitted, rejected, receipt = read_labels(Path(config['paths']['labels']), events, config)
    assert len(rejected) == 2 and receipt['excluded_rows'] == 2
    assert len(admitted) + len(rejected) == len(pd.read_csv(config['paths']['labels']))
    labels = pd.read_csv(config['paths']['labels'])
    labels.loc[0, 'split'] = 'test'
    bad = tmp_path / 'bad_labels.csv'
    labels.to_csv(bad, index=False)
    with pytest.raises(ValueError, match='split'):
        read_labels(bad, events, config)


def test_era5_mapping_units_and_missing_variable(config, tmp_path):
    path = Path(config['paths']['era5_glob'])
    frame, receipt = load_era5([path], config)
    with xr.open_dataset(path) as ds:
        expected = float(ds.t2m.isel(time=0, latitude=0, longitude=0)) - 273.15
        expected_rain = float(ds.tp.isel(time=0, latitude=0, longitude=0)) * 1000
        assert np.isclose(frame.t2m.iloc[0], expected) and np.isclose(frame.tp.iloc[0], expected_rain)
        missing = tmp_path / 'missing.nc'
        ds.drop_vars('cape').to_netcdf(missing)
    assert receipt['files'][0]['actual_names']['t2m'] == 't2m'
    with pytest.raises(ValueError, match='required variable cape'):
        load_era5([missing], config)


def test_cross_split_event_and_target_boundary_are_excluded(config):
    cut = pd.Timestamp(config['time']['train_end'])
    times = pd.Series([cut - pd.Timedelta(hours=1), cut, cut + pd.Timedelta(hours=1)])
    frame = pd.DataFrame(dict(time=times, lat=31.5, lon=76.75, f=1.))
    labels = frame.rename(columns={'time': 'target_time'}).drop(columns='f').copy()
    labels = labels.rename(columns={'target_time': 'time'})
    labels['label'], labels['event_id'] = 1, 'one_shared_event'
    labels['split'] = ['train', 'calib', 'calib']
    labels['available_at'] = labels.time + pd.Timedelta(hours=24)
    merged, receipt = merge_outcomes(frame, labels, config)
    assert merged.label.isna().all()
    assert receipt['cross_split_event_ids_excluded'] == ['one_shared_event']
    config['target']['lead_hours'] = 1
    merged, receipt = merge_outcomes(frame, labels, config)
    assert receipt['purged_split_boundary_rows'] == 1
    assert not merged.time.eq(times.iloc[0]).any()


def test_event_coordinates_map_to_grid_with_explicit_radius(config, tmp_path):
    events, _ = read_events(Path(config['paths']['events']), config)
    raw = pd.read_csv(config['paths']['labels'])
    grid = raw[['lat', 'lon']].drop_duplicates()
    raw['lat'] += .01
    path = tmp_path / 'off_grid.csv'
    raw.to_csv(path, index=False)
    labels, rejected, receipt = read_labels(path, events, config, grid=grid)
    assert rejected.empty and len(labels) == len(raw)
    assert set(labels.lat) == set(grid.lat)
    assert receipt['grid_alignment'].startswith('NEAREST_CONFIGURED_CELL')
    raw['lat'] += 2
    raw.to_csv(path, index=False)
    labels, rejected, _ = read_labels(path, events, config, grid=grid)
    assert labels.empty and len(rejected) == len(raw)

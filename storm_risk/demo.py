"""ERA5-shaped engineering inputs with independent random synthetic outcomes."""
from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from storm_risk.data.splits import assign_split
from storm_risk.io.outputs import write_json


def create_fixture(cfg: dict, directory: Path) -> dict:
    """Create small local files; never represent them as observed weather/events."""
    directory.mkdir(parents=True, exist_ok=False)
    settings = copy.deepcopy(cfg)
    fixture, rng = cfg['fixture'], np.random.default_rng(cfg['models']['seed'])
    start = pd.Timestamp(fixture['start'])
    times = pd.date_range(start, periods=fixture['days'] * 24, freq='h')
    train_end = start + pd.Timedelta(days=int(fixture['days'] * fixture['train_fraction']))
    calib_end = train_end + pd.Timedelta(days=int(fixture['days'] * fixture['calib_fraction']))
    settings['time'].update(start=start.isoformat(), train_end=train_end.isoformat(), calib_end=calib_end.isoformat(), end=(start + pd.Timedelta(days=fixture['days'])).isoformat())
    settings['years'] = sorted(set(times.year.tolist()))
    settings['evidence_kind'] = 'synthetic_engineering'
    shape = (len(times), len(fixture['latitudes']), len(fixture['longitudes']))
    base = dict(t2m=285 + rng.normal(0, 3, shape), d2m=280 + rng.normal(0, 2, shape), sp=85000 + rng.normal(0, 100, shape),
        u10=rng.normal(0, 3, shape), v10=rng.normal(0, 3, shape), fg10=rng.uniform(0, 15, shape))
    arrays = {name: (('time', 'latitude', 'longitude'), base.get(name, rng.random(shape)), {'units': spec['units'][0]}) for name, spec in settings['variables'].items()}
    nc = directory / 'synthetic_era5.nc'
    xr.Dataset(arrays, coords=dict(time=times.tz_localize(None), latitude=fixture['latitudes'], longitude=fixture['longitudes']),
        attrs=dict(evidence_kind='SYNTHETIC_ENGINEERING_ONLY')).to_netcdf(nc)
    labels, events = [], []
    for lat in fixture['latitudes']:
        for lon in fixture['longitudes']:
            outcomes = rng.binomial(1, fixture['event_rate'], len(times))
            roles = assign_split(pd.Series(times), settings)
            for index, (time, outcome, role) in enumerate(zip(times, outcomes, roles)):
                identity = f'synthetic-{lat}-{lon}-{index}'
                labels.append(dict(time=time.isoformat(), lat=lat, lon=lon, label=int(outcome), split=role,
                    available_at=(time + pd.Timedelta(hours=settings['time']['label_delay_hours'])).isoformat()))
                events.append(dict(event_id=identity, type=settings['target']['name'] if outcome else settings['labels']['negative_record_type'],
                    date_start=time.isoformat(), date_end=time.isoformat(), district='SYNTHETIC_NOT_OBSERVED', lat=lat, lon=lon,
                    magnitude=settings['target']['minimum_magnitude'] if outcome else 0, magnitude_unit=settings['target']['magnitude_unit'],
                    source_1='synthetic://fixture-a/' + identity, source_2='synthetic://fixture-b/' + identity,
                    confidence='confirmed', notes='ENGINEERING_ONLY_RANDOM_OUTCOME_NOT_REAL_EVENT', time_known=True))
    label_path, event_path = directory / 'synthetic_labels.csv', directory / 'synthetic_events.csv'
    pd.DataFrame(labels).to_csv(label_path, index=False)
    pd.DataFrame(events).to_csv(event_path, index=False)
    settings['paths'].update(era5_glob=str(nc.resolve()), labels=str(label_path.resolve()), events=str(event_path.resolve()))
    write_json(directory / 'fixture_config.json', {k: v for k, v in settings.items() if not k.startswith('_')})
    return settings

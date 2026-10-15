"""Read bounded UTC ERA5 exports; no labels are inferred from weather."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from storm_risk.settings import digest, utc


def load_era5(paths: list[Path], cfg: dict) -> tuple[pd.DataFrame, dict]:
    """Inspect actual names/units before loading a configured rectilinear subset."""
    frames, receipts = [], []
    region, limits = cfg['region'], cfg['limits']
    if not paths:
        raise ValueError('No local ERA5 files match the configured input glob')
    for path in paths:
        if path.stat().st_size > limits['max_file_bytes']:
            raise ValueError('ERA5 file exceeds configured byte budget')
        with xr.open_dataset(path, decode_times=True, mask_and_scale=True) as original:
            marker = str(original.attrs.get('evidence_kind', original.attrs.get('evidence', ''))).upper()
            if 'SYNTHETIC' in marker and cfg['evidence_kind'] != 'synthetic_engineering':
                raise ValueError('Synthetic NetCDF requires synthetic engineering evidence mode')
            ds = original
            rename = {}
            for key, aliases in {'time': ['time', 'valid_time'], 'lat': ['lat', 'latitude'], 'lon': ['lon', 'longitude']}.items():
                names = [n for n in aliases if n in ds.dims]
                if len(names) != 1:
                    raise ValueError('Unambiguous time/latitude/longitude dimensions required')
                rename[names[0]] = key
            ds = ds.rename(rename)
            for dim in list(ds.dims):
                if dim not in {'time', 'lat', 'lon'}:
                    if ds.sizes[dim] != 1:
                        raise ValueError('Select one ERA5 member/version/step before import')
                    ds = ds.isel({dim: 0}, drop=True)
            ds = ds.assign_coords(lon=((ds.lon + 180) % 360) - 180).sortby('lon').sortby('lat').sortby('time')
            for name in ('lat', 'lon', 'time'):
                if not pd.Index(ds[name].values).is_unique:
                    raise ValueError('Duplicate ERA5 coordinate: ' + name)
            times = pd.DatetimeIndex(ds.time.values)
            if times.hasnans or not (times == times.floor('h')).all():
                raise ValueError('Exact CF-decoded UTC hourly times required')
            selected = (times >= utc(cfg['time']['start']).tz_localize(None)) & (times < utc(cfg['time']['end']).tz_localize(None)) & times.year.isin(cfg['years'])
            ds = ds.isel(time=np.flatnonzero(selected)).sel(lat=slice(region['south'], region['north']), lon=slice(region['west'], region['east']))
            if not ds.sizes['time'] or not ds.sizes['lat'] or not ds.sizes['lon']:
                continue
            for coordinate in ('lat', 'lon'):
                steps = np.diff(ds[coordinate].values) / region['grid_degrees']
                if not np.allclose(steps, np.round(steps)):
                    raise ValueError('ERA5 coordinates differ from the configured grid spacing')
            n = ds.sizes['time'] * ds.sizes['lat'] * ds.sizes['lon']
            if n + sum(len(f) for f in frames) > limits['max_rows'] or ds.sizes['lat'] * ds.sizes['lon'] > limits['max_grid_cells']:
                raise ValueError('ERA5 subset exceeds resource budget; partition dates/region in config')
            names = {}
            for canonical, spec in cfg['variables'].items():
                found = [name for name in spec['aliases'] if name in ds.data_vars]
                if len(found) != 1:
                    raise ValueError(f'ERA5 required variable {canonical}: found {found}; available={list(ds.data_vars)}')
                name = found[0]
                if set(ds[name].dims) != {'time', 'lat', 'lon'} or ds[name].attrs.get('units') not in spec['units']:
                    raise ValueError('Unverified ERA5 dimensions/units: ' + name)
                names[name] = canonical
            selected_ds = ds[list(names)].rename(names)
            frame = selected_ds.to_dataframe().reset_index()[['time', 'lat', 'lon', *cfg['variables']]]
            frame['time'] = pd.to_datetime(frame.time, utc=True)
            for name, spec in cfg['variables'].items():
                frame[name] = frame[name].astype(float) * spec['scale'] + spec['offset']
            frame = frame.replace([np.inf, -np.inf], np.nan)
            frames.append(frame)
            receipts.append(dict(path=str(path), sha256=digest(path), actual_names=names, rows=len(frame)))
    if not frames:
        raise ValueError('No ERA5 rows within configured dates/region/years')
    result = pd.concat(frames, ignore_index=True).sort_values(['time', 'lat', 'lon']).reset_index(drop=True)
    if result.duplicated(['time', 'lat', 'lon']).any():
        raise ValueError('Overlapping ERA5 exports contain duplicate cell-hours')
    return result, dict(files=receipts, rows=len(result), time_basis='UTC', input_kind='RETROSPECTIVE_GRID_CONTEXT',
        availability=cfg['time']['availability_note'], precipitation_semantics=cfg['precipitation_semantics'],
        physical_sensor_channels_added=0)

"""Per-time feature arrays and latest per-feature scientific PNGs."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ml.storm_risk.settings import digest


def export_heatmaps(frame: pd.DataFrame, features: list[str], directory: Path, cfg: dict) -> dict:
    """Export configured UTC map frames without interpolation or extrapolation."""
    directory.mkdir(parents=True, exist_ok=True)
    selected = features if cfg['heatmaps']['features'] == 'all' else cfg['heatmaps']['features']
    if not set(selected) <= set(features):
        raise ValueError('Unknown feature map selection')
    times = sorted(frame.time.unique())
    times = times[::cfg['heatmaps']['time_stride_hours']]
    if len(times) > cfg['heatmaps']['max_frames']:
        raise ValueError('Feature map frame budget exceeded; adjust dates/stride in config')
    lat, lon = np.sort(frame.lat.unique()), np.sort(frame.lon.unique())
    grid_index = pd.MultiIndex.from_product([lat, lon], names=['lat', 'lon'])
    frames, last_arrays = [], None
    for time in times:
        group = frame.loc[frame.time.eq(time)].set_index(['lat', 'lon'])
        arrays = {name: group[name].reindex(grid_index).to_numpy(float).reshape(len(lat), len(lon)) for name in selected}
        stamp = pd.Timestamp(time)
        filename = stamp.strftime('%Y%m%dT%H%M%SZ') + '.npz'
        np.savez_compressed(directory / filename, lat=lat, lon=lon, **arrays)
        frames.append(dict(time=stamp.isoformat(), file=filename, sha256=digest(directory / filename)))
        last_arrays = arrays
    if frames:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        for name, values in last_arrays.items():
            fig, ax = plt.subplots(figsize=(5, 4), layout='constrained')
            image = ax.pcolormesh(lon, lat, values, shading='nearest', cmap=cfg['heatmaps']['cmap'])
            unit = cfg['variables'].get(name, {}).get('output_unit', 'derived')
            fig.colorbar(image, ax=ax, label=unit)
            ax.set(xlabel='Longitude', ylabel='Latitude', title=f'{name}\n{frames[-1]["time"]}')
            fig.savefig(directory / (name + '.png'), dpi=120)
            plt.close(fig)
    derived_units = dict(dewpoint_depression='K', wind_speed='m/s', wind_direction_sin='1', wind_direction_cos='1')
    units = {name: cfg['variables'][name]['output_unit'] if name in cfg['variables'] else derived_units[name] for name in selected}
    return dict(features=selected, units=units, frames=frames, png_scope='LATEST_EXPORTED_TIMESTAMP_PER_FEATURE',
        evidence=cfg['evidence_kind'], method='ORIGINAL_ERA5_GRID_NO_INTERPOLATION',
        time_stride_hours=cfg['heatmaps']['time_stride_hours'], unsupported_cells='NaN')

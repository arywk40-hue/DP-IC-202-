"""Adapt the existing QC'd Indian hourly archive, retaining raw-file lineage."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ml.datasets.registry import digest
from ml.india_sensor.config import DEFAULT, load
from ml.india_sensor.features import METADATA, build
from ml.india_sensor.labels import measured_future
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS


def admitted_sources(cfg):
    registry = json.loads(Path(cfg['source_registry']).read_text())
    sources = {s['source_id']: s for s in registry['sources']}
    for name in cfg['allowed_sources']:
        s = sources[name]
        if s['license_class'] != 'open' or not s['timezone_verified'] or s['timezone'] != 'UTC':
            raise ValueError('Clean sensor view requires approved open UTC sources')
        if s['pressure_reference'] != 'station' or not s['pressure_verified']:
            raise ValueError('Station-pressure reference must be verified')
    return {name: sources[name] for name in cfg['allowed_sources']}


def normalize(hours, stations, qc, cfg):
    if hours.empty or not hours.source_id.isin(cfg['allowed_sources']).all():
        raise ValueError('Unapproved/empty hourly source, external references cannot be mixed')
    if hours.duplicated(['location_id', 'timestamp_utc']).any():
        raise ValueError('Duplicate archive station-hour')
    eligible = stations[stations.source.isin(cfg['allowed_sources']) &
                        stations.geography_status.ne('COUNTRY_LOCATION_CONFLICT') &
                        stations.location_id.isin(hours.location_id)].copy()
    # Highest observed coverage wins exact aliases, independent of outcomes.
    counts = hours.groupby('location_id').size()
    eligible['rows'] = eligible.location_id.map(counts)
    eligible = eligible.sort_values(['rows', 'location_id'], ascending=[False, True]).drop_duplicates('physical_site_id')
    eligible = eligible.merge(qc[['location_id', 'elevation_ok', 'pressure_ok']], on='location_id', validate='one_to_one')
    for key in ['elevation_ok', 'pressure_ok']:
        if not eligible[key].isin([True, False]).all():
            raise ValueError('QC booleans required; unresolved metadata is not approved')
    eligible.elevation_m = eligible.elevation_m.where(eligible.elevation_ok)
    metadata = ['location_id', 'physical_site_id', 'latitude', 'longitude', 'elevation_m',
                'elevation_datum', 'climate_zone', 'pressure_ok']
    frame = hours[['location_id', 'timestamp_utc', 'source_id', *RAW_SENSOR_COLUMNS]].merge(
        eligible[metadata], on='location_id', validate='many_to_one')
    frame['country_code'] = 'IN'  # NOAA ISO-IN candidates; not a verified border polygon.
    frame['available_at_utc'] = frame.timestamp_utc
    frame['pressure_reference'] = np.where(frame.pressure_ok, 'station', 'unresolved')
    frame['interval_seconds'] = cfg['cadence_seconds']
    frame.pressure_hpa = frame.pressure_hpa.where(frame.pressure_ok)
    return frame[[*METADATA, *RAW_SENSOR_COLUMNS]], eligible.drop(columns=['rows'])


def run(cfg, config_path):
    sources = admitted_sources(cfg)
    hours = pd.read_parquet(cfg['hours'])
    stations = pd.read_csv(cfg['stations'])
    qc = pd.read_csv(cfg['station_qc'])
    frame, stations = normalize(hours, stations, qc, cfg)
    for folder in ['processed', 'features', 'reports']:
        Path(cfg[folder]).mkdir(parents=True, exist_ok=True)
    # No stale extra stations after a changed whitelist/configuration.
    if list(Path(cfg['features']).glob('*.parquet')):
        raise ValueError('Feature directory already populated; use a fresh configured output directory')
    stations.to_csv(Path(cfg['processed']) / 'stations.csv', index=False)
    manifests = []
    for i, (site, group) in enumerate(frame.groupby('physical_site_id', sort=True)):
        group = group.sort_values('timestamp_utc').reset_index(drop=True)
        features = build(group, cfg)
        # Physical range cleaning is shared by labels and features. Future labels
        # must not admit a value that features would reject.
        clean = features[[*METADATA, *RAW_SENSOR_COLUMNS]]
        labels = measured_future(clean, cfg)
        path = Path(cfg['features']) / f'{i:04d}.parquet'
        features.to_parquet(path, index=False)
        clean.to_parquet(Path(cfg['processed']) / f'{i:04d}.parquet', index=False)
        label_path = Path(cfg['processed']) / f'{i:04d}.labels.parquet'
        labels.to_parquet(label_path, index=False)
        manifests.append({'physical_site_id': site, 'location_id': str(group.location_id.iloc[0]),
                          'rows': len(group), 'features': str(path), 'feature_sha256': digest(path),
                          'labels': str(label_path), 'label_sha256': digest(label_path),
                          'target_counts': {t: {'observed': int(labels[t].notna().sum()),
                                                'positive': int(labels[t].eq(1).sum())}
                                            for t in cfg['threshold_targets']}})
        if i % 25 == 0:
            print(f'Prepared {i+1}/{len(stations)} Indian stations', flush=True)
    lineage = Path(cfg['hours']).parent / 'lineage.parquet'
    input_paths = [cfg['hours'], cfg['stations'], cfg['station_qc'], cfg['source_registry'], str(config_path)]
    hourly_manifest = Path(cfg['hours']).parents[2] / 'reports/physics_phase/hourly_manifest.json'
    if hourly_manifest.exists():
        input_paths.append(str(hourly_manifest))
    if lineage.exists():
        input_paths.append(str(lineage))
    manifest = {'schema_version': cfg['schema_version'], 'config_sha256': digest(config_path),
                'config_snapshot': cfg,
                'input_sha256': {p: digest(p) for p in input_paths}, 'sources': sources,
                'rows': len(frame), 'stations': len(stations), 'files': manifests,
                'years': sorted(frame.timestamp_utc.dt.year.unique().astype(int).tolist()),
                'raw_lineage': 'Existing hourly_manifest.json raw file hashes; per-file .lineage.parquet observations',
                'availability_assumption': 'Completed hour available at hour-end for retrospective forecast; archive publication/network latency unknown',
                'geography': 'NOAA ISO-IN candidates with country-coordinate conflicts excluded; not an official India border',
                'label_evidence': 'Independent later hourly sensor measurement at exact t+6h, not disaster occurrence',
                'untrained_hazards': cfg['hazard_targets'], 'restricted_view': 'Not admitted; retained original separate restricted store',
                'china': 'Excluded from both training and evaluation; legacy artifacts unchanged',
                'subhour': '10/30-minute features unavailable in hourly archive; no interpolation',
                'missing_pm': 'PM optional and missing here; no PM head fitted'}
    Path(cfg['reports'], 'preparation.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
    print(f'Prepared {len(frame)} rows at {len(stations)} physical sites', flush=True)
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--config', default=str(DEFAULT))
    a = p.parse_args()
    run(load(a.config), a.config)

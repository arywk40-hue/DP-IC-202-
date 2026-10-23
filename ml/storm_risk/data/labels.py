"""Only reviewed event/monitored-negative records can support binary labels."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from ml.storm_risk.data.splits import assign_split
from ml.storm_risk.settings import digest, utc

FIELDS = ['event_id', 'type', 'date_start', 'date_end', 'district', 'lat', 'lon', 'magnitude',
          'magnitude_unit', 'source_1', 'source_2', 'confidence', 'notes', 'time_known']


def read_events(path: Path, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Quarantine missing sources, definitions, time or location; retain reasons."""
    if path.stat().st_size > cfg['limits']['max_file_bytes']:
        raise ValueError('Event records exceed configured budget')
    raw = pd.read_csv(path, keep_default_na=False)
    if not set(FIELDS) <= set(raw) or len(raw) > cfg['limits']['max_rows'] or raw.event_id.duplicated().any() or raw.event_id.astype(str).str.strip().eq('').any():
        raise ValueError('Complete unique event record schema required')
    accepted, excluded = [], []
    for item in raw.to_dict('records'):
        reasons = []
        for key in ('source_1', 'source_2'):
            if not str(item[key]).strip():
                reasons.append('MISSING_' + key.upper())
        a, b = urlparse(str(item['source_1'])), urlparse(str(item['source_2']))
        synthetic = cfg['evidence_kind'] == 'synthetic_engineering'
        if not synthetic and (a.scheme not in {'https', 'http'} or b.scheme not in {'https', 'http'} or not a.netloc or not b.netloc):
            reasons.append('REVIEWABLE_SOURCE_URLS_REQUIRED')
        if item['source_1'] == item['source_2'] or cfg['labels']['require_distinct_domains'] and a.netloc == b.netloc:
            reasons.append('TWO_DISTINCT_SOURCE_DOMAINS_REQUIRED')
        if str(item['time_known']).lower() not in {'true', '1'}:
            reasons.append('UNKNOWN_EVENT_TIME')
        if str(item['confidence']).lower() not in cfg['labels']['accepted_confidence']:
            reasons.append('CONFIDENCE_NOT_ADMITTED')
        target = cfg['target']
        if item['type'] not in {target['name'], cfg['labels']['negative_record_type']}:
            reasons.append('WRONG_TARGET')
        if item['type'] == target['name']:
            if not target['definition']:
                reasons.append('TARGET_DEFINITION_REQUIRED')
            if target['minimum_magnitude'] is not None:
                try:
                    magnitude = float(item['magnitude'])
                    if not np.isfinite(magnitude) or magnitude < target['minimum_magnitude'] or item['magnitude_unit'] != target['magnitude_unit']:
                        reasons.append('TARGET_MAGNITUDE_NOT_VERIFIED')
                except (ValueError, TypeError):
                    reasons.append('TARGET_MAGNITUDE_NOT_VERIFIED')
        try:
            start, end = utc(item['date_start']), utc(item['date_end'])
            lat, lon = float(item['lat']), float(item['lon'])
            if end < start or end - start > pd.Timedelta(hours=cfg['limits']['max_event_hours']):
                raise ValueError('Invalid event duration')
            if not np.isfinite([lat, lon]).all() or not -90 <= lat <= 90 or not -180 <= lon <= 180:
                raise ValueError('Invalid location')
            item.update(date_start=start, date_end=end, lat=lat, lon=lon)
        except (ValueError, TypeError):
            reasons.append('INVALID_TIME_OR_LOCATION')
        if reasons:
            excluded.append({**item, 'exclusion_reasons': ';'.join(sorted(set(reasons)))})
        else:
            accepted.append(item)
    return pd.DataFrame(accepted, columns=FIELDS), pd.DataFrame(excluded, columns=[*FIELDS, 'exclusion_reasons'])


def read_labels(path: Path, events: pd.DataFrame, cfg: dict, grid: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Match explicit positives and monitored zeros; never label absent hours."""
    raw = pd.read_csv(path)
    if not {'time', 'lat', 'lon', 'label', 'split'} <= set(raw) or len(raw) > cfg['limits']['max_rows']:
        raise ValueError('Bounded labels need time, lat, lon, label, split')
    raw['time'] = pd.to_datetime([utc(v) for v in raw.time], utc=True)
    for key in ('lat', 'lon', 'label'):
        raw[key] = pd.to_numeric(raw[key], errors='raise')
    if (not raw.split.isin(['train', 'calib', 'test']).all() or not raw.label.dropna().isin([0, 1]).all()
            or not raw.split.eq(assign_split(raw.time, cfg)).all()):
        raise ValueError('Invalid binary label or split inconsistent with configured dates')
    if not raw.time.eq(raw.time.dt.floor('h')).all() or raw.duplicated(['time', 'lat', 'lon']).any():
        raise ValueError('Unique exact hourly label identities required')
    if not np.isfinite(raw[['lat', 'lon']].to_numpy()).all() or not raw.lat.between(-90, 90).all() or not raw.lon.between(-180, 180).all():
        raise ValueError('Invalid label coordinates')
    raw['_row'] = np.arange(len(raw))
    excluded_grid = pd.Series(False, index=raw.index)
    if grid is not None and len(raw):
        points = grid[['lat', 'lon']].drop_duplicates().to_numpy(float)
        distance, position = cKDTree(points).query(raw[['lat', 'lon']].to_numpy(float))
        raw['record_lat'], raw['record_lon'] = raw.lat.copy(), raw.lon.copy()
        raw['grid_distance_deg'] = distance
        raw[['lat', 'lon']] = points[position]
        excluded_grid = pd.Series(distance > cfg['labels']['match_radius_deg'], index=raw.index)
        excluded_grid |= raw.duplicated(['time', 'lat', 'lon'], keep=False)
    expanded = []
    for record in events.to_dict('records'):
        for time in pd.date_range(record['date_start'].floor('h'), record['date_end'].floor('h'), freq='h'):
            expanded.append(dict(time=time, event_id=record['event_id'], event_lat=record['lat'], event_lon=record['lon'],
                record_label=int(record['type'] == cfg['target']['name'])))
            if len(expanded) > cfg['limits']['max_label_candidates']:
                raise ValueError('Event window expansion exceeds configured budget')
    matches = {}
    if expanded:
        source = pd.DataFrame(expanded)
        counts = raw.groupby('time').size().to_frame('left').join(source.groupby('time').size().rename('right')).fillna(0)
        if (counts.left * counts.right).sum() > cfg['limits']['max_label_candidates']:
            raise ValueError('Event matching exceeds configured candidate budget')
        candidates = raw.merge(source, on='time', how='inner')
        nearby = np.hypot(candidates.lat - candidates.event_lat, candidates.lon - candidates.event_lon) <= cfg['labels']['match_radius_deg']
        for row_id, group in candidates.loc[nearby].groupby('_row'):
            if not excluded_grid.loc[row_id] and group.record_label.nunique() == 1 and group.label.notna().all() and group.label.eq(group.record_label).all():
                matches[row_id] = '|'.join(sorted(group.event_id.astype(str).unique()))
    raw['event_id'] = raw._row.map(matches)
    raw['exclusion_reasons'] = np.where(raw.label.isna(), 'UNKNOWN_LABEL', 'NO_UNCONFLICTED_CONFIRMED_RECORD')
    raw.loc[excluded_grid, 'exclusion_reasons'] = 'GRID_MATCH_OUT_OF_RADIUS_OR_AMBIGUOUS_CELL_HOUR'
    rejected = raw.loc[raw.event_id.isna()].drop(columns='_row')
    admitted = raw.loc[raw.event_id.notna()].drop(columns=['_row', 'exclusion_reasons']).copy()
    if 'available_at' in admitted:
        admitted['available_at'] = pd.to_datetime([utc(v) for v in admitted.available_at], utc=True)
    else:
        admitted['available_at'] = admitted.time + pd.Timedelta(hours=cfg['time']['label_delay_hours'])
    if (admitted.available_at < admitted.time).any():
        raise ValueError('Outcome availability cannot precede its event hour')
    receipt = dict(labels_sha256=digest(path), input_rows=len(raw), admitted_rows=len(admitted), excluded_rows=len(rejected),
        evidence_kind=cfg['evidence_kind'], sources_independence='DECLARED_DISTINCT_RECORD_SOURCES_REQUIRES_OWNER_REVIEW',
        grid_alignment='NEAREST_CONFIGURED_CELL_WITHIN_RADIUS_NO_COLLISION_MERGING' if grid is not None else 'EXACT_SUPPLIED_LABEL_COORDINATES',
        missing_hours='UNKNOWN_NEVER_FILLED_WITH_ZERO')
    return admitted, rejected, receipt

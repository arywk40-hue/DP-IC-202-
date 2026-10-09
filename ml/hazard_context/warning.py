"""Independent next-H-hour onset labels; no guessed negatives or post-onset positives.

Events must already have passed source admission (the CLI rechecks it). Whole
physical groups use their earliest target onset. This is an additive experiment;
the historical exact-future-window target is retained in train.targets.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from ml.hazard_context.events import TARGETS, utc
from ml.hazard_context.matching import DEFAULTS, distance, group_events, validate_monitoring
from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS

PROTOCOL_PATH = Path(__file__).resolve().parents[2]/'configs/himalayan_warning_v1.json'


def load_protocol(path=PROTOCOL_PATH):
    raw = Path(path).read_bytes()
    p = json.loads(raw)
    if p.get('schema_version')!='indra_warning_window_v1' or p.get('label_mode')!='next_h_hours':
        raise ValueError('Versioned next-H-hour protocol required')
    for key in ['horizon_hours','history_minutes','cadence_seconds']:
        if isinstance(p.get(key),bool) or not isinstance(p.get(key),int) or p[key]<=0:
            raise ValueError('Positive integer protocol horizon/history/cadence required')
    if p['cadence_seconds']!=3600 or p['history_minutes']<1440:
        raise ValueError('Current research feature builder requires hourly, at least 24-hour history')
    if not p.get('targets') or set(p['targets'])-TARGETS or len(p['targets'])!=len(set(p['targets'])):
        raise ValueError('Distinct supported protocol targets required')
    if p.get('sensor_columns')!=RAW_SENSOR_COLUMNS or p.get('deployment_approved') is not False:
        raise ValueError('Six-channel research-only protocol required')
    if not isinstance(p.get('matching'),dict) or set(p['matching'])-set(DEFAULTS) or any(not np.isfinite(v) or v<0 for v in p['matching'].values()):
        raise ValueError('Invalid protocol matching parameters')
    policy=p.get('alert_selection',{})
    for key in ['max_false_alert_episodes_per_100_monitored_site_days','minimum_validation_positive_event_groups','minimum_validation_negative_site_days']:
        if isinstance(policy.get(key),bool) or not isinstance(policy.get(key),(int,float)) or not math.isfinite(policy[key]) or policy[key]<0:
            raise ValueError('Finite nonnegative validation threshold policy required')
    if policy['minimum_validation_positive_event_groups']<1 or policy['minimum_validation_negative_site_days']<=0:
        raise ValueError('Positive validation episode/day support required')
    p['_sha256'] = hashlib.sha256(raw).hexdigest()
    return p


def mask_incomplete_history(labels, frame, history_minutes, cadence_seconds):
    if len(labels)!=len(frame):
        raise ValueError('Label/history row mismatch')
    out = labels.copy()
    ready = complete_sensor_history(frame,history_minutes,cadence_seconds)
    out['sensor_history_complete'] = ready
    out.loc[~ready,'label'] = np.nan
    out.loc[~ready,['event_group_id','event_id']] = None
    out.loc[~ready,'label_quality'] = 'six_channel_history_unavailable'
    return out


def complete_sensor_history(frame, history_minutes=1440, cadence_seconds=3600):
    """All six finite channels from t-history through t at exact native cadence.

No grid expansion/imputation. Delayed rows stay unavailable under the existing
aligned feature contract. A 24-hour span includes 25 hourly endpoints.
"""
    if history_minutes < 0 or cadence_seconds <= 0 or history_minutes*60 % cadence_seconds:
        raise ValueError('History must be a nonnegative whole number of native intervals')
    steps = int(history_minutes*60 // cadence_seconds)
    f = frame.reset_index(drop=True).copy()
    required = {'physical_site_id','timestamp_utc', *RAW_SENSOR_COLUMNS}
    if not required <= set(f):
        raise ValueError('Six channels and site/timestamp required for history eligibility')
    f['timestamp_utc'] = [utc(t) for t in f.timestamp_utc]
    if f.duplicated(['physical_site_id','timestamp_utc']).any():
        raise ValueError('Duplicate site timestamp')
    ready = np.zeros(len(f), bool)
    for _, rows in f.groupby('physical_site_id', sort=False):
        rows = rows.sort_values('timestamp_utc')
        good = pd.Series(np.isfinite(rows[RAW_SENSOR_COLUMNS].to_numpy(dtype=float)).all(axis=1), index=rows.index)
        for name,bounds in PHYSICAL_RANGES.items():
            good &= rows[name].between(*bounds)
        if 'pressure_reference' in rows:
            good &= rows.pressure_reference.eq('station')
        if 'available_at_utc' in rows:
            good &= pd.Series([utc(a) <= t for a,t in zip(rows.available_at_utc, rows.timestamp_utc)], index=rows.index)
        if 'interval_seconds' in rows:
            good &= rows.interval_seconds.eq(cadence_seconds)
        complete = good.rolling(steps+1, min_periods=steps+1).sum().eq(steps+1)
        if steps:
            contiguous = rows.timestamp_utc.diff().dt.total_seconds().eq(cadence_seconds)
            complete &= contiguous.rolling(steps, min_periods=steps).sum().eq(steps)
        ready[rows.index] = complete.to_numpy()
    return ready


def _coverage(monitors, start, end):
    """Union compatible reviewed intervals, retaining IDs; gaps cannot disappear."""
    by_definition = defaultdict(list)
    for r in monitors:
        by_definition[(r['source_dataset'],r['definition'])].append(r)
    for key in sorted(by_definition):
        cursor, ids = start, []
        for r in sorted(by_definition[key], key=lambda r:(utc(r['start_utc']),r['monitoring_id'])):
            a, b = utc(r['start_utc']), utc(r['end_utc'])
            if b <= cursor:
                continue
            if a > cursor:
                break
            cursor = b
            ids.append(r['monitoring_id'])
            if cursor >= end:
                return sorted(set(ids))
    return None


def warning_targets(frame, events, stations, monitoring, target, horizon_hours=6,
                    matching_cfg=None, restricted=False):
    """Label earliest admitted target onset in (issue, issue+H], else 0 or NaN.

    Positive: the full onset uncertainty range is strictly after issue and no
    later than H. Ongoing/recent episodes are excluded. Negative: compatible
    monitoring covers the entire future window and no plausible event/candidate
    overlaps it. Unknown event clocks/locations never become negative labels.
    """
    if target not in TARGETS or isinstance(horizon_hours,bool) or not math.isfinite(horizon_hours) or horizon_hours <= 0:
        raise ValueError('Known target and positive finite warning horizon required')
    if set(matching_cfg or {})-set(DEFAULTS):
        raise ValueError('Unknown matching parameter')
    cfg = {**DEFAULTS, **(matching_cfg or {})}
    if any(not np.isfinite(v) or v < 0 for v in cfg.values()):
        raise ValueError('Finite nonnegative matching limits required')
    required = {'physical_site_id','timestamp_utc','country_code'}
    if not required <= set(frame) or not frame.country_code.eq('IN').all():
        raise ValueError('Indian site/time observations required')
    if stations.physical_site_id.isna().any() or stations.physical_site_id.duplicated().any():
        raise ValueError('Resolve physical station identity before labelling')
    sites = stations.set_index('physical_site_id').to_dict('index')
    f = frame.reset_index(drop=True).copy()
    f['timestamp_utc'] = [utc(t) for t in f.timestamp_utc]
    if f.duplicated(['physical_site_id','timestamp_utc']).any():
        raise ValueError('Duplicate observation timestamp')
    events = [r for r in group_events(events, cfg) if r['event_type']==target]
    monitoring = validate_monitoring(monitoring or [])
    if len(f)*max(1,len(events)) > cfg['max_pairs']:
        raise ValueError('Warning matching resource budget exceeded; partition by site/date')
    groups = defaultdict(list)
    for r in events:
        groups[r['event_group_id']].append(r)
    horizon = pd.Timedelta(hours=horizon_hours)
    rows = []
    for row in f.to_dict('records'):
        site = sites.get(row['physical_site_id'])
        if site is None:
            raise ValueError('Unresolved physical station')
        lat, lon = float(site['latitude']), float(site['longitude'])
        if not np.isfinite([lat,lon]).all() or not -90<=lat<=90 or not -180<=lon<=180:
            raise ValueError('Invalid station coordinates')
        issue, end = row['timestamp_utc'], row['timestamp_utc']+horizon
        base = dict(physical_site_id=row['physical_site_id'], timestamp_utc=issue,
                    target_window_end_utc=end, label=np.nan, event_group_id=None,
                    event_id=None, event_type=target,
                    interval_seconds=row.get('interval_seconds',3600),
                    event_start_utc=None, event_onset_min_utc=None, event_onset_max_utc=None,
                    monitoring_ids=None, label_quality='unknown')
        positives, potentially_present, ongoing = [], False, False
        for group, members in groups.items():
            local, precise_nominal = [], False
            for r in members:
                d = distance(r,lat,lon)
                u = r.get('spatial_uncertainty_km')
                if d is not None and u is not None and d > cfg['spatial_radius_km']+u:
                    continue
                local.append(r)
                precise_nominal |= (d is not None and d <= cfg['spatial_radius_km'] and
                                    u is not None and u <= cfg['maximum_spatial_uncertainty_km'])
            if not local:
                continue
            timed = all(r['event_start_utc'] and r['event_end_utc'] and
                        r['temporal_uncertainty_hours'] is not None for r in members)
            if not timed:
                potentially_present = True
                continue
            lows = [utc(r['event_start_utc'])-pd.Timedelta(hours=r['temporal_uncertainty_hours']) for r in members]
            highs = [utc(r['event_start_utc'])+pd.Timedelta(hours=r['temporal_uncertainty_hours']) for r in members]
            earliest, latest = min(lows), min(highs)
            finish = max(utc(r['event_end_utc'])+pd.Timedelta(hours=r['temporal_uncertainty_hours']) for r in members)
            # The group represents one conservative physical episode. Later reports
            # must not turn post-onset observations into new precursor positives.
            if earliest <= issue <= finish+pd.Timedelta(hours=cfg['post_event_hours']):
                ongoing = True
            if issue < finish and earliest <= end:
                potentially_present = True
            admitted = all(r['admission_status']=='admitted_for_training' and
                           r['temporal_uncertainty_hours'] <= cfg['maximum_temporal_uncertainty_hours']
                           for r in members)
            if admitted and precise_nominal and issue < earliest and latest <= end:
                positives.append(dict(event_group_id=group,
                                      event_id=min(members,key=lambda r:(utc(r['event_start_utc']),r['event_id']))['event_id'],
                                      event_start_utc=min(utc(r['event_start_utc']) for r in members).isoformat(),
                                      event_onset_min_utc=earliest.isoformat(),event_onset_max_utc=latest.isoformat()))
        if ongoing:
            base['label_quality'] = 'ongoing_or_post_event_context'
        elif len(positives)==1:
            base.update(positives[0], label=1., label_quality='admitted_onset_in_next_h_hours')
        elif len(positives)>1:
            base['label_quality'] = 'multiple_episode_groups_require_adjudication'
        elif potentially_present:
            base['label_quality'] = 'candidate_or_uncertain_event_window'
        else:
            eligible = [m for m in monitoring if m['physical_site_id']==row['physical_site_id'] and
                        m['event_type']==target and m['spatial_coverage_radius_km']>=cfg['spatial_radius_km'] and
                        (restricted or m['rights_status']=='approved_open')]
            ids = _coverage(eligible,issue,end)
            if ids:
                base.update(label=0.,event_group_id=f'background_{int(issue.timestamp()//(72*3600))}',
                            monitoring_ids='|'.join(ids),label_quality='verified_full_warning_window_negative')
        rows.append(base)
    columns = ['physical_site_id','timestamp_utc','target_window_end_utc','label','event_group_id','event_id','event_type','interval_seconds',
               'event_start_utc','event_onset_min_utc','event_onset_max_utc','monitoring_ids','label_quality']
    return pd.DataFrame(rows,columns=columns)

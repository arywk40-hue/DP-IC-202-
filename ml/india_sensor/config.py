"""Validated research configuration; paths are relative to the repository root."""
import json
import math
import re
from pathlib import Path

import pandas as pd

from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / 'configs/india_sensor_risk.json'


def load(path=DEFAULT):
    cfg = json.loads(Path(path).read_text())
    if cfg['schema_version'] != 'indra_india_sensor_v1' or cfg['country_code'] != 'IN':
        raise ValueError('India sensor configuration required')
    if cfg['cadence_seconds'] != 3600:
        raise ValueError('Archive training currently requires native hourly data')
    cutoffs = [pd.Timestamp(cfg[k]) for k in ['validation_start', 'calibration_start', 'test_start', 'test_end']]
    if any(t.tzinfo is None or t.utcoffset().total_seconds() != 0 for t in cutoffs) or cutoffs != sorted(set(cutoffs)):
        raise ValueError('Ordered distinct UTC cutoffs required')
    if cfg['forecast_hours'] < 1 or cfg['history_minutes'] < 1440 or cfg['minimum_per_class'] < 1:
        raise ValueError('Invalid horizon/history/class minimum')
    if not cfg['threshold_targets'] or not cfg['strategies'] or not cfg['scopes']:
        raise ValueError('Nonempty targets, strategies and scopes required')
    for name, target in cfg['threshold_targets'].items():
        if not math.isfinite(float(target['threshold'])):
            raise ValueError('Finite measurement threshold required')
        if not re.fullmatch(r'[a-z][a-z0-9_]+', name) or target['variable'] not in RAW_SENSOR_COLUMNS:
            raise ValueError('Invalid target name or variable')
    if set(cfg['strategies']) - set('ABCD') or set(cfg['scopes']) - {'national', 'himalaya_holdout', 'temporal', 'himalaya_only'}:
        raise ValueError('Unknown strategy/scope')
    if not cfg.get('candidate_weights', ['unweighted']) or set(cfg.get('candidate_weights', ['unweighted'])) - {'unweighted', 'sqrt_ratio_capped'}:
        raise ValueError('Unknown class-weight candidate')
    policy = cfg.get('threshold_tuning')
    if policy and (not all(math.isfinite(float(v)) for v in policy.values()) or policy['beta'] <= 0 or policy['max_false_positive_hours_per_station_day'] < 0 or min(policy[k] for k in ['minimum_positive_hours', 'minimum_positive_episodes', 'minimum_positive_sites']) < 1):
        raise ValueError('Invalid predeclared threshold policy')
    for key in ['hours', 'stations', 'station_qc', 'source_registry', 'processed', 'features', 'models', 'reports']:
        cfg[key] = str((ROOT / cfg[key]).resolve())
    cfg['_config_path'] = str(Path(path).resolve())
    return cfg

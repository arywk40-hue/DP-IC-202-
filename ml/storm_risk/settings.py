"""Load local, versioned settings; no portal access or embedded credentials."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


def digest(path: str | Path) -> str:
    """Hash a local input without deserializing it."""
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def utc(value: Any, *, naive_is_utc: bool = False) -> pd.Timestamp:
    """Normalize a known UTC instant; naive CSV values need explicit consent."""
    stamp = pd.Timestamp(value)
    if pd.isna(stamp):
        raise ValueError('Missing time')
    if stamp.tzinfo is None:
        if not naive_is_utc:
            raise ValueError('Explicit UTC offset required')
        stamp = stamp.tz_localize('UTC')
    return stamp.tz_convert('UTC')


def load_config(path: str | Path, *, base: str | Path | None = None) -> dict:
    """Validate a complete snapshot before any model or label is inspected."""
    cfg = yaml.safe_load(Path(path).read_text())
    cfg['_base'] = str(Path(base or '.').resolve())
    cfg['_config_sha256'] = digest(path)
    gate = yaml.safe_load(resolve(cfg, cfg['paths']['gate']).read_text())
    cfg['gate'] = gate
    if cfg['schema_version'] != 'indra_storm_risk_v1' or gate['schema_version'] != 'indra_storm_gate_v1':
        raise ValueError('Unsupported storm configuration')
    if cfg['evidence_kind'] not in {'confirmed_event_records', 'synthetic_engineering'}:
        raise ValueError('Explicit evidence kind required')
    dates = [utc(cfg['time'][k]) for k in ('start', 'train_end', 'calib_end', 'end')]
    if not all(a < b for a, b in zip(dates, dates[1:])):
        raise ValueError('Ordered disjoint train/calib/test dates required')
    if cfg['time']['timezone'] != 'UTC' or cfg['precipitation_semantics'] != 'hourly_accumulation':
        raise ValueError('Select UTC hourly ERA5 accumulation semantics')
    r = cfg['region']
    if not (-90 <= r['south'] < r['north'] <= 90 and -180 <= r['west'] < r['east'] <= 180 and r['grid_degrees'] > 0):
        raise ValueError('Invalid region/grid')
    if not 1 <= cfg['features']['history_hours'] <= 168 or not 0 < cfg['features']['inner_validation_fraction'] < .5:
        raise ValueError('Bounded causal history/validation required')
    if not 0 <= cfg['target']['lead_hours'] <= 168:
        raise ValueError('Bounded target lead required')
    if gate['bootstrap_resamples'] < 1000 or not 0 < gate['confidence_level'] < 1 or gate['bin_count'] < 2:
        raise ValueError('At least 1000 day bootstrap samples required')
    if not 0 < cfg['ensemble']['simplex_step'] <= 1 or not np.isclose(1 / cfg['ensemble']['simplex_step'], round(1 / cfg['ensemble']['simplex_step'])):
        raise ValueError('Simplex step must divide one')
    if not 0 < cfg['anomaly']['percentile'] < 100:
        raise ValueError('Invalid anomaly percentile')
    c = cfg['confirmation']
    if not 0 <= c['threshold'] <= 1 or c['radius_deg'] <= 0 or c['n_min'] < 1 or c['window_hours'] < 1:
        raise ValueError('Invalid neighbour settings')
    if cfg['calibration']['method'] not in {'none', 'isotonic', 'platt'}:
        raise ValueError('Unsupported calibrator')
    if any(not isinstance(v, (int, float)) or not np.isfinite(v) or v <= 0 for v in cfg['limits'].values()):
        raise ValueError('Positive finite resource budgets required')
    if (not 0 <= gate['reliability_max'] <= 1 or not np.isfinite(gate['bss_min']) or gate['min_bin_count'] < 1
            or gate['min_positives_test'] < 1 or gate['min_test_days'] < 2):
        raise ValueError('Invalid evidence-gate thresholds')
    args = cfg['online']
    if (not 0 < args['reference_days'] < args['warmup_days'] or args['checkpoint_days'] < 1
            or args['rolling_days'] < 1 or args['min_reference_rows'] < 1
            or args['min_positives'] < 1 or args['min_negatives'] < 1 or not 0 < args['drift_brier_increase'] <= 1):
        raise ValueError('Invalid online warm-up/reference/checkpoint settings')
    if cfg['heatmaps']['time_stride_hours'] < 1 or cfg['heatmaps']['max_frames'] < 1:
        raise ValueError('Positive map sampling/budget required')
    if not cfg['heatmaps']['png_latest_only']:
        raise ValueError('PNG export supports latest per feature; all sampled frames remain in NPZ')
    if cfg['models']['ridge']['alpha'] <= 0 or not 1 <= cfg['models']['mlp']['epochs'] <= 1000:
        raise ValueError('Invalid linear/neural fit settings')
    return cfg


def resolve(cfg: dict, path: str | Path) -> Path:
    """Resolve configured paths against an explicit project directory."""
    value = Path(path)
    return value if value.is_absolute() else Path(cfg['_base']) / value


def snapshot(cfg: dict) -> dict:
    """Return a JSON-safe full settings snapshot without machine-local helpers."""
    return json.loads(json.dumps({k: v for k, v in cfg.items() if not k.startswith('_')}))

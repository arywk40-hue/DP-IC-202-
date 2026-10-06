"""Bounded research-only node forecast. Never emits an untrained hazard score."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from ml.datasets.registry import digest
from ml.india_sensor.config import DEFAULT, load
from ml.india_sensor.features import build
from ml.india_sensor.train import apply_calibration, experts
from ml.spatial_ensemble.national import region


def predict(history, cfg, strategy='B', scope='national'):
    if strategy not in ['A', 'B', 'C', 'D'] or scope not in cfg['scopes']:
        raise ValueError('Unknown strategy/scope')
    path = Path(cfg['models']) / 'metadata.json'
    meta = json.loads(path.read_text())
    if meta['model_version'] != 'india_sensor_research_v1':
        raise ValueError('Unknown model version')
    if meta['config_sha256'] != digest(DEFAULT if cfg.get('_config_path') is None else cfg['_config_path']):
        raise ValueError('Inference configuration differs from training')
    if history.physical_site_id.nunique() != 1:
        raise ValueError('One node history required; this is not spatial inference')
    runtime_cfg = {**cfg, 'allowed_sources': meta['allowed_sources'] + ['indra_owner_nodes']}
    f = build(history, runtime_cfg).sort_values('timestamp_utc')
    row = f.iloc[[-1]]
    issue = row.timestamp_utc.iloc[0]
    result = {'issue_time_utc': issue.isoformat(), 'target_time_utc': (issue + pd.Timedelta(hours=cfg['forecast_hours'])).isoformat(),
              'strategy': strategy, 'scope': scope, 'status': 'RESEARCH_ONLY_NOT_FIELD_VALIDATED',
              'deployment_approved': False, 'targets': {},
              'hazards': {h: {'probability': None, 'status': 'INDEPENDENT_LABELS_REQUIRED'} for h in meta['untrained_hazards']}}
    if issue - f.timestamp_utc.min() < pd.Timedelta(minutes=cfg['history_minutes']):
        result['status'] = 'REFUSED_INSUFFICIENT_HISTORY'
        return result
    if row[['temperature_c', 'relative_humidity_pct', 'wind_speed_mps']].isna().any(axis=None):
        result['status'] = 'REFUSED_INVALID_CURRENT_CORE'
        return result
    for target in meta['labels']:
        heads = meta['artifacts'][f'{scope}/{target}']
        head, calibration, fallback = heads.get(strategy, {}), None, None
        if strategy == 'C':
            calibration = head.get('mountain_calibration') if region(row).iloc[0] else None
            fallback = head.get('status')
            head = heads['B']
        elif strategy == 'D':
            expert = head.get('experts', {}).get(experts(row)[0], {})
            if expert.get('calibration') is not None and expert.get('artifact'):
                head = expert
            else:
                head, fallback = heads['B'], 'NATIONAL_FALLBACK_UNAVAILABLE_EXPERT'
        if head.get('status') != 'RESEARCH_FITTED':
            result['targets'][target] = {'probability': None, 'status': 'UNTRAINED_HEAD'}
            continue
        # Current fitted bounds are a simple OOD check, not a multivariate proof.
        violations = [name for name, bounds in head['training_bounds'].items()
                      if pd.notna(row[name].iloc[0]) and not bounds[0] <= float(row[name].iloc[0]) <= bounds[1]]
        if violations:
            result['targets'][target] = {'probability': None, 'status': 'REFUSED_OUTSIDE_TRAINED_RANGE', 'features': violations}
            continue
        model_path = Path(head['artifact'])
        if not model_path.is_absolute():
            model_path = Path(cfg['models']) / model_path
        model_path = model_path.resolve()
        try:
            trusted = model_path.is_relative_to(Path(cfg['models']).resolve()) and digest(model_path) == head['sha256']
        except OSError:
            trusted = False
        if not trusted:
            result['targets'][target] = {'probability': None, 'status': 'REFUSED_MISSING_OR_UNTRUSTED_ARTIFACT'}
            continue
        try:
            model = XGBClassifier()
            model.load_model(model_path)
            raw = model.predict_proba(row[head['features']].to_numpy(dtype='float32'))[:, 1]
            fit = calibration or head.get('calibration')
            p = apply_calibration(raw, fit)[0]
            if not np.isfinite(p):
                raise ValueError('Nonfinite prediction')
            result['targets'][target] = {'probability': float(p) if fit is not None else None,
                                        'research_score': float(raw[0]), 'probability_status': 'ARCHIVE_CALIBRATED_NOT_FIELD_VALIDATED' if fit else 'UNCALIBRATED',
                                        'status': fallback or 'RESEARCH_ONLY', 'definition': meta['labels'][target]}
            selection = head.get('threshold_selection') or {}
            cutoff = selection.get('raw_threshold')
            result['targets'][target]['validation_raw_cutoff'] = cutoff
            result['targets'][target]['research_flag'] = bool(raw[0] >= cutoff) if cutoff is not None else None
            result['targets'][target]['alert_enabled'] = False
        except (ValueError, RuntimeError, OSError) as exc:
            result['targets'][target] = {'probability': None, 'status': 'MODEL_FAILURE', 'reason': type(exc).__name__}
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--config', default=str(DEFAULT))
    p.add_argument('--input', required=True, help='One node UTC history in the exact sensor view schema')
    p.add_argument('--strategy', choices=list('ABCD'), default='B')
    p.add_argument('--scope', choices=['national', 'himalaya_holdout', 'temporal', 'himalaya_only'], default='national')
    p.add_argument('--model-dir', help='Serving artifact directory; frozen training config digest is still checked')
    a = p.parse_args()
    cfg = load(a.config)
    if a.model_dir:
        cfg['models'] = str(Path(a.model_dir).resolve())
    history = pd.read_csv(a.input, nrows=cfg['max_expanded_station_rows']+1)
    if len(history) > cfg['max_expanded_station_rows']:
        raise ValueError('Node history resource budget exceeded')
    print(json.dumps(predict(history, cfg, a.strategy, a.scope), indent=2, allow_nan=False))

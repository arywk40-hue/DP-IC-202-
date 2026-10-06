"""Optional observed PM forecasts with source/time/rights admission gates."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from ml.datasets.registry import digest
from ml.india_sensor.features import build, feature_columns
from ml.india_sensor.splits import row_roles, station_roles
from ml.six_sensor_forecast.features import future_targets
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS

PM = ['pm25_ug_m3', 'pm10_ug_m3']


def eligibility(source, restricted=False):
    if source.get('timezone_verified') not in (True, 1) or source.get('interval_semantics') not in ('instant', 'hour_end', 'hour_start'):
        return 'BLOCKED_CLOCK_OR_INTERVAL_UNVERIFIED'
    if source.get('license_class') == 'restricted' and not restricted:
        return 'RESTRICTED_VIEW_REQUIRED'
    if source.get('license_class') not in ['open', 'restricted']:
        return 'BLOCKED_RIGHTS_UNRESOLVED'
    return 'ELIGIBLE_RESTRICTED' if source['license_class'] == 'restricted' else 'ELIGIBLE_OPEN'


def audit(registry='data/registry/sources.json', output='reports/offline_phase/pm_admission.json'):
    sources = json.loads(Path(registry).read_text())['sources']
    names = ['india_cpcb_kaggle_v2', 'delhi_opencity', 'openaq', 'sensor_community']
    report = {'heads': {p: 'UNTRAINED_NO_APPROVED_INDIAN_PM_LABELS' for p in PM},
              'sources': {s['source_id']: {'status': eligibility(s, restricted=True),
                          'license_class': s['license_class'], 'timezone_verified': s['timezone_verified'],
                          'interval_semantics': s['interval_semantics']} for s in sources if s['source_id'] in names},
              'legacy': 'Existing NC CPCB PM weights retained as assumption-limited legacy research, never admitted into new clean India fit',
              'synthetic': 'Contract tests only; not real PM accuracy', 'china': 'Excluded',
              'registry_sha256': digest(registry)}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(report, indent=2)+'\n')
    return report


def train(frame, source, cfg, stations, output, restricted=False):
    status = eligibility(source, restricted)
    if not status.startswith('ELIGIBLE'):
        raise ValueError(status)
    if not frame.source_id.eq(source['source_id']).all():
        raise ValueError('PM source provenance mismatch')
    if source.get('country_code') != 'IN' or source['source_id'].startswith('uci_beijing'):
        raise ValueError('PM country provenance must explicitly be Indian')
    view_cfg = {**cfg, 'allowed_sources': [source['source_id']]}
    features = build(frame, view_cfg)
    target = future_targets(features[['location_id', 'timestamp_utc', *RAW_SENSOR_COLUMNS]], cfg['forecast_hours'])
    roles = station_roles(stations, 'national', cfg)
    masks = row_roles(features, roles, cfg)
    columns = [c for c in feature_columns(features) if any(c.startswith(p) for p in PM)]
    output = Path(output) / ('restricted' if source['license_class'] == 'restricted' else 'open')
    output.mkdir(parents=True, exist_ok=True)
    report = {'view': output.name, 'source': source['source_id'], 'heads': {}, 'station_roles': roles,
              'country': 'IN', 'seed': cfg['seed'], 'source_metadata': source,
              'config_sha256': digest(cfg['_config_path']),
              'input_frame_sha256': hashlib.sha256(pd.util.hash_pandas_object(frame, index=True).values.tobytes()).hexdigest(),
              'purpose': 'Observed future optical PM measurement, not certified AQI/fire/dust', 'hardware_validated': False}
    for name in PM:
        fitting = masks['train'] & target[name].notna()
        test = masks['test'] & target[name].notna()
        active = [c for c in columns if features.loc[fitting, c].notna().any()]
        if fitting.sum() < 100 or not active:
            report['heads'][name] = {'status': 'UNTRAINED_INSUFFICIENT_LABELS', 'labels': int(fitting.sum())}
            continue
        model = XGBRegressor(n_estimators=40, max_depth=3, tree_method='hist', max_bin=64,
                             n_jobs=cfg['threads'], random_state=cfg['seed'])
        model.fit(features.loc[fitting, active], target.loc[fitting, name])
        path = output / (name+'.ubj')
        model.save_model(path)
        p = np.clip(model.predict(features.loc[test, active]), 0, 5000) if test.any() else np.array([])
        y = target.loc[test, name].to_numpy()
        report['heads'][name] = {'status': 'RESEARCH_ONLY', 'fit_rows': int(fitting.sum()), 'test_rows': len(y),
                                 'features': active, 'sha256': digest(path),
                                 'mae': float(np.abs(y-p).mean()) if len(y) else None,
                                 'rmse': float(np.sqrt(((y-p)**2).mean())) if len(y) else None}
    (output/'metadata.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    return report


if __name__ == '__main__':
    from ml.india_sensor.config import DEFAULT, load
    parser = argparse.ArgumentParser()
    parser.add_argument('--registry', default='data/registry/sources.json')
    parser.add_argument('--output', default='reports/offline_phase/pm_admission.json')
    parser.add_argument('--input')
    parser.add_argument('--stations')
    parser.add_argument('--source-id')
    parser.add_argument('--config', default=str(DEFAULT))
    parser.add_argument('--restricted', action='store_true')
    a = parser.parse_args()
    if a.input:
        if not a.stations or not a.source_id:
            parser.error('--input requires --stations and --source-id')
        source = next(s for s in json.loads(Path(a.registry).read_text())['sources'] if s['source_id'] == a.source_id)
        # Check eligibility before reading a possibly unavailable/untrusted export.
        if not eligibility(source, a.restricted).startswith('ELIGIBLE'):
            raise ValueError(eligibility(source, a.restricted))
        result = train(pd.read_csv(a.input), source, load(a.config), pd.read_csv(a.stations), a.output, a.restricted)
    else:
        result = audit(a.registry, a.output)
    print(json.dumps(result, indent=2))

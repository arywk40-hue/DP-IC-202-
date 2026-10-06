"""India-only measured-threshold forecast benchmark, NOT a disaster detector.

A: sensor/time. B: +GPS/EGM96 altitude. C: B + mountain calibration.
D: sensor/geo regional experts, falling back to B. XGBoost is reused from
the existing node forecasts; the between-node ensemble remains unchanged.
"""
from __future__ import annotations
import argparse
import importlib.metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier

from ml.datasets.registry import digest
from ml.india_sensor.config import DEFAULT, load
from ml.india_sensor.features import feature_columns
from ml.india_sensor.metrics import metrics, cluster_brier_interval
from ml.india_sensor.splits import station_roles, row_roles
from ml.spatial_ensemble.national import region
from ml.spatial_ensemble.episodes import episode_ids
from ml.india_sensor.thresholds import tune, decision_metrics


def logit(p):
    p = np.clip(p, 1e-6, 1-1e-6)
    return np.log(p/(1-p)).reshape(-1, 1)


def calibration(y, p, minimum=20):
    if min(int((y == 0).sum()), int((y == 1).sum())) < minimum:
        return None
    m = LogisticRegression(C=1., random_state=42).fit(logit(p), y)
    return {'coefficient': float(m.coef_[0, 0]), 'intercept': float(m.intercept_[0]),
            'rows': len(y), 'positives': int(y.sum()), 'method': 'chronological_Platt_logit'}


def apply_calibration(p, fit):
    if fit is None:
        return p
    z = logit(p).ravel()*fit['coefficient'] + fit['intercept']
    return 1/(1+np.exp(-np.clip(z, -60, 60)))


def experts(frame):
    """Declared GPS/elevation proxies, not official regions or external inputs."""
    return np.select([region(frame), (frame.longitude >= 88) & (frame.latitude >= 22),
                      (frame.longitude <= 76) & (frame.latitude >= 22), frame.latitude < 22],
                     ['mountain_proxy', 'northeast_proxy', 'western_arid_proxy', 'peninsula_proxy'],
                     default='northern_plains_proxy')


def fit_head(frame, target, masks, columns, cfg, path):
    good = frame[target].notna().to_numpy()
    train = np.asarray(masks['train']) & good
    cal = np.asarray(masks['calibration']) & good
    val = np.asarray(masks['validation']) & good
    test = np.asarray(masks['test']) & good
    y = frame[target].to_numpy(dtype=float)
    counts = {role: int((np.asarray(m) & good).sum()) for role, m in masks.items()}
    if min(int((y[train] == 0).sum()), int((y[train] == 1).sum())) < cfg['minimum_per_class']:
        return None, {'status': 'INSUFFICIENT_TRAINING_CLASSES', 'rows_by_role': counts}
    active = [c for c in columns if frame.loc[train, c].notna().any()]
    xtrain = frame.loc[train, active].to_numpy(dtype='float32')
    xval = frame.loc[val, active].to_numpy(dtype='float32')
    selected, candidates = None, []
    for policy in cfg.get('candidate_weights', ['unweighted']):
        weight = 1. if policy == 'unweighted' else min(25., np.sqrt((y[train] == 0).sum()/(y[train] == 1).sum()))
        params = dict(n_estimators=cfg['rounds'], max_depth=3, learning_rate=.1, max_bin=64,
                      tree_method='hist', n_jobs=cfg['threads'], random_state=cfg['seed'],
                      objective='binary:logistic', eval_metric='logloss', scale_pos_weight=weight)
        model = XGBClassifier(**params)
        model.fit(xtrain, y[train])
        vp = model.predict_proba(xval)[:, 1] if val.any() else np.array([])
        decision = tune(y[val], vp, episode_ids(frame.loc[val, 'timestamp_utc']),
                        frame.loc[val, 'physical_site_id'], cfg['threshold_tuning'], cfg['cadence_seconds']) if cfg.get('threshold_tuning') else None
        vm = metrics(y[val], vp)
        entry = {'weight_policy': policy, 'scale_pos_weight': float(weight), 'validation_uncalibrated': vm,
                 'threshold_selection': decision}
        candidates.append(entry)
        score = (decision['validation_decisions']['f2'], vm['pr_auc_average_precision'] or 0.) if decision and decision.get('raw_threshold') is not None else (-1., 0.)
        if selected is None or score > selected['selection_score']:
            selected = dict(model=model, params=params, validation_scores=vp, entry=entry, selection_score=score)
    model, vp, decision = selected['model'], selected['validation_scores'], selected['entry']['threshold_selection']
    reproducibility = {'checked': False}
    if cfg.get('verify_reproducibility'):
        repeated = XGBClassifier(**selected['params']).fit(xtrain, y[train])
        same = bytes(model.get_booster().save_raw()) == bytes(repeated.get_booster().save_raw())
        if not same:
            raise RuntimeError('Identical-seed repeated fit differs')
        reproducibility = {'checked': True, 'identical_model_bytes': True, 'seed': cfg['seed']}
        del repeated
    del xtrain, xval
    raw_cal = model.predict_proba(frame.loc[cal, active].to_numpy(dtype='float32'))[:, 1] if cal.any() else np.array([])
    fit = calibration(y[cal], raw_cal, cfg['minimum_per_class'])
    raw = model.predict_proba(frame.loc[test, active].to_numpy(dtype='float32'))[:, 1] if test.any() else np.array([])
    model.save_model(path)
    bounds = {c: [float(frame.loc[train, c].min()), float(frame.loc[train, c].max())] for c in active}
    artifact = {'status': 'RESEARCH_FITTED', 'features': active, 'inactive_features': sorted(set(columns)-set(active)),
                'rows_by_role': counts, 'train_positive': int(y[train].sum()), 'calibration': fit,
                'artifact': str(path), 'sha256': digest(path), 'training_bounds': bounds,
                'validation_uncalibrated': metrics(y[val], vp),
                'prevalence_train': float(y[train].mean()),
                'candidate_selection': {'method': 'validation_F2_then_AP; unweighted fallback if unsupported', 'candidates': candidates,
                                        'chosen': selected['entry']['weight_policy'], 'scale_pos_weight': selected['entry']['scale_pos_weight']},
                'threshold_selection': decision, 'reproducibility': reproducibility,
                'probability_status': 'CALIBRATED_ARCHIVE_ONLY' if fit else 'UNCALIBRATED_SCORE'}
    return {'probabilities': apply_calibration(raw, fit), 'raw_calibration': raw_cal,
            'raw_test': raw, 'raw_thresholds': np.full(len(raw), decision['raw_threshold'] if decision and decision['raw_threshold'] is not None else .5),
            'calibration_truth': y[cal], 'calibration_mask': cal, 'test_mask': test}, artifact


def breakdown(frame, target, test, probabilities, cfg):
    truth = frame.loc[test, target].to_numpy(dtype=float)
    meta = frame.loc[test]
    def score(mask):
        m = np.asarray(mask)
        r = metrics(truth[m], probabilities[m], cfg['cadence_seconds'])
        r['physical_sites'] = int(meta.loc[m, 'physical_site_id'].nunique())
        r['brier_station_bootstrap_95ci'] = cluster_brier_interval(truth[m], probabilities[m], meta.loc[m, 'physical_site_id'], cfg['seed'])
        return r
    heights = pd.cut(meta.elevation_m, [-np.inf, 500, 1500, 3000, np.inf], labels=['below500', '500to1500', '1500to3000', 'above3000']).astype(object).fillna('unknown')
    hp = meta.latitude.between(30.3, 33.3) & meta.longitude.between(75.5, 79.1)
    return {'overall': score(np.ones(len(meta), dtype=bool)),
            'per_climate_zone': {str(z): score(meta.climate_zone.eq(z)) for z in sorted(meta.climate_zone.dropna().unique())},
            'per_elevation_band': {str(z): score(heights.eq(z)) for z in sorted(heights.unique())},
            'per_geographic_proxy': {str(z): score(experts(meta) == z) for z in sorted(set(experts(meta)))},
            'himalaya_proxy': score(region(meta)), 'himachal_bbox_proxy': score(hp),
            'himachal_warning': 'Rectangle only; no official Himachal boundary verification'}


def run(cfg, config_path):
    report_path = Path(cfg['reports']) / 'preparation.json'
    prepared = json.loads(report_path.read_text())
    if prepared['config_sha256'] != digest(config_path):
        raise ValueError('Configuration changed since preparation')
    for path, expected in prepared['input_sha256'].items():
        if digest(path) != expected:
            raise ValueError('Source/registry/QC changed since preparation')
    frames = []
    for item in prepared['files']:
        if digest(item['features']) != item['feature_sha256'] or digest(item['labels']) != item['label_sha256']:
            raise ValueError('Modified feature/label artifact')
        f = pd.read_parquet(item['features'])
        labels = pd.read_parquet(item['labels'])
        f = f.merge(labels.drop(columns=['source_id']), on=['physical_site_id', 'timestamp_utc'], validate='one_to_one')
        frames.append(f)
    frame = pd.concat(frames, ignore_index=True)
    del frames
    # Current T/RH/wind required, PM and QC-masked pressure remain optional.
    valid = frame[['temperature_c', 'relative_humidity_pct', 'wind_speed_mps']].notna().all(axis=1)
    frame = frame[valid].reset_index(drop=True)
    columns_a = [c for c in feature_columns(frame) if c not in cfg['threshold_targets'] and c != 'target_timestamp_utc']
    columns_b = columns_a + ['latitude', 'longitude', 'elevation_m']
    stations = pd.read_csv(Path(cfg['processed']) / 'stations.csv')
    stations = stations[stations.location_id.isin(frame.location_id)]
    output = Path(cfg['models'])
    output.mkdir(parents=True, exist_ok=True)
    experiments, artifacts = {}, {}
    for scope in cfg['scopes']:
        roles = station_roles(stations, scope, cfg)
        masks = row_roles(frame, roles, cfg)
        print(f'{scope}: ' + str({k: int(m.sum()) for k, m in masks.items()}), flush=True)
        experiment = {'station_roles': roles, 'row_roles': {k: int(m.sum()) for k, m in masks.items()}, 'targets': {}}
        for target, definition in cfg['threshold_targets'].items():
            predictions, heads = {}, {}
            for strategy, cols in [('A', columns_a), ('B', columns_b)]:
                print(f'Fit {scope}/{target}/{strategy}', flush=True)
                values, artifact = fit_head(frame, target, masks, cols, cfg, output/f'{scope}_{target}_{strategy}.ubj')
                heads[strategy] = artifact
                if values is not None:
                    predictions[strategy] = values
            if 'B' in predictions:
                base = predictions['B']
                # C uses the same India-wide model, with separately fitted
                # mountain calibration. Never calibrate on held-out Himalaya.
                mountain = region(frame).to_numpy()
                local = mountain[base['calibration_mask']]
                fit = calibration(base['calibration_truth'][local], base['raw_calibration'][local], cfg['minimum_per_class'])
                p = base['probabilities'].copy()
                raw_scores, thresholds = base['raw_test'].copy(), base['raw_thresholds'].copy()
                test_mountain = mountain[base['test_mask']]
                # Invert global calibration is unnecessary: get raw B scores.
                if fit is not None:
                    b = XGBClassifier()
                    b.load_model(heads['B']['artifact'])
                    raw = b.predict_proba(frame.loc[base['test_mask'], heads['B']['features']].to_numpy(dtype='float32'))[:, 1]
                    p[test_mountain] = apply_calibration(raw[test_mountain], fit)
                predictions['C'] = {**base, 'probabilities': p}
                heads['C'] = {'status': 'REGIONAL_CALIBRATION' if fit else 'NATIONAL_FALLBACK_NO_MOUNTAIN_CALIBRATION',
                              'base': 'B', 'mountain_calibration': fit}
                # D's routing uses only runtime GPS/elevation, not reanalysis.
                p = base['probabilities'].copy()
                routes = experts(frame)
                heads['D'] = {'status': 'REGIONAL_EXPERTS_WITH_NATIONAL_FALLBACK', 'experts': {}}
                for name in sorted(set(routes)):
                    local_masks = {r: np.asarray(m) & (routes == name) for r, m in masks.items()}
                    sites = frame.loc[local_masks['train'], 'physical_site_id'].nunique()
                    if sites < cfg['minimum_expert_sites']:
                        heads['D']['experts'][name] = {'status': 'NATIONAL_FALLBACK_INSUFFICIENT_SITES', 'sites': int(sites)}
                        continue
                    values, artifact = fit_head(frame, target, local_masks, columns_b, cfg, output/f'{scope}_{target}_D_{name}.ubj')
                    heads['D']['experts'][name] = artifact
                    if values is not None and artifact['calibration'] is not None:
                        p[(routes == name)[base['test_mask']]] = values['probabilities']
                        raw_scores[(routes == name)[base['test_mask']]] = values['raw_test']
                        thresholds[(routes == name)[base['test_mask']]] = values['raw_thresholds']
                    else:
                        artifact['serving_status'] = 'NATIONAL_FALLBACK_NO_CALIBRATED_EXPERT'
                predictions['D'] = {**base, 'probabilities': p, 'raw_test': raw_scores, 'raw_thresholds': thresholds}
            target_report = {'definition': {**definition, 'horizon_hours': cfg['forecast_hours'],
                             'meaning': 'Exact t+6h completed hourly measurement, not next-6h occurrence or official hazard'}, 'strategies': {}}
            for name in cfg['strategies']:
                if name in predictions:
                    result = predictions[name]
                    target_report['strategies'][name] = breakdown(frame, target, result['test_mask'], result['probabilities'], cfg)
                    target_report['strategies'][name]['raw_validation_cutoff_test'] = decision_metrics(
                        frame.loc[result['test_mask'], target], result['raw_test']-result['raw_thresholds'], 0., cfg['cadence_seconds'])
                    target_report['strategies'][name]['raw_validation_cutoff_test']['note'] = 'Raw score minus per-route validation cutoff >=0; fallback .5 when validation support is insufficient'
                else:
                    target_report['strategies'][name] = {'status': 'UNAVAILABLE'}
            if 'B' in predictions:
                test = predictions['B']['test_mask']
                current = frame.loc[test, definition['variable']].to_numpy()
                target_report['baselines'] = {
                    'current_measurement_persistence': breakdown(frame, target, test, (current >= definition['threshold']).astype(float), cfg),
                    'training_prevalence': breakdown(frame, target, test, np.full(test.sum(), heads['B']['prevalence_train']), cfg)}
            experiment['targets'][target] = target_report
            artifacts[f'{scope}/{target}'] = heads
        experiments[scope] = experiment
    result = {'model_version': 'india_sensor_research_v1', 'seed': cfg['seed'],
              'trained_at_utc': datetime.now(timezone.utc).isoformat(),
              'config_sha256': digest(config_path), 'preparation_sha256': digest(report_path),
              'data_rows_after_current_core_mask': len(frame), 'prepared_rows': prepared['rows'],
              'station_count': len(stations), 'years': prepared['years'],
              'runtime': {'python': platform.python_version(), **{p: importlib.metadata.version(p) for p in ['numpy', 'pandas', 'scikit-learn', 'xgboost', 'pyarrow']}},
              'evidence_categories': ['geographical_holdout', 'temporal_holdout', 'future_measured_threshold_validation'],
              'not_evidence': ['historical_disaster_validation', 'real_INDRA_sensor_validation', 'between_node_risk_validation'],
              'spatial_buffer_km': cfg['buffer_km'], 'threshold': .5, 'no_row_caps': True,
              'decision_policy': cfg.get('threshold_tuning'),
              'split_scope_semantics': 'temporal intentionally shares stations across disjoint times; other scopes are buffered whole-site splits; Himalaya-only uses only QC-valid mountain proxy sites',
              'episode_partition': 'Global 72h blocks wholly assigned to one chronological role; boundary blocks and history/target overlaps dropped. Blocks are storm proxies, not event truth.',
              'untrained_hazards': {h: 'INDEPENDENT_LABELS_REQUIRED' for h in cfg['hazard_targets']},
              'deployment_approved': False, 'esp32': 'No new export or hardware verification',
              'geography_warning': 'GPS/elevation region and Himachal bbox proxies, not official boundaries; missing/QC-invalid altitude not assumed mountain',
              'intervals': '95% station-cluster bootstrap Brier intervals; not prediction bands; shared storms not independent across stations',
              'calibration': 'Separate Sep/Oct validation stations; Platt fit excludes held-out sites and test hours; field reliability not established',
              'experiment': experiments}
    Path(cfg['reports'], 'results.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    metadata = {k: v for k, v in result.items() if k != 'experiment'}
    metadata.update(artifacts=artifacts, labels=cfg['threshold_targets'], feature_views={'A': columns_a, 'B': columns_b},
                    station_roles={s: e['station_roles'] for s, e in experiments.items()},
                    allowed_sources=cfg['allowed_sources'], raw_lineage_manifest=prepared['input_sha256'])
    metadata['implementation_sha256'] = {str(p.name): digest(p) for p in Path(__file__).parent.glob('*.py')}
    (output / 'metadata.json').write_text(json.dumps(metadata, indent=2, allow_nan=False)+'\n')
    Path(cfg['reports'], 'model_manifest.json').write_text(json.dumps(metadata, indent=2, allow_nan=False)+'\n')
    print('Wrote measured-threshold evaluation; all disaster heads remain unavailable', flush=True)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--config', default=str(DEFAULT))
    a = p.parse_args()
    run(load(a.config), a.config)

#!/usr/bin/env python3
"""Read-only XGBoost audit: native holdouts, archived 14-feature tests and Mandi proxies.

Run: python3 scripts/test_models.py --as-of 2026-10-07
Raw downloads, recovered Git files and JSON/console evidence stay in ignored results/.
No training functions are invoked and no model files are modified.
"""
from __future__ import annotations

import argparse
import contextlib
from datetime import date, datetime, timedelta
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import ssl
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             f1_score, mean_absolute_error, mean_squared_error, r2_score)
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
HAZARDS = ['wildfire', 'flood', 'storm', 'air_quality']
THRESHOLDS = dict(wildfire=.70, flood=.70, storm=.75, air_quality=.65)
PRIORITY = ['flood', 'storm', 'wildfire', 'air_quality']
SOURCES = {
    'weather': 'https://archive-api.open-meteo.com/v1/archive',
    'air': 'https://air-quality-api.open-meteo.com/v1/air-quality',
}


def sha(path):
    if getattr(Path(path).stat(), 'st_flags', 0) & 0x40000000:
        raise FileNotFoundError(f'Cloud-only file is not downloaded locally: {path}')
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def classify(truth, predicted, names=('negative', 'positive')):
    truth, predicted = np.asarray(truth, dtype=int), np.asarray(predicted, dtype=int)
    labels = list(range(len(names)))
    if not len(truth):
        raise ValueError('No usable labels')
    return dict(rows=len(truth), accuracy=float(accuracy_score(truth, predicted)),
                macro_f1=float(f1_score(truth, predicted, labels=labels, average='macro', zero_division=0)),
                classification_report=classification_report(truth, predicted, labels=labels,
                    target_names=list(names), output_dict=True, zero_division=0),
                confusion_matrix=confusion_matrix(truth, predicted, labels=labels).tolist(),
                class_order=list(names), true_share={n: float(np.mean(truth == i)) for i, n in enumerate(names)},
                predicted_share={n: float(np.mean(predicted == i)) for i, n in enumerate(names)})


def regress(truth, predicted, persistence):
    return dict(rows=len(truth), mae=float(mean_absolute_error(truth, predicted)),
                rmse=float(np.sqrt(mean_squared_error(truth, predicted))), r2=float(r2_score(truth, predicted)),
                persistence_mae=float(mean_absolute_error(truth, persistence)),
                accuracy=None, macro_f1=None, reason='Continuous regression: classification accuracy/F1 are undefined')


def discover():
    """Identify actual Booster weights, rather than treating every JSON report as a model."""
    found = []
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file() or path.suffix not in {'.json', '.ubj', '.pkl', '.joblib'}:
            continue
        relative = path.relative_to(ROOT)
        if any(p in {'.git', '.pio', 'results', '__pycache__', '.venv', 'venv'} for p in relative.parts):
            continue
        if path.suffix == '.json':
            try:
                data = json.loads(path.read_text())
            except (ValueError, UnicodeError):
                continue
            if not isinstance(data, dict) or 'learner' not in data:
                continue
        entry = dict(path=str(relative), sha256=sha(path), origin='working_tree', status='not_evaluated')
        if path.suffix in {'.pkl', '.joblib'}:
            entry['reason'] = 'Pickle requires a known trusted deserialization/feature contract; not loaded automatically'
        else:
            try:
                booster = xgb.Booster(params={'nthread': 4}); booster.load_model(path)
                config = json.loads(booster.save_config())['learner']
                entry.update(objective=config['objective']['name'], n_features=booster.num_features(),
                             feature_names=booster.feature_names, trees=booster.num_boosted_rounds())
            except (ValueError, xgb.core.XGBoostError) as exc:
                entry['reason'] = str(exc)
        found.append(entry)
    return found


def recover_legacy(ref, cache):
    """Recover immutable historical source/weights without changing the checked-out code."""
    commit = git('rev-parse', ref).decode().strip()
    paths = git('ls-tree', '-r', '--name-only', commit).decode().splitlines()
    modules = {}
    for filename in ['prepare_dataset.py', 'train_model.py', 'convert_to_c.py']:
        candidates = [p for p in paths if p in [f'code/ml/{filename}', f'ml/{filename}']]
        if not candidates:
            raise FileNotFoundError(f'{filename} absent from historical ref {commit}')
        destination = cache / filename
        destination.write_bytes(git('show', f'{commit}:{candidates[0]}'))
        modules[filename] = destination
    prep = load_module(modules['prepare_dataset.py'], 'archived_prepare_dataset')
    trainer = load_module(modules['train_model.py'], 'archived_train_model')
    if prep.FEATURE_NAMES != trainer.FEATURE_NAMES or prep.HAZARD_CLASSES != trainer.HAZARD_CLASSES:
        raise ValueError('Archived feature/class contracts disagree')
    raw_path = next((p for p in paths if p.endswith('/weatherHistory.csv')), None)
    if raw_path is None:
        raise FileNotFoundError('weatherHistory.csv absent from historical ref')
    raw = cache / 'weatherHistory.csv'; raw.write_bytes(git('show', f'{commit}:{raw_path}'))
    groups, inventory = [], []
    for norm in [p for p in paths if p.endswith('/normalization.json') and '/model' in p]:
        metadata = json.loads(git('show', f'{commit}:{norm}'))
        folder = norm.rsplit('/', 1)[0]
        if metadata.get('feature_names') != prep.FEATURE_NAMES:
            continue
        target_dir = cache / folder; target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / 'normalization.json').write_bytes(git('show', f'{commit}:{norm}'))
        group = dict(name=f'archive:{folder}', folder=target_dir, heads={}, normalization=metadata,
                     native_holdout=folder in ['ml/model', 'ml/model_baseline'])
        for hazard in HAZARDS:
            source = f'{folder}/xgboost_{hazard}.json'
            if source not in paths:
                continue
            dest = target_dir / Path(source).name; dest.write_bytes(git('show', f'{commit}:{source}'))
            group['heads'][hazard] = dest
            inventory.append(dict(path=f'git:{commit}:{source}', sha256=sha(dest), origin='git_history',
                                  objective='binary:logistic', n_features=14, status='not_evaluated'))
        if group['heads']:
            groups.append(group)
    recovered_paths={item['path'].split(':',2)[-1] for item in inventory}
    for source in paths:
        if source in recovered_paths or '/model' not in source or not source.endswith('.json'):
            continue
        raw_bytes=git('show',f'{commit}:{source}')
        try:
            data=json.loads(raw_bytes)
        except ValueError:
            continue
        if not isinstance(data,dict) or 'learner' not in data:continue
        learner=data['learner']
        inventory.append(dict(path=f'git:{commit}:{source}',sha256=hashlib.sha256(raw_bytes).hexdigest(),
            origin='git_history',objective=learner['objective']['name'],
            n_features=int(learner['learner_model_param']['num_feature']),
            status='incompatible_archived_contract',
            reason='Different archived feature/target contract; 14-feature weatherHistory testing would be invalid; original preparation/split not reconstructed'))
    return prep, groups, inventory, dict(commit=commit, dataset=raw_path, dataset_sha256=sha(raw),
        source_sha256={n: sha(p) for n, p in modules.items()}, features=prep.FEATURE_NAMES,
        class_order=HAZARDS, split='random seed 42; test 20%; validation 12.5% of remaining 80%',
        evidence='Input-derived rule labels; synthetic PM2.5/CO2/lightning; random split is not temporal or site validation')


def download(name, params, cache, offline=False):
    url = SOURCES[name] + '?' + urllib.parse.urlencode(params)
    fingerprint = hashlib.sha256(url.encode()).hexdigest()[:16]
    path = cache / f'{name}_{fingerprint}.json'
    if not path.exists():
        if offline:
            raise FileNotFoundError(f'No cached response for {url}')
        try:
            import certifi
            context = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            context = ssl.create_default_context()
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers={'User-Agent': 'INDRA-model-evaluation/1.0'})
                with urllib.request.urlopen(request, timeout=45, context=context) as response:
                    raw = response.read()
                value = json.loads(raw)
                if value.get('error') or 'hourly' not in value:
                    raise ValueError(value.get('reason', 'Missing hourly response'))
                path.write_bytes(raw)
                break
            except (OSError, ValueError):
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)
    value = json.loads(path.read_text())
    return value, dict(url=url, sha256=sha(path), cache=str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                       returned_latitude=value.get('latitude'), returned_longitude=value.get('longitude'),
                       elevation=value.get('elevation'), units=value.get('hourly_units'))


def mandi_data(args, cache):
    end = date.fromisoformat(args.as_of) - timedelta(days=1)
    start = end - timedelta(days=29)
    params = dict(latitude=31.71, longitude=76.93, start_date=start.isoformat(), end_date=end.isoformat(), timezone='UTC')
    weather, wproof = download('weather', {**params, 'hourly':
        'temperature_2m,relative_humidity_2m,dew_point_2m,surface_pressure,wind_speed_10m,cloud_cover,precipitation'}, cache, args.offline)
    air, aproof = download('air', {**params, 'hourly': 'pm10,pm2_5,carbon_monoxide,nitrogen_dioxide'}, cache, args.offline)
    for data in [weather, air]:
        if data.get('utc_offset_seconds') != 0:
            raise ValueError('API timezone must be UTC')
    def frame(data):
        df = pd.DataFrame(data['hourly']); df['timestamp_utc'] = pd.to_datetime(df.pop('time'), utc=True)
        if df.timestamp_utc.duplicated().any():
            raise ValueError('Duplicate API timestamps')
        return df
    df = frame(weather).merge(frame(air), on='timestamp_utc', how='outer', validate='one_to_one').sort_values('timestamp_utc')
    expected = pd.date_range(start.isoformat(), end.isoformat()+'T23:00:00', freq='h', tz='UTC')
    df = df.set_index('timestamp_utc').reindex(expected).rename_axis('timestamp_utc').reset_index()
    if weather['hourly_units']['wind_speed_10m'] != 'km/h' or weather['hourly_units']['surface_pressure'] != 'hPa':
        raise ValueError('Unexpected API wind/pressure units')
    return df, dict(start_date=start.isoformat(), end_date=end.isoformat(), expected_hours=720,
        weather=wproof, air=aproof, missing_per_variable={c: int(df[c].isna().sum()) for c in df if c != 'timestamp_utc'},
        evidence='Open-Meteo gridded weather reanalysis and CAMS air-quality model data, not local sensor ground truth')


def legacy_tests(prep, groups, cache, mandi, args):
    output = cache / 'prepared'; output.mkdir(exist_ok=True)
    with contextlib.redirect_stdout(io.StringIO()):
        prep.prepare_dataset(str(cache/'weatherHistory.csv'), str(output))
    features = pd.read_csv(output/'features.csv').to_numpy(dtype=np.float32)
    labels = pd.read_csv(output/'labels.csv').to_numpy(dtype=np.float32)
    indices = np.arange(len(features))
    train_val, test = train_test_split(indices, test_size=.2, random_state=42)
    train, validation = train_test_split(train_val, test_size=.125, random_state=42)
    results, bundles = [], []
    weather_features = proxy = valid = None
    if mandi is not None:
        base = pd.DataFrame(dict(temp_current=mandi.temperature_2m,
            humidity_current=mandi.relative_humidity_2m/100, pressure_current=mandi.surface_pressure,
            wind_speed_current=mandi.wind_speed_10m, pm25_current=mandi.pm2_5,
            co2_current=np.nan, lightning_dist_current=np.nan))
        weather_features = prep.compute_derived_features(base)[prep.FEATURE_NAMES].astype(np.float32)
        # Preserve unknown lightning in lightning_threat; never synthesize external features.
        rain = mandi.precipitation.rolling(3, min_periods=3).sum()
        valid = mandi[['temperature_2m', 'relative_humidity_2m', 'wind_speed_10m', 'pm2_5']].notna().all(axis=1) & rain.notna()
        conditions = dict(flood=rain >= args.rain_3h_mm, storm=mandi.wind_speed_10m > 40,
            wildfire=(mandi.temperature_2m > 30) & (mandi.relative_humidity_2m < 35) & (mandi.wind_speed_10m > 20),
            air_quality=mandi.pm2_5 > 60)
        proxy = np.full(len(mandi), 'normal', dtype=object)
        for hazard in reversed(PRIORITY):
            proxy[np.asarray(conditions[hazard])] = hazard
    reconstructed_mean = features[train].mean(axis=0)
    reconstructed_std = features[train].std(axis=0); reconstructed_std[reconstructed_std == 0] = 1
    for group in groups:
        norm = group['normalization']; mean = np.asarray(norm['mean'], dtype=np.float32); std = np.asarray(norm['std'], dtype=np.float32)
        if mean.shape != (14,) or std.shape != (14,) or np.any(std <= 0):
            raise ValueError('Invalid archived normalization')
        norm_match = bool(np.allclose(mean, reconstructed_mean, rtol=1e-5, atol=1e-5) and
                          np.allclose(std, reconstructed_std, rtol=1e-5, atol=1e-5))
        native = group['native_holdout'] and norm_match
        held_predictions, weather_predictions = {}, {}
        for hazard, path in group['heads'].items():
            booster = xgb.Booster(params={'nthread': 4}); booster.load_model(path)
            if booster.num_features() != 14:
                raise ValueError('Historical model width differs from feature contract')
            p = booster.predict(xgb.DMatrix((features[test]-mean)/std))
            predicted = p > THRESHOLDS[hazard]; held_predictions[hazard] = predicted
            entry = dict(model=f'{group["name"]}/{hazard}', origin='git_history', sha256=sha(path),
                         target=hazard, split='weatherHistory_seed42_test20', threshold=THRESHOLDS[hazard],
                         test_keys_sha256=hashlib.sha256(test.tobytes()).hexdigest(),
                         evidence='native_random_holdout' if native else 'weatherHistory_transfer_diagnostic_not_original_test',
                         normalization_reconstruction_matches=norm_match,
                         heldout=classify(labels[test, HAZARDS.index(hazard)], predicted))
            if weather_features is not None:
                p = booster.predict(xgb.DMatrix((weather_features.to_numpy()-mean)/std))
                predicted = p > THRESHOLDS[hazard]; weather_predictions[hazard] = predicted
                entry['mandi_proxy'] = classify((proxy[valid] == hazard).astype(int), predicted[valid])
                entry['mandi_proxy']['evidence'] = 'Exclusive research proxies; modeled weather; missing CO2/lightning inputs'
                entry['predicted_share_all_hours'] = float(predicted.mean())
            results.append(entry)
        if len(held_predictions) == 4:
            matrix = np.column_stack([held_predictions[h] for h in HAZARDS])
            bundle = dict(model=group['name'], native_holdout=native,
                rows=len(test), subset_accuracy=float(accuracy_score(labels[test], matrix)),
                macro_f1=float(f1_score(labels[test], matrix, average='macro', zero_division=0)),
                mean_head_accuracy=float(np.mean([accuracy_score(labels[test, i], matrix[:, i]) for i in range(4)])),
                sha256_by_head={h: sha(p) for h,p in group['heads'].items()})
            if len(weather_predictions) == 4:
                pred = np.full(len(mandi), 'normal', dtype=object)
                for hazard in reversed(PRIORITY):
                    pred[weather_predictions[hazard]] = hazard
                order = ['normal', *HAZARDS]
                bundle['mandi_proxy'] = classify([order.index(s) for s in proxy[valid]],
                    [order.index(s) for s in pred[valid]], order)
                bundle['mandi_proxy']['majority_normal_accuracy'] = float(np.mean(proxy[valid] == 'normal'))
                bundle['mandi_proxy']['overlapping_head_prediction_hours'] = int((np.column_stack(list(weather_predictions.values())).sum(axis=1) > 1).sum())
            bundles.append(bundle)
    return results, bundles, dict(rows=len(features), train=len(train), validation=len(validation), test=len(test),
        generated_feature_sha256=sha(output/'features.csv'), generated_label_sha256=sha(output/'labels.csv'),
        missing_mandi_features=['co2_current', 'lightning_dist_current', 'lightning_threat'],
        no_voc_feature=True, unused_downloaded_variables=['pm10', 'carbon_monoxide', 'nitrogen_dioxide', 'cloud_cover', 'dew_point_2m'],
        proxy_rule=f'flood: preceding 3h rain >= {args.rain_3h_mm} mm; storm: wind >40 km/h; wildfire: T>30C, RH<35%, wind>20 km/h; air_quality: PM2.5>60 ug/m3; else normal',
        proxy_priority=PRIORITY, usable_proxy_hours=None if valid is None else int(valid.sum()),
        derivation_notes='Historical compute_derived_features reused exactly. RH fraction; wind km/h. API dewpoint retained but historical approximation used. Surface pressure preserved; no sea-level substitution or >900hPa imputation.')


def native_regressors(inventory, mandi):
    from ml.six_sensor_forecast.features import build_features, future_targets, split_masks
    from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS, PHYSICAL_RANGES
    results = []; datasets = {}
    weather = None
    if mandi is not None:
        weather = pd.DataFrame(dict(location_id='Mandi_OpenMeteo', timestamp_utc=mandi.timestamp_utc,
            temperature_c=mandi.temperature_2m, relative_humidity_pct=mandi.relative_humidity_2m,
            pressure_hpa=mandi.surface_pressure, pm25_ug_m3=mandi.pm2_5, pm10_ug_m3=mandi.pm10,
            wind_speed_mps=mandi.wind_speed_10m/3.6))
    for report_path in sorted((ROOT/'ml/models').glob('*/training_report.json')):
        report = json.loads(report_path.read_text()); folder = report_path.parent
        source = ROOT/'data'/('india_cpcb_research' if folder.name.startswith('india_') else 'uci_beijing_air_quality')/'observations.csv'
        readable = source.exists() and not (getattr(source.stat(), 'st_flags', 0) & 0x40000000)
        frame = features = labels = masks = current_ok = None
        if readable:
            if sha(source) != report['source']['observations_sha256']:
                raise ValueError(f'Native dataset hash mismatch: {source}')
            if source not in datasets:
                datasets[source] = build_features(pd.read_csv(source))
            frame, features = datasets[source]
        sensors = report.get('sensor_profile', RAW_SENSOR_COLUMNS)
        if readable:
            labels = future_targets(frame, report['horizon_hours']); split = report['split']
            masks = split_masks(frame, report['horizon_hours'], split['validation_start'], split['test_start'], split['holdout_locations'])
            current_ok = np.isfinite(frame[sensors].to_numpy()).all(axis=1)
        wf = wfeatures = wlabels = None
        if weather is not None:
            wf, wfeatures = build_features(weather); wlabels = future_targets(wf, report['horizon_hours'])
        for target, head in report['models'].items():
            for kind in ['teacher', 'student']:
                path = folder/head[f'{kind}_file']
                if sha(path) != head[f'{kind}_sha256']:
                    raise ValueError('Forecast model checksum mismatch')
                booster = xgb.Booster(params={'nthread': 4}); booster.load_model(path)
                columns = report['architecture'][f'{kind}_features']
                x = None if not readable else (features[columns] if kind == 'teacher' else frame[columns].astype(np.float32))
                for split_name in ['future_test', 'geographic_test']:
                    if not readable:
                        prior = report['models'][target]['metrics'][split_name]
                        score = dict(prior[kind], persistence_mae=prior['persistence']['mae'], accuracy=None, macro_f1=None)
                        results.append(dict(model=str(path.relative_to(ROOT)), sha256=sha(path), target=target,
                            split=split_name, evidence='RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED', regression=score))
                        continue
                    mask = masks[split_name] & current_ok & np.isfinite(labels[target])
                    if not mask.any():
                        continue
                    truth = labels.loc[mask, target].to_numpy(); baseline = frame.loc[mask, target].to_numpy(dtype=np.float32)
                    residual = booster.predict(xgb.DMatrix(x.loc[mask], feature_names=columns))
                    predicted = np.clip(baseline+head[f'{kind}_weight']*residual, *PHYSICAL_RANGES[target])
                    results.append(dict(model=str(path.relative_to(ROOT)), sha256=sha(path), target=target,
                        split=split_name, evidence='native_holdout', regression=regress(truth, predicted, baseline)))
                if wf is not None:
                    mask = np.isfinite(wf[sensors].to_numpy()).all(axis=1) & np.isfinite(wlabels[target])
                    if mask.any():
                        xw = wfeatures[columns] if kind == 'teacher' else wf[columns].astype(np.float32)
                        baseline = wf.loc[mask, target].to_numpy(dtype=np.float32)
                        predicted = np.clip(baseline+head[f'{kind}_weight']*booster.predict(xgb.DMatrix(xw.loc[mask], feature_names=columns)), *PHYSICAL_RANGES[target])
                        results.append(dict(model=str(path.relative_to(ROOT)), sha256=sha(path), target=target,
                            split='Mandi_modeled_future_values', evidence='modeled_numeric_proxy_not_hazard_accuracy',
                            regression=regress(wlabels.loc[mask,target].to_numpy(), predicted, baseline)))
    return results, datasets


def native_event_heads(datasets):
    from ml.event_classifier.features import build_features, apply_event_labels, split_masks, ALL_EVENT_FEATURE_COLS
    path = ROOT/'ml/models/uci_beijing_event_rules_6sensor/event_training_report.json'
    report = json.loads(path.read_text()); source = ROOT/'data/uci_beijing_air_quality/observations.csv'
    if not source.exists() or getattr(source.stat(),'st_flags',0) & 0x40000000:
        results=[]
        for target,head in report['models'].items():
            if head.get('skipped'):continue
            model=path.parent/head['student_file']
            if sha(model)!=head['student_sha256']:raise ValueError('Event model checksum mismatch')
            for split_name in ['future_test','geographic_test']:
                m=head['metrics'][split_name]
                # Reconstruct the original report from its saved confusion counts, explicitly not a fresh rerun.
                tn,fp,fn,tp=[m[k] for k in ['tn','fp','fn','tp']]
                y=np.repeat([0,0,1,1],[tn,fp,fn,tp]);p=np.repeat([0,1,0,1],[tn,fp,fn,tp])
                results.append(dict(model=str(model.relative_to(ROOT)),sha256=sha(model),target=target,
                    split=split_name,evidence='RECORDED_ONLY_NATIVE_RAW_CLOUD_ONLY_NOT_FRESHLY_REPRODUCED',heldout=classify(y,p)))
        return results
    if sha(source) != report['source']['observations_sha256']:
        raise ValueError('Event dataset hash mismatch')
    frame, features = build_features(pd.read_csv(source)); labels = apply_event_labels(features)
    split = report['split']; masks = split_masks(frame, split['validation_start'], split['test_start'], split['holdout_locations'])
    good = np.isfinite(features[ALL_EVENT_FEATURE_COLS].to_numpy()).all(axis=1); results=[]
    for target, head in report['models'].items():
        if head.get('skipped'):
            continue
        model = path.parent/'esp32_student'/f'{target}.ubj'
        if sha(model)!=head['student_sha256']:raise ValueError('Event model checksum mismatch')
        booster = xgb.Booster(params={'nthread': 4}); booster.load_model(model)
        for split_name in ['future_test', 'geographic_test']:
            mask = masks[split_name] & good & np.isfinite(labels[target])
            if mask.any():
                scores = booster.predict(xgb.DMatrix(features.loc[mask, ALL_EVENT_FEATURE_COLS], feature_names=ALL_EVENT_FEATURE_COLS))
                results.append(dict(model=str(model.relative_to(ROOT)), sha256=sha(model), target=target,
                    split=split_name, evidence='native_holdout_sensor_rule_labels_not_observed_hazards',
                    heldout=classify(labels.loc[mask,target], scores >= .5)))
    return results


def native_india_heads(inventory):
    from ml.india_sensor.splits import row_roles
    from ml.india_sensor.train import apply_calibration, experts
    results=[]; available={item['sha256']: item for item in inventory}
    for report_dir in ['offline_phase', 'india_sensor_phase']:
        folder=ROOT/'reports'/report_dir
        manifest=json.loads((folder/'model_manifest.json').read_text())
        prep=json.loads((folder/'preparation.json').read_text())
        if 'config_snapshot' in prep:
            cfg=prep['config_snapshot']
        else:
            config_path=ROOT/'configs/india_sensor_risk.json'
            if sha(config_path)!=manifest['config_sha256']:
                raise ValueError('Historical India training configuration checksum mismatch')
            cfg=json.loads(config_path.read_text())
        for scope, roles in manifest['station_roles'].items():
            frames=[]
            for item in prep['files']:
                if item['location_id'] not in roles['test']:
                    continue
                fp, lp=Path(item['features']), Path(item['labels'])
                if not fp.exists() or not lp.exists():
                    raise FileNotFoundError(f'Native prepared file missing: {fp}')
                if sha(fp)!=item['feature_sha256'] or sha(lp)!=item['label_sha256']:
                    raise ValueError('Native prepared feature/label checksum mismatch')
                f=pd.read_parquet(fp).merge(pd.read_parquet(lp).drop(columns=['source_id']),
                    on=['physical_site_id','timestamp_utc'],validate='one_to_one')
                f=f[f[['temperature_c','relative_humidity_pct','wind_speed_mps']].notna().all(axis=1)]
                frames.append(f.loc[row_roles(f,roles,cfg)['test']])
            if not frames:
                continue
            frame=pd.concat(frames,ignore_index=True)
            for target in manifest['labels']:
                heads=manifest['artifacts'][f'{scope}/{target}']
                for strategy, head in heads.items():
                    candidates=head.get('experts',{}).items() if strategy=='D' else [(strategy,head)]
                    for route, h in candidates:
                        if h.get('status')!='RESEARCH_FITTED' or h['sha256'] not in available:
                            continue
                        mask=frame[target].notna()
                        if strategy=='D':
                            mask &= experts(frame)==route
                        data=frame.loc[mask]
                        cross_region=False
                        if not len(data) and strategy=='D':
                            # The frozen geographic holdout can contain no sites in this expert's route.
                            # Test its weights on the full heldout population as an explicitly separate
                            # transfer diagnostic; do not claim that the deployed router uses this head.
                            data=frame.loc[frame[target].notna()]
                            cross_region=True
                        if not len(data):continue
                        path=ROOT/available[h['sha256']]['path']
                        booster=xgb.Booster(params={'nthread': 4});booster.load_model(path)
                        scores=booster.predict(xgb.DMatrix(data[h['features']].to_numpy(dtype=np.float32)))
                        p=apply_calibration(scores,h.get('calibration'))
                        results.append(dict(model=str(path.relative_to(ROOT)),sha256=sha(path),target=target,
                            split=f'{report_dir}/{scope}/test/{route}',
                            test_keys_sha256=hashlib.sha256(pd.util.hash_pandas_object(
                                data[['physical_site_id','timestamp_utc']],index=False).to_numpy().tobytes()).hexdigest(),
                            evidence='cross_region_transfer_no_native_routed_test_rows' if cross_region else 'native_holdout_future_measured_threshold',
                            heldout=classify(data[target],p>=.5), calibrated=h.get('calibration') is not None,
                            threshold=.5, source='NOAA Indian hourly measurements; PM absent; no disaster ground truth'))
    return results


def comparable_rankings(records):
    groups={}
    for record in records:
        split=record['split']
        cohort=split.rsplit('/',1)[0] if '/test/' in split else split
        key=(record['target'],cohort,record['evidence'],record.get('test_keys_sha256',record['sha256']))
        groups.setdefault(key,[]).append(record)
    ranked=[]
    for key,rows in sorted(groups.items()):
        previous=None;rank=0
        for position,row in enumerate(sorted(rows,key=lambda r:(-r['heldout']['macro_f1'],-r['heldout']['accuracy'],r['model'])),1):
            score=(row['heldout']['macro_f1'],row['heldout']['accuracy'])
            if score!=previous:rank=position
            ranked.append((rank,row));previous=score
    return ranked


def markdown(report):
    lines=['# XGBoost model test results', '', f'Run date: {report["as_of"]}. No model or training code was changed.', '',
        '## Scope and interpretation', '',
        'The requested 14-feature pipeline is absent from the current tree. Its exact source, weatherHistory.csv and compatible weights were recovered into an ignored cache from Git history. Current models were evaluated on their own feature/target contracts and native held-out splits. A single accuracy ranking across regression, rule classification and future-threshold classification would be invalid.', '',
        'The archived training labels are computed from the same features, with synthetic PM2.5, CO2 and lightning. High weatherHistory accuracy measures rule reproduction and is not independently observed hazard accuracy. Random row splitting and full-series pressure interpolation also weaken the independence of that test.', '',
        'Mandi scores below are agreement with explicitly defined research proxies on Open-Meteo/CAMS modeled data, not real hazard labels or sensor validation. CO2, lightning distance and lightning threat remain NaN. VOC is not one of the 14 features. CO and NO2 are not CO2; they are downloaded but never substituted. The historical dewpoint approximation is reused despite downloading source dewpoint.', '',
        '[Open-Meteo weather documentation](https://open-meteo.com/en/docs/historical-weather-api) · [Open-Meteo air-quality documentation](https://open-meteo.com/en/docs/air-quality-api)', '',
        '## Run contract', '', '```json', json.dumps(report['legacy_contract'],indent=2), '```', '',
        '## Mandi source and missing-data audit', '', '```json', json.dumps(report['mandi'],indent=2), '```', '',
        '## Archived bundle ranking on the reconstructed native holdout', '',
        '| Rank | Bundle | Exact four-label accuracy | Macro-F1 across four hazards | Mean binary accuracy |',
        '| --- | --- | ---: | ---: | ---: |']
    ranked=sorted([b for b in report['bundles'] if b['native_holdout']],key=lambda b:(-b['macro_f1'],-b['subset_accuracy'],b['model']))
    for i,b in enumerate(ranked,1):
        lines.append(f'| {i} | {b["model"]} | {b["subset_accuracy"]:.6f} | {b["macro_f1"]:.6f} | {b["mean_head_accuracy"]:.6f} |')
    if ranked:
        best=ranked[0];ties=[b['model'] for b in ranked if b['macro_f1']==best['macro_f1'] and b['subset_accuracy']==best['subset_accuracy']]
        lines += ['', 'Best comparable native legacy bundle(s): **'+', '.join(ties)+'**. This names the best rule-reproduction score, not a field deployment winner.']
    lines += ['', '## Archived bundles: Mandi exclusive proxy ranking', '',
        '| Rank | Bundle | Proxy accuracy | Macro-F1 (all five classes) | Normal-only baseline accuracy | Predicted class shares |',
        '| --- | --- | ---: | ---: | ---: | --- |']
    for i,b in enumerate(sorted([b for b in report['bundles'] if 'mandi_proxy' in b],key=lambda b:(-b['mandi_proxy']['macro_f1'],-b['mandi_proxy']['accuracy'],b['model'])),1):
        m=b['mandi_proxy'];shares=', '.join(f'{k} {100*v:.1f}%' for k,v in m['predicted_share'].items())
        lines.append(f'| {i} | {b["model"]} | {m["accuracy"]:.6f} | {m["macro_f1"]:.6f} | {m["majority_normal_accuracy"]:.6f} | {shares} |')
    lines += ['', '## All classifier accuracy results', '',
        'Rank resets for each target, identical test-row key set, split and evidence category. Order: macro-F1, then accuracy; exact score ties receive equal ranks. Regression models are listed separately with their continuous errors.', '',
        '| Rank within comparable task | Model | Target / split | Accuracy | Binary macro-F1 | Evidence |', '| ---: | --- | --- | ---: | ---: | --- |']
    for rank,r in comparable_rankings(report['classifications']):
        m=r['heldout'];lines.append(f'| {rank} | {r["model"]} | {r["target"]} / {r["split"]} | {m["accuracy"]:.6f} | {m["macro_f1"]:.6f} | {r["evidence"]} |')
    lines += ['', '## Regression results (classification accuracy is not applicable)', '',
        '| Model | Split | Rows | MAE | RMSE | R² | Persistence MAE |', '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for r in report['regressions']:
        m=r['regression'];lines.append(f'| {r["model"]} | {r["split"]} | {m["rows"]} | {m["mae"]:.6f} | {m["rmse"]:.6f} | {m["r2"]:.6f} | {m["persistence_mae"]:.6f} |')
    lines += ['', '## Per-class reports and confusion matrices', '', 'Binary matrix order is [negative, positive], rows=true and columns=predicted. Zero-support classes have zero F1 by explicit convention.']
    for r in report['classifications']:
        for key in ['heldout','mandi_proxy']:
            if key not in r:continue
            m=r[key];lines += ['', f'### {r["model"]} — {r["split"]} / {key}', '',
                f'Rows {m["rows"]}; accuracy {m["accuracy"]:.6f}; macro-F1 {m["macro_f1"]:.6f}.', '', '```json',
                json.dumps({k:m[k] for k in ['class_order','classification_report','confusion_matrix','true_share','predicted_share']},indent=2), '```']
    for b in report['bundles']:
        if 'mandi_proxy' in b:
            m=b['mandi_proxy'];lines += ['', f'### {b["model"]} — Mandi exclusive proxy class report', '', '```json',json.dumps(m,indent=2),'```']
    lines += ['', '## Current deployable India national-B model', '',
        'These are three separate +6h measured-threshold classifiers. Rare positives make accuracy alone misleading; positive recall is included. They have no trained flood/storm/wildfire/air-quality hazard heads.', '',
        '| Target | Accuracy | Binary macro-F1 | Positive recall | Positive test hours |', '| --- | ---: | ---: | ---: | ---: |']
    for r in report['classifications']:
        if r['split']=='offline_phase/national/test/B':
            m=r['heldout'];positive=m['classification_report']['positive']
            lines.append(f'| {r["target"]} | {m["accuracy"]:.6f} | {m["macro_f1"]:.6f} | {positive["recall"]:.6f} | {positive["support"]} |')
    lines += ['', '## Complete model inventory (current tree and recovered archive)', '', '| Weight path / SHA-256 prefix | Objective / width | Status |', '| --- | --- | --- |']
    for item in report['inventory']:
        lines.append(f'| {item["path"]} / {item["sha256"][:12]} | {item.get("objective","unknown")} / {item.get("n_features","unknown")} | {item["status"]}: {item.get("reason", "native contract evaluated")} |')
    lines += ['', '## Errors and unavailable tests', '', *['- '+e for e in report['errors']], '',
        'Current models do not accept the archived 14-feature matrix. Regression models have continuous targets; current event models have twelve multilabel slots (two untrained); India classifiers predict three measured thresholds at +6h. No five-class label mapping is invented for them. Historical Indian 14-feature models were tested on weatherHistory only as transfer diagnostics, because their original split differs.', '',
        'Beijing observations.csv and source.zip were iCloud-only placeholders during this run. Their original native metrics are explicitly marked RECORDED_ONLY and were not freshly reproduced. Beijing regression weights were freshly evaluated against modeled Mandi six-hour outcomes. India regional experts with zero native routed test rows were tested separately on the full geographic holdout as cross-region transfer diagnostics. Rankings do not mix these evidence categories.', '',
        'Full machine-readable results and the console transcript are saved under the ignored results/model_tests directory. Source/model hashes allow identifying precisely what was evaluated. No model was selected or tuned using these new proxy scores.']
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of',default=datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat(),help='Last 30 complete UTC dates ending the day before this date')
    parser.add_argument('--legacy-ref',default='7b3c362^',help='Git ref containing original 14-feature pipeline')
    parser.add_argument('--cache',type=Path,default=ROOT/'results/model_tests/cache')
    parser.add_argument('--report',type=Path,default=ROOT/'docs/reference/MODEL_TEST_RESULTS.md')
    parser.add_argument('--offline',action='store_true',help='Require cached API responses; never replace with synthetic weather')
    parser.add_argument('--rain-3h-mm',type=float,default=30.,help='Experimental flood-proxy threshold; not a validated flood definition')
    args=parser.parse_args();args.cache=args.cache.resolve();args.cache.mkdir(parents=True,exist_ok=True)
    report=dict(as_of=args.as_of,inventory=discover(),errors=[],classifications=[],regressions=[],bundles=[])
    print(f'Found {len(report["inventory"])} current weight files. Reading archived training/preparation contracts... ',flush=True)
    legacy_cache=args.cache/'legacy';legacy_cache.mkdir(exist_ok=True)
    prep,groups,archived,contract=recover_legacy(args.legacy_ref,legacy_cache)
    report['legacy_contract']=contract;report['inventory'].extend(archived)
    mandi=None
    try:
        mandi,report['mandi']=mandi_data(args,args.cache)
        print(f'Downloaded/aligned {len(mandi)} Mandi hourly rows.',flush=True)
    except (OSError,ValueError,KeyError) as exc:
        report['mandi']={'status':'UNAVAILABLE','error':str(exc)};report['errors'].append('Mandi API: '+str(exc))
    classifications,bundles,split=legacy_tests(prep,groups,legacy_cache,mandi,args)
    report['classifications'].extend(classifications);report['bundles']=bundles;report['legacy_contract'].update(split)
    for label,operation in [('regression',lambda:native_regressors(report['inventory'],mandi)),
                            ('India classifiers',lambda:native_india_heads(report['inventory']))]:
        print('Evaluating '+label+' on native held-out data...',flush=True)
        try:
            value=operation()
            if label=='regression':
                regressions,datasets=value;report['regressions'].extend(regressions)
            else:report['classifications'].extend(value)
        except (OSError,ValueError,KeyError,xgb.core.XGBoostError) as exc:
            report['errors'].append(label+': '+str(exc))
    print('Evaluating current event-rule heads...',flush=True)
    try:report['classifications'].extend(native_event_heads({}))
    except (OSError,ValueError,KeyError,xgb.core.XGBoostError) as exc:report['errors'].append('Event heads: '+str(exc))
    fresh={r['sha256'] for r in report['classifications']+report['regressions'] if not r['evidence'].startswith('RECORDED_ONLY')}
    recorded={r['sha256'] for r in report['classifications']+report['regressions'] if r['evidence'].startswith('RECORDED_ONLY')}
    for item in report['inventory']:
        if item['sha256'] in fresh:
            item['status']='freshly_evaluated'
            evidence=sorted({r['evidence'] for r in report['classifications']+report['regressions'] if r['sha256']==item['sha256']})
            item['reason']='; '.join(evidence)+'; aliases share results by weight hash'
        elif item['sha256'] in recorded:
            item['status']='recorded_metrics_only'
            item['reason']='Original native raw data is cloud-only; saved confusion counts reproduced, weights hash-verified; no fresh heldout accuracy claim'
        else:item['reason']=item.get('reason','No matching native data/split/feature manifest; no fabricated accuracy')
    for item in report['inventory']:
        if item['origin']=='working_tree' and sha(ROOT/item['path'])!=item['sha256']:
            raise ValueError('Model weights changed during the read-only evaluation: '+item['path'])
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(markdown(report))
    results_path=args.cache.parent/'results.json';results_path.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    # Full console classification reports, as requested. The final concise table follows them.
    for r in report['classifications']:
        for key in ['heldout','mandi_proxy']:
            if key not in r:continue
            m=r[key];print(f'\n{r["model"]} {r["split"]} {key}: accuracy={m["accuracy"]:.6f} macro-F1={m["macro_f1"]:.6f}')
            print(json.dumps(m['classification_report'],indent=2));print('Confusion matrix:',m['confusion_matrix'])
    print('\nFINAL SUMMARY')
    print('Current weight files:',sum(i['origin']=='working_tree' for i in report['inventory']),
          'freshly evaluated by exact hash:',sum(i['origin']=='working_tree' and i['status']=='freshly_evaluated' for i in report['inventory']),
          'recorded metrics only:',sum(i['origin']=='working_tree' and i['status']=='recorded_metrics_only' for i in report['inventory']))
    print('NATIVE LEGACY BUNDLE RANKING (same original 14-feature split)')
    ranked=sorted([b for b in bundles if b['native_holdout']],key=lambda b:(-b['macro_f1'],-b['subset_accuracy'],b['model']))
    for rank,b in enumerate(ranked,1):print(rank,b['model'],f'exact_accuracy={b["subset_accuracy"]:.6f} macro_F1={b["macro_f1"]:.6f}')
    if ranked:print('BEST COMPARABLE BUNDLE:',ranked[0]['model'],'(identical-score ties are documented; rule reproduction only)')
    print('MANDI PROXY AGREEMENT (not true hazard accuracy)')
    for b in sorted([b for b in bundles if 'mandi_proxy' in b],key=lambda b:-b['mandi_proxy']['macro_f1']):
        m=b['mandi_proxy'];print(b['model'],f'accuracy={m["accuracy"]:.6f} macro_F1={m["macro_f1"]:.6f}',m['predicted_share'])
    print('Classification result rows:',len(report['classifications']),'regression result rows:',len(report['regressions']))
    print('Errors:',report['errors']);print('Report:',args.report);print('Machine-readable results:',results_path)
    return 1 if report['errors'] else 0


if __name__=='__main__':
    raise SystemExit(main())

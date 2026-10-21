"""Frozen-model Mandi evaluation and honestly timestamped dashboard replay.

No fitting, downloads, proxy event labels or sensor identities are created here.
The data is retrospective modeled weather/PM, not observed hazard ground truth.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ml.india_mandi.benchmark import arrays, metric
from ml.india_mandi.data import load_config
from ml.india_mandi.hybrid import DEFAULT_MODEL, Hybrid, blend
from ml.operational.contracts import UNITS
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.data import sha256
from ml.six_sensor_forecast.predict import predict as compact_predict
from server.dashboard import assess


def replay_records(frame: pd.DataFrame, manifest: dict) -> list[dict]:
    """Export the last 25 real API positions, retaining actual retrieval time."""
    if frame.location_id.nunique() != 1 or len(frame) < 25:
        raise ValueError('One Mandi location and 25 hourly snapshots required')
    recent = frame.sort_values('timestamp_utc').tail(25)
    times = pd.DatetimeIndex(recent.timestamp_utc)
    if times.tz is None or not (times[1:] - times[:-1] == pd.Timedelta(hours=1)).all():
        raise ValueError('Complete timezone-aware hourly replay required')
    if not np.isfinite(recent[RAW_SENSOR_COLUMNS].to_numpy(float)).all():
        raise ValueError('Complete six-channel replay required')
    retrieved = pd.Timestamp(manifest['retrieved_at_utc'])
    if retrieved.tzinfo is None or retrieved < times.max():
        raise ValueError('Actual source retrieval must follow replay observations')
    receipt = manifest['source_receipts'][-1]
    cells = {kind: [receipt[kind]['returned_latitude'], receipt[kind]['returned_longitude']]
             for kind in ('weather', 'air')}
    cell_id = json.dumps(cells, separators=(',', ':'))
    result = []
    for row in recent.itertuples(index=False):
        stamp = pd.Timestamp(row.timestamp_utc).isoformat()
        result.append(dict(node_id='mandi-api-grid', physical_site_id='NOT_A_PHYSICAL_STATION',
            registration_id='mandi-modeled-frozen-v1', latitude=manifest['requested_latitude'],
            longitude=manifest['requested_longitude'], elevation_m=None, elevation_datum='unknown',
            sensor_height_m=None, wind_height_m=None, native_interval_seconds=3600,
            source_class='modeled_grid', source_id='OpenMeteo_ECMWF_IFS_CAMS_retrospective',
            source_cell_id=cell_id, pressure_reference='grid_surface', timestamp_utc=stamp,
            valid_time_utc=stamp, available_at_utc=retrieved.isoformat(),
            sensor_model='MODELED_VALUES_NOT_SENSOR_HARDWARE',
            calibration_ids=dict.fromkeys(RAW_SENSOR_COLUMNS), units=UNITS.copy(),
            measurements={c: float(getattr(row, c)) for c in RAW_SENSOR_COLUMNS}))
    return result


def compare(predictions: dict[str, np.ndarray], truth: np.ndarray, current: np.ndarray) -> dict:
    """Score all candidates on exactly the same six-target cohort, in units."""
    if (truth.ndim != 2 or truth.shape[1] != 6 or current.shape != truth.shape
            or len(truth) < 2 or not np.isfinite(truth).all() or not np.isfinite(current).all()):
        raise ValueError('Matching finite six-target held-out rows required')
    result = {}
    for name, values in predictions.items():
        if values.shape != truth.shape or not np.isfinite(values).all():
            raise ValueError('All candidates must use identical finite target rows')
        result[name] = {c: metric(truth[:, j], values[:, j], current[:, j])
                        for j, c in enumerate(RAW_SENSOR_COLUMNS)}
    return result


def render(result: dict) -> str:
    """Write a submission-facing report with evidence limits beside results."""
    lines = ['# INDRA Mandi submission test', '', f"Executed: {result['executed_at_utc']}", '',
        '**Task:** six numerical measurements at +6h. **Evidence:** retrospective Mandi',
        'API/model grids, not physical station or hazard accuracy. No model was retrained',
        'and no ensemble weights were selected using this test.', '',
        f"Source: {result['source']['rows']:,} hourly positions, {result['source']['start']} to {result['source']['end']}.",
        f"Split counts: {result['rows_by_role']}. Six-hour targets are purged at split boundaries.",
        'The September/October test is reused research evidence, not a new untouched holdout.', '',
        '## All saved Mandi forecast candidates — test MAE', '',
        'Lower is better. Columns have different physical units and must not be averaged directly.', '',
        '| Model | T °C | RH percentage points | P hPa | PM2.5 µg/m³ | PM10 µg/m³ | Wind m/s |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for name, targets in result['metrics'].items():
        lines.append('| ' + name + ' | ' + ' | '.join(f'{targets[c]["mae"]:.4f}' for c in RAW_SENSOR_COLUMNS) + ' |')
    lines += ['', 'Full MAE/RMSE/R², persistence skill and row counts: [metrics.json](metrics.json).',
        'Classification accuracy/F1 do not apply to these continuous targets. The deployed',
        'hybrid is kept fixed even where an individual component has a lower test error.', '',
        '## Inputs, labels and learned weights', '',
        'Inputs, in order: temperature_c, relative_humidity_pct, pressure_hpa, pm25_ug_m3,',
        'pm10_ug_m3, wind_speed_mps. The hybrid derives 66 causal features from 25 hourly',
        'snapshots spanning 24 hours. Labels are the same six API values exactly +6h later.',
        'Examples with input, prediction and later API values are included in metrics.json.', '',
        'Learned MLP arrays/normalization, tree files and ridge arrays remain at their',
        'original paths. The active profile records their checksums; per-target prediction',
        'blend coefficients are recorded below. These are not hazard probabilities.', '',
        '| Target | Selected MLP | Neural | History XGBoost | Ridge |',
        '| --- | --- | ---: | ---: | ---: |']
    for target, head in result['blend_heads'].items():
        lines.append(f'| {target} | {head["neural"]} | ' + ' | '.join(f'{head["weights"][k]:.2f}' for k in ('neural', 'xgb_history', 'ridge_history')) + ' |')
    lines += ['', '## End-to-end Mandi replay', '',
        f"One historical node: `{result['dashboard']['node_id']}`; forecast status `{result['dashboard']['forecast_status']}`.",
        'The replay keeps actual source retrieval time, modeled source class, different',
        'weather/PM grid identities, no claimed calibration and grid-surface pressure.',
        'It never shifts old dates to today or invents nodes, rainfall labels or 15-minute readings.',
        'Forecast target times remain historical. Stale readings are explicitly marked.', '',
        '**Expected abstention:** current hazard rules reject modeled sources as field',
        'evidence. Their scores remain unavailable; this is a checked safety state, not',
        'measured hazard accuracy. The native 15-minute storm sequence cannot be evaluated',
        'from this hourly source. One grid cannot validate neighbour consensus or a spatial map.', '',
        '## What the submission can claim', '',
        '- Implemented six-channel hybrid forecasting, source/weight integrity checks and retrospective numerical comparison.',
        '- Tested local backend/frontend, explicit missing-history fallback, stale/cache handling and unavailable hazard states.',
        '- Separate engineered tests for anomaly, neighbour/radio simulation, spatial research and ERA5 pipeline execution.',
        '- No calibrated cloudburst/storm/snowstorm probability, flood/landslide skill, physical ESP32/RF execution or live six-sensor learning.', '',
        'Attribution: Open-Meteo, ECMWF IFS and Copernicus Atmosphere Monitoring Service (CAMS).',
        'Weather/air grids differ; underlying CAMS is coarser than its hourly API representation.',
        'Original issue-time data availability is unverified. This is a retrospective value forecast.', '']
    return '\n'.join(lines)


def run(config: Path, output: Path, replay_path: Path) -> dict:
    """Evaluate frozen weights and produce a separate report and local replay."""
    cfg = load_config(config)
    frame, features, labels, masks, manifest = arrays(cfg)
    engine = Hybrid()
    if (manifest['observations_sha256'] != engine.profile['source_sha256']
            or cfg['_config_sha256'] != engine.components.report['experiment_config_sha256']):
        raise ValueError('Matching frozen Mandi source and split configuration required')
    mask = masks['future_test']
    now = frame.loc[mask, RAW_SENSOR_COLUMNS]
    candidates = engine.components.predict(features.loc[mask], now)
    frozen = blend(candidates, engine.weights)
    shipping = engine.predict(frame[['location_id', 'timestamp_utc', *RAW_SENSOR_COLUMNS]])
    predictions = shipping.loc[mask, ['forecast_'+c for c in RAW_SENSOR_COLUMNS]].to_numpy()
    parity = float(np.max(np.abs(predictions-frozen)))
    if parity > 1e-5 or not shipping.loc[mask, 'status'].eq('HYBRID_READY').all():
        raise ValueError('Shipping hybrid parity/history check failed')
    compact = compact_predict(frame.loc[mask, ['location_id', 'timestamp_utc', *RAW_SENSOR_COLUMNS]],
                              engine.components.base, 'student')
    values = {'persistence': now.to_numpy(float),
        'compact_xgboost': compact[['forecast_'+c for c in RAW_SENSOR_COLUMNS]].to_numpy(),
        **candidates, 'active_hybrid': predictions}
    metrics = compare(values, labels.loc[mask].to_numpy(float), now.to_numpy(float))
    replay = replay_records(frame, manifest)
    nodes = assess(replay,model_dir=DEFAULT_MODEL)
    node = nodes[0]
    if (node['forecastStatus'] != 'HYBRID_READY' or node['sourceClass'] != 'modeled_grid'
            or any(not r['abstain'] or r['probability'] is not None for r in node['risks'].values())):
        raise ValueError('Mandi replay provenance or hazard-abstention check failed')
    indices = np.flatnonzero(mask)
    examples = []
    for pos in sorted(set([0, len(indices)//2, len(indices)-1])):
        i = indices[pos]
        examples.append(dict(input_time_utc=frame.timestamp_utc.iloc[i].isoformat(),
            target_time_utc=(frame.timestamp_utc.iloc[i]+pd.Timedelta(hours=6)).isoformat(),
            input={c: float(frame[c].iloc[i]) for c in RAW_SENSOR_COLUMNS},
            prediction=dict(zip(RAW_SENSOR_COLUMNS, predictions[pos].tolist())),
            later_api_value={c: float(labels[c].iloc[i]) for c in RAW_SENSOR_COLUMNS}))
    result = dict(schema_version='indra_mandi_submission_v1', executed_at_utc=datetime.now(timezone.utc).isoformat(),
        evaluation_code_sha256=sha256(Path(__file__)),
        profile=engine.profile['id'], model_profile_sha256=engine.profile_sha256,
        source=dict(kind=manifest['evidence_kind'], observations_sha256=manifest['observations_sha256'],
            rows=len(frame), start=frame.timestamp_utc.min().isoformat(), end=frame.timestamp_utc.max().isoformat()),
        rows_by_role={k: int(v.sum()) for k, v in masks.items()}, feature_names=features.columns.tolist(),
        test_status='REUSED_RETROSPECTIVE_MODELED_COHORT', field_validated=False,
        china_data_or_weights_used=False, trained_or_retuned=False, metrics=metrics,
        blend_heads=engine.weights['heads'], examples=examples, shipping_parity_max_absolute_error=parity,
        dashboard=dict(node_id=node['id'], forecast_status=node['forecastStatus'],
            history_rows=node['forecastHistoryRows'], stale=node['stale'], source_class=node['sourceClass'],
            observation_timestamp=node['timestamp'], forecast_timestamp=node['forecastTimestamp'],
            source_retrieved_at_utc=manifest['retrieved_at_utc'],
            risk_states={k: dict(abstain=r['abstain'], probability=r['probability'], state=r['assessment_state']) for k, r in node['risks'].items()}))
    output.mkdir(parents=True, exist_ok=True)
    replay_path.parent.mkdir(parents=True, exist_ok=True)
    replay_path.write_text(json.dumps(replay, indent=2, allow_nan=False)+'\n')
    (output/'metrics.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    (output/'REPORT.md').write_text(render(result))
    return result

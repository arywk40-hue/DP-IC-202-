"""Build the active numerical hybrid from saved India-only learned components."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
from ml.india_mandi.benchmark import arrays, metric  # noqa: E402
from ml.india_mandi.data import load_config  # noqa: E402
from ml.india_mandi.hybrid import Components, FAMILIES, Hybrid, blend, select_blend  # noqa: E402
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS  # noqa: E402
from ml.six_sensor_forecast.data import sha256  # noqa: E402


def build(path: Path) -> dict:
    """Select neural heads/blends on validation, freeze, then score reused tests."""
    cfg = json.loads(path.read_text())
    if cfg['schema_version'] != 'indra_mandi_hybrid_build_v1' or cfg['field_validated'] is not False:
        raise ValueError('Versioned unvalidated hybrid build required')
    output, reports = ROOT / cfg['models_output'], ROOT / cfg['reports_output']
    if output.exists():
        raise ValueError('Hybrid version exists; preserve it and choose a new version')
    base_cfg = load_config(ROOT / cfg['base_config'])
    frame, features, truth, masks, manifest = arrays(base_cfg)
    neural = {Path(p).name: ROOT / p for p in cfg['neural_candidates']}
    components = Components(ROOT / cfg['base_model'], neural, threads=cfg['threads'])
    if (components.report['source']['observations_sha256'] != manifest['observations_sha256']
            or components.report['experiment_config_sha256'] != base_cfg['_config_sha256']):
        raise ValueError('Saved components require their matching frozen source and split configuration')
    # Only complete train/validation/test cohorts enter component prediction.
    eligible = np.logical_or.reduce(list(masks.values()))
    predictions = components.predict(features.loc[eligible], frame.loc[eligible, RAW_SENSOR_COLUMNS])
    roles = {name: mask[eligible] for name, mask in masks.items()}
    y = truth.loc[eligible].to_numpy(float)
    current = frame.loc[eligible, RAW_SENSOR_COLUMNS].to_numpy(float)
    weights = select_blend({name: values[roles['validation']] for name, values in predictions.items()}, y[roles['validation']], cfg['simplex_step'])
    output.mkdir(parents=True)
    weights_path = output / 'ensemble_weights.json'
    weights_path.write_text(json.dumps(weights, indent=2, allow_nan=False) + '\n')
    model_files = [ROOT / cfg['base_model'] / p for p in ('training_report.json', 'ridge_report.json', 'temporal_ridge.npz')]
    model_files += [ROOT / cfg['base_model'] / item['teacher_file'] for item in components.report['models'].values()]
    model_files += [p / name for p in neural.values() for name in ('model.json', 'weights.npz')]
    profile = dict(schema_version='indra_mandi_hybrid_profile_v1', id=cfg['profile_id'],
        display_name='Mandi neural hybrid', sensors=RAW_SENSOR_COLUMNS, horizon_hours=6, history_hours=24,
        country='IN', evidence='MODELED_GRID_RETROSPECTIVE', field_validated=False, warmup_fallback=cfg['warmup_fallback'],
        base_model=cfg['base_model'], neural_candidates={p.name: str(p.relative_to(ROOT)) for p in neural.values()},
        weights_file=weights_path.name, weights_sha256=sha256(weights_path), threads=cfg['threads'],
        component_hashes={str(p.relative_to(ROOT)): sha256(p) for p in model_files},
        source_sha256=manifest['observations_sha256'], build_config_sha256=sha256(path),
        selection='VALIDATION_ONLY_NEURAL_ARCHITECTURE_AND_PER_TARGET_CONVEX_MAE_BLEND',
        forecast_task='SIX_NUMERICAL_MEASUREMENTS_NOT_HAZARD_EVENTS')
    (output / 'profile.json').write_text(json.dumps(profile, indent=2, allow_nan=False) + '\n')
    combined = blend(predictions, weights)
    results = {}
    for j, target in enumerate(RAW_SENSOR_COLUMNS):
        results[target] = {role: {name: metric(y[mask, j], values[mask, j], current[mask, j])
            for name, values in {**predictions, 'hybrid': combined, 'persistence': current}.items()} for role, mask in roles.items()}
    report = dict(profile_id=profile['id'], evidence=profile['evidence'], china_data_or_weights_used=False,
        rows_by_role={k: int(v.sum()) for k, v in roles.items()}, selection=weights, results=results,
        test_status='REUSED_RETROSPECTIVE_MODELED_BENCHMARK_NOT_UNTOUCHED_FIELD_TEST',
        exposure_note=base_cfg['test_exposure_note'], source_sha256=manifest['observations_sha256'], field_validated=False)
    # Verify the shipping predictor reproduces the artifact's batch calculation.
    deployed = Hybrid(output).predict(frame[['location_id', 'timestamp_utc', *RAW_SENSOR_COLUMNS]])
    actual = deployed.loc[eligible, ['forecast_' + c for c in RAW_SENSOR_COLUMNS]].to_numpy()
    report['shipping_parity_max_absolute_error'] = float(np.max(np.abs(actual - combined)))
    if report['shipping_parity_max_absolute_error'] > 1e-5:
        raise ValueError('Hybrid shipping/batch parity failed')
    reports.mkdir(parents=True, exist_ok=True)
    (reports / 'results.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    lines = ['# Active Mandi neural hybrid', '', 'Six numerical +6h endpoints from six channels and 24h causal history.',
        'Validation selects neural architecture and convex prediction coefficients. No existing learned weight is rewritten.',
        'Mandi-location modeled grids; this is not measured station or hazard validation. The test period was examined previously.', '',
        '| Target | Neural choice | Neural weight | XGB history weight | Ridge weight | Test hybrid MAE | Persistence MAE |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for target in RAW_SENSOR_COLUMNS:
        head, result = weights['heads'][target], results[target]['future_test']
        lines.append('| ' + target + ' | ' + head['neural'] + ' | ' + ' | '.join(f'{head["weights"][f]:.2f}' for f in FAMILIES)
            + f' | {result["hybrid"]["mae"]:.4f} | {result["persistence"]["mae"]:.4f} |')
    lines += ['', 'Warm-up uses clearly named persistence. Missing current channels produce unavailable forecasts.',
        'The backend selects exact hourly snapshots at the current observation phase; no interpolated or filled history is used.', '']
    (reports / 'REPORT.md').write_text('\n'.join(lines))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'configs/mandi_hybrid_forecast_v1.json')
    result = build(parser.parse_args().config)
    print(json.dumps({k: result[k] for k in ('profile_id', 'rows_by_role', 'shipping_parity_max_absolute_error', 'field_validated')}))

"""Config-driven local context pipeline; uncalibrated experimental risk outputs."""
from __future__ import annotations

import glob
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from storm_risk.anomaly.anomaly import fit_thresholds, flag_anomalies
from storm_risk.calibration.calibrate import apply_calibrator, fit_calibrator
from storm_risk.confirmation.neighbour import confirm_frame
from storm_risk.data.era5_loader import load_era5
from storm_risk.data.labels import read_events, read_labels
from storm_risk.data.splits import assign_split
from storm_risk.features.derived import derive
from storm_risk.features.lagged import build_lagged
from storm_risk.io.outputs import save_bundle, write_json
from storm_risk.models.ensemble import NAMES, base_scores, fit_base, fit_weights
from storm_risk.models.online import run_online
from storm_risk.settings import digest, resolve, snapshot
from storm_risk.validation.bootstrap import day_bootstrap
from storm_risk.validation.gate import evaluate_gate
from storm_risk.validation.metrics import metrics
from storm_risk.viz.heatmaps import export_heatmaps

SCORE_COLUMNS = [name + '_risk_uncal' for name in [*NAMES, 'ensemble']]


def empty_metrics() -> dict:
    """Keep the diagnostic report shape stable when evidence is unavailable."""
    return dict(total_samples=0, positive_samples=0, positive_events=0, base_rate=None,
        brier_score=None, reliability=None, resolution=None, uncertainty=None, binned_brier_score=None,
        binning_remainder=None, brier_skill_score=None, reliability_diagram=dict(bin_edges=[], bins=[], total_count=0))


def initial_report(cfg: dict, run_id: str) -> dict:
    """Describe evidence, settings and missing evidence before opening inputs."""
    return dict(schema_version='indra_storm_risk_report_v1', run_id=run_id, status='NOT_READY',
        evidence_kind=cfg['evidence_kind'], target=cfg['target'], calibrated=False, calibration_method='none',
        gate_failures=['PIPELINE_NOT_EVALUATED'], warnings=[], sample_counts={}, base_rates={}, metrics=empty_metrics(),
        base_model_metrics={}, confidence_intervals=None, ensemble_weights=None, model_artifact=None,
        fit_audit=[], sources={}, config=snapshot(cfg),
        settings_snapshot_sha256=hashlib.sha256(json.dumps(snapshot(cfg), sort_keys=True).encode()).hexdigest(),
        heatmaps=dict(features=[], frames=[]),
        online=dict(status='NOT_STARTED' if cfg['online']['enabled'] else 'DISABLED', calibrated=False), physical_sensor_channels_added=0,
        output_kind='EXPERIMENTAL_RISK_UNCALIBRATED', field_validation='NOT_ESTABLISHED')


def merge_outcomes(features: pd.DataFrame, labels: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    """Align configured lead times, purge split boundaries and shared event IDs."""
    frame = features.copy()
    frame['target_time'] = frame.time + pd.Timedelta(hours=cfg['target']['lead_hours'])
    frame['split'] = assign_split(frame.time, cfg)
    valid = frame.split.ne('outside') & frame.split.eq(assign_split(frame.target_time, cfg))
    purged = int((~valid).sum())
    frame = frame.loc[valid]
    truth = labels.rename(columns={'time': 'target_time', 'split': 'label_split'})
    frame = frame.merge(truth[['target_time', 'lat', 'lon', 'label', 'label_split', 'event_id', 'available_at']],
        on=['target_time', 'lat', 'lon'], how='left', validate='one_to_one')
    frame = frame.sort_values(['time', 'lat', 'lon']).reset_index(drop=True)
    known = frame.loc[frame.label.notna()].copy()
    memberships = known.assign(event_id=known.event_id.str.split('|')).explode('event_id').groupby('event_id').split.nunique()
    overlapping = set(memberships.loc[memberships > 1].index)
    crossed = frame.event_id.fillna('').map(lambda s: bool(set(s.split('|')) & overlapping))
    frame.loc[crossed, ['label', 'event_id']] = [np.nan, None]
    return frame, dict(purged_split_boundary_rows=purged, cross_split_event_ids_excluded=sorted(overlapping),
        unknown_outcome_rows=int(frame.label.isna().sum()), labeled_rows=int(frame.label.notna().sum()))


def test_diagnostics(test: pd.DataFrame, scores: np.ndarray, cfg: dict) -> tuple[dict | None, dict | None]:
    """Compute fixed-model test diagnostics without passing test rows to a fit."""
    if test.empty:
        return None, None
    result = metrics(test.label.to_numpy(int), scores, cfg)
    result['positive_events'] = len(set('|'.join(test.loc[test.label.eq(1), 'event_id']).split('|')) - {''})
    return result, day_bootstrap(test, scores, cfg)


def redact_synthetic(result: dict | None, intervals: dict | None) -> tuple[dict, dict | None]:
    """Do not publish synthetic diagnostic values as empirical model skill."""
    if result is None:
        return empty_metrics(), None
    out = {**result}
    for key in ('brier_score', 'reliability', 'resolution', 'uncertainty', 'binned_brier_score', 'binning_remainder', 'brier_skill_score'):
        out[key] = None
    out['diagnostics_status'] = 'WITHHELD_SYNTHETIC_ENGINEERING_ONLY'
    out['reliability_diagram'] = {**result['reliability_diagram'], 'bins': [dict(b, mean_forecast=None, observed_frequency=None) for b in result['reliability_diagram']['bins']]}
    if intervals:
        intervals = {**intervals, 'intervals': {k: dict(lower=None, upper=None, valid_resamples=v['valid_resamples']) for k, v in intervals['intervals'].items()},
            'diagnostics_status': 'WITHHELD_SYNTHETIC_ENGINEERING_ONLY'}
    return out, intervals


def run_pipeline(cfg: dict, run_id: str) -> tuple[Path, dict]:
    """Execute local inputs, independent-label models and feature-only UI exports."""
    if not 1 <= len(run_id) <= 96 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in run_id):
        raise ValueError('Bounded filesystem-safe run ID required')
    directory = resolve(cfg, cfg['paths']['outputs']) / run_id
    directory.mkdir(parents=True, exist_ok=False)
    (directory / 'heatmaps').mkdir()
    report = initial_report(cfg, run_id)
    scores = pd.DataFrame(columns=['time', 'lat', 'lon', *SCORE_COLUMNS, 'neighbour_confirmed', 'anomaly_flag', 'anomaly_features', 'split'])
    try:
        raw, report['sources']['era5'] = load_era5([Path(p) for p in sorted(glob.glob(str(resolve(cfg, cfg['paths']['era5_glob']))))], cfg)
        raw, derived = derive(raw)
        current = [*cfg['variables'], *derived]
        report['heatmaps'] = export_heatmaps(raw, current, directory / 'heatmaps', cfg)
        write_json(directory / 'heatmaps' / 'manifest.json', report['heatmaps'])
        frame, feature_names, history = build_lagged(raw, current, cfg)
        report['features'] = dict(names=feature_names, current_names=current, **history)
        events_path, labels_path = resolve(cfg, cfg['paths']['events']), resolve(cfg, cfg['paths']['labels'])
        if events_path.is_file() and labels_path.is_file():
            events, rejected_events = read_events(events_path, cfg)
            labels, rejected_labels, report['sources']['labels'] = read_labels(labels_path, events, cfg, grid=raw[['lat', 'lon']])
            report['sources']['events_sha256'] = digest(events_path)
            rejected_events.to_csv(directory / 'excluded_events.csv', index=False)
            rejected_labels.to_csv(directory / 'excluded_labels.csv', index=False)
            if len(rejected_events) or len(rejected_labels):
                report['warnings'].append(f'EXCLUDED_RECORDS events={len(rejected_events)} labels={len(rejected_labels)}')
        else:
            report['warnings'].append('CONFIRMED_LABEL_OR_EVENT_RECORD_FILE_MISSING')
            labels = pd.DataFrame(dict(time=pd.Series([], dtype='datetime64[ns, UTC]'), lat=pd.Series([], dtype=float),
                lon=pd.Series([], dtype=float), label=pd.Series([], dtype=float), split=pd.Series([], dtype=str),
                event_id=pd.Series([], dtype=str), available_at=pd.Series([], dtype='datetime64[ns, UTC]')))
        frame, report['outcomes'] = merge_outcomes(frame, labels, cfg)
        if frame.empty:
            raise ValueError('No complete causal rows within configured splits')
        thresholds = fit_thresholds(frame.loc[frame.split.eq('train')], current, cfg)
        flags = flag_anomalies(frame, thresholds, current)
        scores = frame[['time', 'lat', 'lon', 'split']].copy().join(flags)
        report['anomaly_thresholds'] = thresholds
        for name in SCORE_COLUMNS:
            scores[name] = np.nan
        scores['neighbour_confirmed'] = False
        for role in ('train', 'calib', 'test'):
            part = frame.loc[frame.split.eq(role) & frame.label.notna()]
            report['sample_counts'][role] = dict(total_rows=int(frame.split.eq(role).sum()), labeled_rows=len(part), positive_samples=int(part.label.eq(1).sum()), negative_samples=int(part.label.eq(0).sum()))
            report['base_rates'][role] = float(part.label.mean()) if len(part) else None
            if part.label.eq(1).sum() < cfg['labels']['min_positives']:
                report['warnings'].append('INSUFFICIENT_POSITIVES_' + role.upper())
        train = frame.loc[frame.split.eq('train') & frame.label.notna()]
        calib = frame.loc[frame.split.eq('calib') & frame.label.notna()]
        calib = calib.loc[calib.available_at.le(pd.Timestamp(cfg['time']['calib_end']))]
        test = frame.loc[frame.split.eq('test') & frame.label.notna()]
        report['metrics'].update(total_samples=len(test), positive_samples=int(test.label.eq(1).sum()),
            positive_events=len(set('|'.join(test.loc[test.label.eq(1), 'event_id']).split('|')) - {''}),
            base_rate=float(test.label.mean()) if len(test) else None)
        report['online'] = run_online(frame, feature_names, directory, cfg)
        if str(report['online']['status']).startswith('NOT_READY'):
            report['warnings'].append(report['online']['status'])
        if train.label.nunique() != 2 or calib.empty:
            raise ValueError('NOT_READY: confirmed training classes and calibration rows required')
        # Exclude training outcomes that were not available before validation.
        train = train.loc[train.available_at.le(pd.Timestamp(cfg['time']['train_end']))]
        bundle, warnings = fit_base(train, feature_names, cfg, report['fit_audit'])
        report['warnings'].extend(warnings)
        all_base = base_scores(bundle, frame, cfg)
        weights = fit_weights(all_base[calib.index], calib, cfg, report['fit_audit'])
        raw_ensemble = all_base @ weights
        calibrator, method, warnings = fit_calibrator(raw_ensemble[calib.index], calib, cfg, report['fit_audit'])
        report['warnings'].extend(warnings)
        mapped = apply_calibrator(calibrator, method, raw_ensemble)
        diagnostics, intervals = test_diagnostics(test, mapped[test.index], cfg)
        positive_events = diagnostics['positive_events'] if diagnostics else 0
        gate = evaluate_gate(diagnostics, intervals, positive_events, method, cfg)
        report.update(calibrated=gate['calibrated'], calibration_method=method, gate_failures=gate['failed_conditions'],
            gate=gate, ensemble_weights=dict(zip(NAMES, weights.tolist())))
        if cfg['evidence_kind'] == 'synthetic_engineering':
            diagnostics, intervals = redact_synthetic(diagnostics, intervals)
            report['warnings'].append('SYNTHETIC_ENGINEERING_ONLY_NO_EMPIRICAL_SKILL_REPORTED')
        report['metrics'], report['confidence_intervals'] = diagnostics or empty_metrics(), intervals
        for i, name in enumerate(NAMES):
            scores[name + '_risk_uncal'] = all_base[:, i]
            result = metrics(test.label.to_numpy(int), all_base[test.index, i], cfg) if len(test) else None
            report['base_model_metrics'][name] = redact_synthetic(result, None)[0] if cfg['evidence_kind'] == 'synthetic_engineering' else result
        # The gate applies only to the mapped ensemble, never the unmapped heads.
        output_name = 'ensemble_cal_prob' if gate['calibrated'] else 'ensemble_risk_uncal'
        scores = scores.drop(columns=['ensemble_risk_uncal'])
        scores[output_name] = mapped
        scores['ensemble_raw_risk_uncal'] = raw_ensemble
        scores['neighbour_confirmed'] = confirm_frame(frame, mapped, cfg)
        if not scores.anomaly_available.all():
            report['warnings'].append('ANOMALY_CLIMATOLOGY_MISSING_FOR_SOME_MONTHS')
        if not gate['calibrated']:
            report['warnings'].append('GATE_FAILED_OUTPUTS_REMAIN_EXPERIMENTAL_RISK_UNCALIBRATED')
        bundle.update(weights=weights, calibrator=calibrator, calibration_method=method, calibrated=gate['calibrated'],
            anomaly_thresholds=thresholds, target=cfg['target'], training_evidence=cfg['evidence_kind'])
        report['model_artifact'] = save_bundle(directory, bundle, cfg)
        report['status'] = 'COMPLETED_EXPERIMENTAL'
        report['output_kind'] = 'GATE_PASSED_MAPPED_ENSEMBLE' if gate['calibrated'] else 'EXPERIMENTAL_RISK_UNCALIBRATED'
    except (ValueError, KeyError, OSError) as exc:
        report['status'] = 'NOT_READY'
        report['warnings'].append(str(exc))
        report['gate_failures'] = list(dict.fromkeys([*report['gate_failures'], 'INPUT_OR_LABEL_EVIDENCE_INSUFFICIENT']))
    if len(scores):
        scores['time'] = scores.time.map(lambda t: t.isoformat() if hasattr(t, 'isoformat') else t)
    scores.to_csv(directory / 'scores.csv', index=False)
    report['score_columns'] = scores.columns.tolist()
    report['warnings'] = list(dict.fromkeys(report['warnings']))
    write_json(directory / 'report.json', report)
    return directory, report

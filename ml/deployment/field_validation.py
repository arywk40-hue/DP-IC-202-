"""Evaluate independent field records; fit calibration only before a fixed cutoff.

This produces evidence, never an automatic field-deployment approval.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, precision_score, recall_score, roc_auc_score

from ml.event_classifier.features import EVENT_NAMES, validate_observations
from ml.event_classifier.predict import EventPredictor
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.data import sha256
from ml.six_sensor_forecast.predict import predict


def utc_times(values):
    parsed = [pd.Timestamp(v) for v in values]
    if any(pd.isna(t) or t.tzinfo is None for t in parsed):
        raise ValueError('Every timestamp must include its source-confirmed timezone')
    return pd.to_datetime(parsed, utc=True)


def binary_metrics(truth, scores):
    truth, scores = np.asarray(truth), np.asarray(scores)
    if not len(truth):
        return None
    flag = scores >= .5
    return {'rows': len(truth), 'positives': int(truth.sum()),
            'brier': float(brier_score_loss(truth, scores)),
            'precision_at_0_5': float(precision_score(truth, flag, zero_division=0)),
            'recall_at_0_5': float(recall_score(truth, flag, zero_division=0)),
            'false_positives': int(((truth == 0) & flag).sum()),
            'false_negatives': int(((truth == 1) & ~flag).sum()),
            'auc': float(roc_auc_score(truth, scores)) if len(np.unique(truth)) == 2 else None}


def calibrate_and_evaluate(scores, labels, timestamps, cutoff, minimum_per_class=20):
    """No thresholds chosen on test data; absent labels remain unknown."""
    if minimum_per_class < 1:
        raise ValueError('minimum_per_class must be positive')
    scores, labels = np.asarray(scores, dtype=float), np.asarray(labels, dtype=float)
    if np.any(~np.isnan(labels) & ~np.isin(labels, [0, 1])):
        raise ValueError('Observed event labels must be 0, 1, or missing')
    valid = np.isfinite(scores) & np.isfinite(labels)
    if np.any(valid & ((scores < 0) | (scores > 1))):
        raise ValueError('Scores outside [0,1]')
    early = valid & (timestamps < cutoff)
    test = valid & (timestamps >= cutoff)
    counts = {'calibration_rows': int(early.sum()), 'test_rows': int(test.sum()),
              'calibration_positive': int((labels[early] == 1).sum()),
              'calibration_negative': int((labels[early] == 0).sum()),
              'test_positive': int((labels[test] == 1).sum()),
              'test_negative': int((labels[test] == 0).sum())}
    report = {'counts': counts, 'uncalibrated_test': binary_metrics(labels[test], scores[test]),
              'calibration': None, 'calibrated_test': None,
              'status': 'INSUFFICIENT_INDEPENDENT_LABELS'}
    if min(counts['calibration_positive'], counts['calibration_negative']) < minimum_per_class:
        return report
    def logit(x):
        p = np.clip(x, 1e-6, 1-1e-6)
        return np.log(p/(1-p)).reshape(-1, 1)
    model = LogisticRegression(C=1., solver='lbfgs', random_state=42)
    model.fit(logit(scores[early]), labels[early])
    report['calibration'] = {'method': 'logistic_on_score_logit',
                             'coefficient': float(model.coef_[0, 0]),
                             'intercept': float(model.intercept_[0]), 'clip': 1e-6}
    if test.any():
        calibrated = model.predict_proba(logit(scores[test]))[:, 1]
        report['calibrated_test'] = binary_metrics(labels[test], calibrated)
    if min(counts['test_positive'], counts['test_negative']) >= minimum_per_class:
        report['status'] = 'EVALUATED_REQUIRES_REVIEW'
    return report


def forecast_metrics(observations, forecasts, cutoff):
    left = observations.merge(forecasts.drop(columns=['status']), on=['location_id', 'timestamp_utc'], validate='one_to_one')
    right = observations.rename(columns={c: 'truth_' + c for c in RAW_SENSOR_COLUMNS})
    right = right.rename(columns={'timestamp_utc': 'forecast_timestamp_utc'})
    paired = left.merge(right, on=['location_id', 'forecast_timestamp_utc'], validate='many_to_one')
    paired = paired[paired.timestamp_utc >= cutoff]
    reports = {}
    for station, group in [('ALL', paired), *list(paired.groupby('location_id'))]:
        metrics = {}
        for name in RAW_SENSOR_COLUMNS:
            values = group[[name, 'forecast_' + name, 'truth_' + name]].to_numpy(dtype=float)
            values = values[np.isfinite(values).all(axis=1)]
            if not len(values):
                metrics[name] = {'pairs': 0}
                continue
            current, predicted, truth = values.T
            mae = float(np.abs(predicted-truth).mean())
            baseline = float(np.abs(current-truth).mean())
            metrics[name] = {'pairs': len(values), 'mae': mae,
                             'rmse': float(np.sqrt(np.square(predicted-truth).mean())),
                             'persistence_mae': baseline, 'beats_persistence_mae': mae < baseline}
        reports[str(station)] = metrics
    return reports


def evaluate(observations, labels, provenance, cutoff, forecast_dir, event_dir):
    if (provenance.get('independent_event_labels') is not True
            or provenance.get('timezone_verified') is not True
            or provenance.get('units_verified') is not True
            or provenance.get('pressure_reference') != 'station'
            or not provenance.get('observation_source') or not provenance.get('label_source')):
        raise ValueError('Provide independently observed labels and verified time/unit/pressure provenance')
    cutoff = utc_times([cutoff])[0]
    observations = observations.copy()
    labels = labels.copy()
    observations['timestamp_utc'] = utc_times(observations.timestamp_utc)
    labels['timestamp_utc'] = utc_times(labels.timestamp_utc)
    keys = ['timestamp_utc', 'location_id']
    if (set(labels.columns) != set(keys + EVENT_NAMES)
            or labels[keys].isna().any().any() or labels.duplicated(keys).any()):
        raise ValueError('Labels require unique station/timestamps and all event columns (unknowns blank)')
    for name in EVENT_NAMES:
        labels[name] = pd.to_numeric(labels[name], errors='raise')
        if not labels[name].dropna().isin([0, 1]).all():
            raise ValueError('Labels must be independently observed 0/1 or blank')
    observations = validate_observations(observations)
    labels['location_id'] = labels['location_id'].astype(str)
    predictor = EventPredictor(event_dir)
    scores = predictor.predict(observations)
    forecasts = predict(observations, forecast_dir, 'student')
    paired = scores.merge(labels, on=keys, suffixes=('_score', '_label'), validate='one_to_one')
    result = {'status': 'RESEARCH_EVIDENCE_REQUIRES_REVIEW', 'cutoff': str(cutoff),
              'provenance_declaration': provenance,
              'event_horizon_hours': 0, 'forecast_horizon_hours': 6,
              'event_rows_matched': len(paired), 'events': {},
              'forecasts': forecast_metrics(observations, forecasts, cutoff),
              'field_deployment_approved': False}
    for name, trained in zip(EVENT_NAMES, predictor.trained_mask):
        result['events'][name] = (calibrate_and_evaluate(
            paired[name+'_score'], paired[name+'_label'], paired.timestamp_utc, cutoff)
            if trained else {'status': 'UNTRAINED'})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observations', type=Path, required=True)
    parser.add_argument('--labels', type=Path, required=True)
    parser.add_argument('--provenance', type=Path, required=True)
    parser.add_argument('--test-start', required=True)
    parser.add_argument('--forecast-model', type=Path, default=Path('ml/models/uci_beijing_6h'))
    parser.add_argument('--event-model', type=Path, default=Path('ml/models/uci_beijing_event_rules_6sensor'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(pd.read_csv(args.observations), pd.read_csv(args.labels),
                      json.loads(args.provenance.read_text()), args.test_start,
                      args.forecast_model, args.event_model)
    report['sha256'] = {str(p): sha256(p) for p in [args.observations, args.labels, args.provenance,
        args.forecast_model/'training_report.json', args.event_model/'event_training_report.json']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(args.output)


if __name__ == '__main__':
    main()

"""Optional daily retrospective prequential SGD stream, separately reported."""
from __future__ import annotations

import hashlib
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

from ml.storm_risk.io.outputs import write_json
from ml.storm_risk.settings import utc


def run_online(frame: pd.DataFrame, features: list[str], directory: Path, cfg: dict) -> dict:
    """Durably record each day's scores before any mature batch update."""
    args = cfg['online']
    if not args['enabled']:
        return dict(status='DISABLED', calibrated=False)
    start = frame.time.min().floor('D')
    warmup_end = start + pd.Timedelta(days=args['warmup_days'])
    fit_end = warmup_end - pd.Timedelta(days=args['reference_days'])
    if warmup_end >= utc(cfg['time']['train_end']):
        return dict(status='NOT_READY_WARMUP_EXCEEDS_TRAIN', calibrated=False)
    train = frame.loc[frame.split.eq('train') & frame.time.lt(fit_end) & frame.available_at.le(fit_end) & frame.label.notna()]
    counts = train.label.value_counts()
    if counts.get(1, 0) < args['min_positives'] or counts.get(0, 0) < args['min_negatives']:
        return dict(status='NOT_READY_INSUFFICIENT_WARMUP_CLASSES', calibrated=False)
    scaler = StandardScaler().fit(train[features])
    scaler_hash = hashlib.sha256(np.r_[scaler.mean_, scaler.scale_].tobytes()).hexdigest()
    weights = {c: len(train) / (2 * counts[c]) for c in (0, 1)}
    model = SGDClassifier(loss='log_loss', random_state=cfg['models']['seed'], shuffle=False,
        learning_rate='constant', eta0=args['eta0'], alpha=args['alpha'])
    model.partial_fit(scaler.transform(train[features]), train.label.to_numpy(int), classes=[0, 1], sample_weight=train.label.map(weights).to_numpy())
    audit = [dict(action='INITIAL_FIT', rows=train.index.tolist(), maximum_time=train.time.max().isoformat(), role='train')]
    checkpoints = directory / 'checkpoints'
    checkpoints.mkdir()
    predictions, metrics_rows, pending, reference = [], [], {}, []
    baseline = None
    path = directory / 'online_scores.csv'
    trained_through = train.time.max()
    frozen = False
    for day, batch in frame.loc[frame.time.ge(fit_end)].groupby(frame.time.dt.floor('D'), sort=True):
        issue = max(day + pd.Timedelta(days=1), batch.time.max() + pd.Timedelta(hours=cfg['time']['feature_delay_hours']))
        frozen = frozen or day >= utc(cfg['time']['calib_end'])
        if trained_through >= day:
            raise ValueError('Online training crossed its prediction day')
        scores = model.predict_proba(scaler.transform(batch[features]))[:, 1]
        records = batch[['time', 'lat', 'lon', 'split']].copy()
        records['online_risk_uncal'], records['issued_at'] = scores, issue.isoformat()
        # Append/close makes prediction records inspectable before partial_fit.
        records.to_csv(path, mode='a', index=False, header=not path.exists())
        audit.append(dict(action='PREDICT_RECORDED', day=day.isoformat(), rows=batch.index.tolist(), trained_through=trained_through.isoformat()))
        for index, row, score in zip(batch.index, batch.to_dict('records'), scores):
            pending[index] = dict(row=row, score=float(score), x=batch.loc[index, features].to_numpy(float), day=day)
        predictions.extend(records.to_dict('records'))
        mature = [(i, e) for i, e in pending.items() if pd.notna(e['row']['label']) and e['row']['available_at'] <= issue]
        for i, entry in mature:
            reference.append(dict(time=entry['row']['time'], label=int(entry['row']['label']), score=entry['score'],
                split=entry['row']['split'], reference=entry['day'] < warmup_end))
            del pending[i]
        if baseline is None and day >= warmup_end:
            initial = [r for r in reference if r['reference']]
            outstanding = any(e['day'] < warmup_end and pd.notna(e['row']['label']) for e in pending.values())
            if len(initial) >= args['min_reference_rows'] and not outstanding:
                baseline = float(brier_score_loss([r['label'] for r in initial], [r['score'] for r in initial]))
        end = max((r['time'] for r in reference), default=day)
        rolling = [r for r in reference if r['time'] > end - pd.Timedelta(days=args['rolling_days']) and (not frozen or r['split'] == 'test')]
        y, s = [r['label'] for r in rolling], [r['score'] for r in rolling]
        brier = float(brier_score_loss(y, s)) if y else None
        auc = float(roc_auc_score(y, s)) if len(set(y)) == 2 else None
        synthetic = cfg['evidence_kind'] == 'synthetic_engineering'
        metrics_rows.append(dict(date=day.date().isoformat(), as_of=issue.isoformat(), rows=len(y),
            brier_score=None if synthetic else brier, roc_auc=None if synthetic else auc,
            baseline_brier=None if synthetic else baseline,
            drift_warning=bool(brier is not None and baseline is not None and brier > baseline + args['drift_brier_increase']),
            evidence_kind=cfg['evidence_kind'], diagnostics_status='WITHHELD_SYNTHETIC_ENGINEERING' if synthetic else 'PREQUENTIAL', calibrated=False))
        eligible = [(i, e) for i, e in mature if e['row']['split'] != 'test'] if not frozen else []
        if eligible:
            x = np.asarray([e['x'] for _, e in eligible])
            y = np.asarray([e['row']['label'] for _, e in eligible], int)
            model.partial_fit(scaler.transform(pd.DataFrame(x, columns=features)), y, sample_weight=np.array([weights[c] for c in y]))
            trained_through = max(trained_through, max(e['row']['time'] for _, e in eligible))
            audit.append(dict(action='UPDATE', day=day.isoformat(), rows=[i for i, _ in eligible], role='non_test'))
        if hashlib.sha256(np.r_[scaler.mean_, scaler.scale_].tobytes()).hexdigest() != scaler_hash:
            raise ValueError('Warm-up scaler changed')
        if ((day - fit_end.floor('D')).days + 1) % args['checkpoint_days'] == 0:
            joblib.dump(dict(model=model, scaler=scaler, class_weights=weights, pending=pending, predictions=predictions,
                audit=audit, config=cfg, frozen=frozen), checkpoints / (day.strftime('%Y-%m-%d') + '.joblib'), compress=3)
    pd.DataFrame(metrics_rows).to_csv(directory / 'online_metrics.csv', index=False)
    joblib.dump(dict(model=model, scaler=scaler, class_weights=weights, pending=pending, predictions=predictions,
        audit=audit, config=cfg, frozen=frozen), checkpoints / (day.strftime('%Y-%m-%d') + '_final.joblib'), compress=3)
    write_json(directory / 'online_audit.json', dict(events=audit, scaler_sha256=scaler_hash))
    return dict(status='COMPLETED_RETROSPECTIVE_PREQUENTIAL_REPLAY', calibrated=False, predictions=len(predictions),
        updates=sum(a['action'] == 'UPDATE' for a in audit), evidence_kind=cfg['evidence_kind'],
        frozen_before_test=True, pending_labels=len(pending), scaler_sha256=scaler_hash)

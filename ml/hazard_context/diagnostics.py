"""Validation operating curves, frozen choices; no test-set threshold optimization."""
import numpy as np
from xgboost import XGBClassifier

from ml.datasets.registry import digest
from ml.hazard_context.episodes import evaluate
from ml.india_sensor.thresholds import decision_metrics


def operating_curve(frame,head,mask,horizon_hours,warning_only=False,cadence_seconds=3600):
    valid=np.asarray(mask,bool)&frame.label.notna().to_numpy()
    if not valid.any():return []
    if digest(head['artifact'])!=head['sha256']:raise ValueError('Changed selected research artifact')
    model=XGBClassifier();model.load_model(head['artifact'])
    selected=frame.loc[valid].copy();scores=model.predict_proba(selected[head['features']].to_numpy('float32'))[:,1]
    from pandas import Timedelta
    selected['issue_time_utc']=selected.timestamp_utc;selected['target_time_utc']=selected.timestamp_utc+Timedelta(hours=horizon_hours);selected['score']=scores
    thresholds=np.unique(np.r_[np.quantile(scores,np.linspace(0,1,41)),1.] if warning_only else np.quantile(scores,np.linspace(0,1,41)))
    return [{'raw_cutoff':float(t),'hourly':decision_metrics(selected.label,scores,t),'episodes':evaluate(selected,float(t),cadence_seconds,warning_only)} for t in thresholds]


def select_warning_threshold(curve,policy):
    """Freeze a raw decision cutoff from validation episode metrics only."""
    budget=policy['max_false_alert_episodes_per_100_monitored_site_days']
    events=policy['minimum_validation_positive_event_groups']
    days=policy['minimum_validation_negative_site_days']
    if not all(np.isfinite(v) and v>=0 for v in [budget,events,days]) or events<1 or days<=0:raise ValueError('Invalid warning threshold support/budget')
    eligible=[]
    for row in curve:
        e=row['episodes'];rate=e['false_alert_episodes_per_100_monitored_site_days']
        if e['positive_event_groups']>=events and e['eligible_monitored_negative_site_days']>=days and rate is not None and rate<=budget and e['event_recall'] is not None:
            eligible.append(row)
    chosen=max(eligible,key=lambda r:(r['episodes']['event_recall'],-r['episodes']['false_alert_episodes_per_100_monitored_site_days'],r['raw_cutoff'])) if eligible else None
    return {'raw_threshold':chosen['raw_cutoff'] if chosen else None,'status':'VALIDATION_SELECTED' if chosen else 'NO_SUPPORTED_CUTOFF_WITHIN_BUDGET',
            'policy':policy,'validation_episodes':chosen['episodes'] if chosen else None,
            'candidate_cutoffs':len(curve),'test_retuning':False}

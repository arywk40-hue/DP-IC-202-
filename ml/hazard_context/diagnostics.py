"""Validation operating curves, frozen choices; no test-set threshold optimization."""
import numpy as np
from xgboost import XGBClassifier

from ml.datasets.registry import digest
from ml.hazard_context.episodes import evaluate
from ml.india_sensor.thresholds import decision_metrics


def operating_curve(frame,head,mask,horizon_hours):
    valid=np.asarray(mask,bool)&frame.label.notna().to_numpy()
    if not valid.any():return []
    if digest(head['artifact'])!=head['sha256']:raise ValueError('Changed selected research artifact')
    model=XGBClassifier();model.load_model(head['artifact'])
    selected=frame.loc[valid].copy();scores=model.predict_proba(selected[head['features']].to_numpy('float32'))[:,1]
    from pandas import Timedelta
    selected['issue_time_utc']=selected.timestamp_utc;selected['target_time_utc']=selected.timestamp_utc+Timedelta(hours=horizon_hours);selected['score']=scores
    thresholds=np.unique(np.quantile(scores,np.linspace(0,1,41)))
    return [{'raw_cutoff':float(t),'hourly':decision_metrics(selected.label,scores,t),'episodes':evaluate(selected,float(t))} for t in thresholds]

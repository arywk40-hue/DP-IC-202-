# Experimental risk scores, not calibrated probabilities. No predictive accuracy
# is claimed until evaluated on held-out independently observed events.
"""Daily prequential SGD research replay with delayed labels and fixed scaling."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import platform

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

from ml.hazard_context.online_data import FEATURES, MAX_ROWS, utc
from ml.six_sensor_forecast.data import sha256

SCHEMA = "indra_online_storm_research_v1"
DEFAULT = dict(warmup_days=30, reference_days=7, rolling_days=30, min_positives=10,
    min_negatives=10, min_reference_rows=24, drift_brier_increase=.05,
    checkpoint_days=30, eta0=.01, alpha=.0001, seed=42, holdout_start=None)


def validate_config(config):
    """Freeze bounded operational choices before inspecting replay outcomes."""
    cfg={**DEFAULT,**config}
    if set(cfg)!=set(DEFAULT):
        raise ValueError("Unknown online configuration field")
    bounds={"warmup_days":(3,366),"reference_days":(1,90),"rolling_days":(1,366),
        "min_positives":(1,10000),"min_negatives":(1,10000),"min_reference_rows":(2,10000),"checkpoint_days":(1,366)}
    for key,(low,high) in bounds.items():
        if type(cfg[key]) is not int or not low<=cfg[key]<=high:
            raise ValueError("Invalid bounded online setting: "+key)
    if cfg["reference_days"]>=cfg["warmup_days"]:
        raise ValueError("Reserve a smaller reference tail within warm-up")
    for key,low,high in (("eta0",0,.1),("alpha",0,1),("drift_brier_increase",0,1)):
        if not np.isfinite(cfg[key]) or not low<cfg[key]<=high:
            raise ValueError("Invalid positive online setting: "+key)
    if cfg["holdout_start"] is not None:
        h=utc(cfg["holdout_start"])
        if h!=h.floor("D"):
            raise ValueError("Holdout must start at a UTC day boundary")
        cfg["holdout_start"]=h.isoformat()
    return cfg


def scaler_digest(scaler):
    """Fingerprint the fitted scaler so later accidental refits are rejected."""
    h=hashlib.sha256()
    for value in (scaler.mean_,scaler.scale_,scaler.var_,np.atleast_1d(scaler.n_samples_seen_)):
        h.update(np.asarray(value).tobytes())
    return h.hexdigest()


def mature_labels(labels, now):
    """Reveal only binary outcomes whose stated availability has passed."""
    return labels.loc[labels.available_at.le(now)&labels.label.isin([0,1])]


@dataclass
class OnlineState:
    """Serializable learner, immutable predictions and delayed-label backlog."""
    model: SGDClassifier
    scaler: StandardScaler
    config: dict
    target: str
    label_role: str
    train_end: pd.Timestamp
    warmup_end: pd.Timestamp
    class_weights: dict
    scaler_sha256: str
    trained_through: pd.Timestamp
    trained_labels_available_through: pd.Timestamp
    version: int = 1
    last_day: pd.Timestamp | None = None
    last_issue: pd.Timestamp | None = None
    frozen: bool = False
    pending: dict = field(default_factory=dict)
    predictions: list = field(default_factory=list)
    scored: list = field(default_factory=list)
    metrics: list = field(default_factory=list)
    audit: list = field(default_factory=list)
    baseline_brier: float | None = None
    baseline_established_at: str | None = None


def initialize(features, labels, config, *, target, label_role):
    """Fit scaler/first SGD pass only on mature initial training outcomes."""
    cfg=validate_config(config)
    if target not in {"cloudburst","snowstorm"} or label_role not in {"satellite_proxy","observed_event_unverified","synthetic_test"}:
        raise ValueError("Explicit supported research target/evidence required")
    start=features.time.min().floor("D")
    warmup_end=start+pd.Timedelta(days=cfg["warmup_days"])
    train_end=warmup_end-pd.Timedelta(days=cfg["reference_days"])
    if cfg["holdout_start"] is not None and utc(cfg["holdout_start"])<warmup_end:
        raise ValueError("Frozen holdout must follow warm-up/reference")
    known=mature_labels(labels,train_end)
    eligible=features.loc[(features.time<train_end)&(features.feature_available_at<=train_end)]
    training=eligible.merge(known[["key","label","available_at"]],on="key",validate="one_to_one")
    training=training.loc[np.isfinite(training[FEATURES].to_numpy(float)).all(axis=1)]
    counts=training.label.value_counts()
    if counts.get(1,0)<cfg["min_positives"] or counts.get(0,0)<cfg["min_negatives"]:
        raise ValueError(f"NOT_READY: insufficient mature warm-up classes: positives={counts.get(1,0)}, negatives={counts.get(0,0)}")
    weights={c:len(training)/(2*int(counts[c])) for c in (0,1)}
    scaler=StandardScaler().fit(training[FEATURES].to_numpy(float))
    model=SGDClassifier(loss="log_loss",learning_rate="constant",eta0=cfg["eta0"],
        alpha=cfg["alpha"],random_state=cfg["seed"],shuffle=False)
    model.partial_fit(scaler.transform(training[FEATURES].to_numpy(float)),training.label.to_numpy(int),
        classes=np.array([0,1]),sample_weight=training.label.map(weights).to_numpy(float))
    state=OnlineState(model,scaler,cfg,target,label_role,train_end,warmup_end,weights,scaler_digest(scaler),
        training.time.max(),training.available_at.max())
    state.audit.append(dict(action="INITIAL_FIT",at=train_end.isoformat(),rows=len(training),
        maximum_feature_time=state.trained_through.isoformat(),maximum_label_available_at=state.trained_labels_available_through.isoformat(),
        class_counts={str(k):int(v) for k,v in counts.items()},scaler_sha256=state.scaler_sha256))
    return state


def predict_day(state, batch, day, issue):
    """Predict an entire observation day before any of its update labels enter."""
    if scaler_digest(state.scaler)!=state.scaler_sha256:
        raise ValueError("Fixed scaler changed after warm-up")
    if state.trained_through>=day:
        raise ValueError("Future/current-day observations entered training before prediction")
    if state.trained_labels_available_through>issue:
        raise ValueError("Model has seen unavailable labels")
    valid=np.isfinite(batch[FEATURES].to_numpy(float)).all(axis=1)&batch.feature_available_at.le(issue).to_numpy()
    values=np.full(len(batch),np.nan)
    if valid.any():
        values[valid]=state.model.predict_proba(state.scaler.transform(batch.loc[valid,FEATURES].to_numpy(float)))[:,1]
    records=[]
    role="FROZEN_HOLDOUT" if state.frozen else "PREQUENTIAL_REFERENCE" if day<state.warmup_end else "PREQUENTIAL_ADAPTIVE"
    for i,(_,row) in enumerate(batch.iterrows()):
        record=dict(key=row["key"],time=row.time.isoformat(),lat=float(row.lat),lon=float(row.lon),
            issued_at=issue.isoformat(),model_version=state.version,trained_through=state.trained_through.isoformat(),
            evaluation_role=role,label_role=state.label_role,
            status="EXPERIMENTAL_UNCALIBRATED" if valid[i] else "MISSING_OR_UNAVAILABLE_FEATURES",
            **{state.target+"_risk_uncal":float(values[i]) if valid[i] else None})
        records.append(record)
        if valid[i]:
            state.pending[row["key"]]=dict(record=record,x=row[FEATURES].to_numpy(float))
    state.predictions.extend(records)
    state.audit.append(dict(action="PREDICT",day=day.isoformat(),at=issue.isoformat(),rows=len(batch),
        model_version=state.version,maximum_trained_feature_time=state.trained_through.isoformat(),scaler_sha256=state.scaler_sha256))
    return records


def reveal_and_update(state, labels, issue, day):
    """Score stored predictions first, then update once on mature unseen labels."""
    eligible=mature_labels(labels.loc[labels.key.isin(state.pending)],issue)
    revealed=[]
    for label in eligible.itertuples(index=False):
        if label.key not in state.pending:
            continue
        entry=state.pending.pop(label.key)
        record=entry["record"]
        state.scored.append(dict(key=label.key,time=record["time"],issued_at=record["issued_at"],
            label=int(label.label),score=record[state.target+"_risk_uncal"],
            label_available_at=label.available_at.isoformat(),evaluation_role=record["evaluation_role"]))
        revealed.append((label,entry))
    if revealed:
        state.audit.append(dict(action="SCORE_STORED_PREDICTIONS",day=day.isoformat(),at=issue.isoformat(),rows=len(revealed),model_version=state.version))
    if revealed and not state.frozen:
        revealed.sort(key=lambda pair:(pair[0].time,pair[0].key))
        x=np.asarray([e["x"] for _,e in revealed],dtype=float)
        y=np.asarray([r.label for r,_ in revealed],dtype=int)
        state.model.partial_fit(state.scaler.transform(x),y,sample_weight=np.asarray([state.class_weights[int(c)] for c in y]))
        state.version+=1
        state.trained_through=max(state.trained_through,max(r.time for r,_ in revealed))
        state.trained_labels_available_through=max(state.trained_labels_available_through,max(r.available_at for r,_ in revealed))
        state.audit.append(dict(action="UPDATE",day=day.isoformat(),at=issue.isoformat(),rows=len(revealed),
            model_version=state.version,maximum_label_available_at=max(r.available_at for r,_ in revealed).isoformat(),
            maximum_feature_time=max(r.time for r,_ in revealed).isoformat(),scaler_sha256=state.scaler_sha256))


def rolling_metrics(state, issue, day):
    """Use unweighted, stored out-of-sample scores; undefined AUC stays null."""
    scored=pd.DataFrame(state.scored)
    reference=[r for r in state.scored if r["evaluation_role"]=="PREQUENTIAL_REFERENCE"]
    expected=sum(r["evaluation_role"]=="PREQUENTIAL_REFERENCE" and r["status"]=="EXPERIMENTAL_UNCALIBRATED" for r in state.predictions)
    if (state.baseline_brier is None and day+pd.Timedelta(days=1)>=state.warmup_end
            and len(reference)==expected and len(reference)>=state.config["min_reference_rows"]):
        state.baseline_brier=float(brier_score_loss([r["label"] for r in reference],[r["score"] for r in reference]))
        state.baseline_established_at=issue.isoformat()
    if state.frozen and not scored.empty:
        scored=scored.loc[scored.evaluation_role.eq("FROZEN_HOLDOUT")]
    window_end=None
    if not scored.empty:
        scored["time"]=pd.to_datetime(scored.time,utc=True)
        # The window ends at the newest *mature scored outcome*. With delayed
        # labels it is not falsely described as the latest live weather month.
        window_end=scored.time.max()
        scored=scored.loc[scored.time>window_end-pd.Timedelta(days=state.config["rolling_days"])]
    count=len(scored)
    brier=float(brier_score_loss(scored.label,scored.score)) if count else None
    auc=float(roc_auc_score(scored.label,scored.score)) if count and scored.label.nunique()==2 else None
    record=dict(date=day.date().isoformat(),as_of_utc=issue.isoformat(),window_end_utc=window_end.isoformat() if window_end is not None else None,
        window_days=state.config["rolling_days"],rows=count,positives=int(scored.label.sum()) if count else 0,
        brier_score=brier,roc_auc=auc,auc_status="AVAILABLE" if auc is not None else "NOT_EVALUATED_NEEDS_BOTH_CLASSES",
        reference_brier=state.baseline_brier,reference_established_at=state.baseline_established_at,
        reference_status="READY_PREQUENTIAL_REFERENCE" if state.baseline_brier is not None else "WAITING_FOR_COMPLETE_REFERENCE_LABELS",
        drift_warning=bool(brier is not None and state.baseline_brier is not None and brier-state.baseline_brier>state.config["drift_brier_increase"]),
        label_role=state.label_role,empirical_accuracy_claimed=False,calibrated=False,
        evaluation_role="FROZEN_HOLDOUT" if state.frozen else "PREQUENTIAL_ADAPTIVE")
    state.metrics.append(record)
    return record


def process_day(state, batch, labels, day, *, before_update=None):
    """Advance one UTC observation day, conserving delayed-label causality."""
    day=utc(day)
    if day!=day.floor("D") or day<state.train_end or state.last_day is not None and day!=state.last_day+pd.Timedelta(days=1):
        raise ValueError("Process each consecutive UTC day once in order")
    if not batch.empty and not batch.time.dt.floor("D").eq(day).all():
        raise ValueError("A prediction batch may contain only its observation day")
    if batch.key.duplicated().any() or any(k in state.pending for k in batch.key):
        raise ValueError("Duplicate prediction identities")
    if len(state.predictions)+len(batch)>MAX_ROWS:
        raise ValueError("Research replay row budget exceeded")
    issue=max(day+pd.Timedelta(days=1),state.last_issue or day)
    if not batch.empty:
        issue=max(issue,batch.feature_available_at.max())
    if state.config["holdout_start"] is not None and day>=utc(state.config["holdout_start"]):
        state.frozen=True
    records=predict_day(state,batch,day,issue)
    if before_update:
        before_update(records)  # durable CSV append happens before partial_fit
    reveal_and_update(state,labels,issue,day)
    metric=rolling_metrics(state,issue,day)
    state.last_day,state.last_issue=day,issue
    return records,metric


def save_checkpoint(state, path):
    """Save complete resumable research state and a checksum/version receipt."""
    path=Path(path)
    if path.exists() or path.with_suffix(".manifest.json").exists():
        raise ValueError("Checkpoint path already exists")
    path.parent.mkdir(parents=True,exist_ok=True)
    joblib.dump(state,path,compress=3)
    manifest=dict(schema_version=SCHEMA,sha256=sha256(path),python=platform.python_version(),sklearn=sklearn.__version__,
        target=state.target,label_role=state.label_role,model_version=state.version,scaler_sha256=state.scaler_sha256,
        last_day=state.last_day.isoformat() if state.last_day is not None else None,
        deployment_approved=False,empirical_accuracy_claimed=False,calibrated=False)
    path.with_suffix(".manifest.json").write_text(json.dumps(manifest,indent=2,allow_nan=False)+"\n")
    return manifest


def load_checkpoint(path):
    """Load only an operator-trusted local joblib checkpoint; never web uploads."""
    path=Path(path)
    manifest=json.loads(path.with_suffix(".manifest.json").read_text())
    if manifest.get("schema_version")!=SCHEMA or sha256(path)!=manifest["sha256"] or manifest["sklearn"]!=sklearn.__version__:
        raise ValueError("Checkpoint version/hash mismatch")
    state=joblib.load(path)
    if not isinstance(state,OnlineState) or scaler_digest(state.scaler)!=manifest["scaler_sha256"]:
        raise ValueError("Checkpoint state/scaler mismatch")
    return state

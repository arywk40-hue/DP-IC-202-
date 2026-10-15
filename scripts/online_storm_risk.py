# Experimental risk scores, not calibrated probabilities. No predictive accuracy
# is claimed until evaluated on held-out independently observed events.
"""Run/resume a daily ERA5-context SGD research replay with delayed labels."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from ml.hazard_context.online import (  # noqa: E402
    SCHEMA, initialize, load_checkpoint, process_day, save_checkpoint, validate_config)
from ml.hazard_context.online_data import load_era5, read_labels, utc  # noqa: E402
from ml.six_sensor_forecast.data import sha256  # noqa: E402


def append_predictions(path, records):
    """Flush immutable issued scores to disk before their learning update."""
    if not records:
        return
    exists=path.exists()
    with path.open("a",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(records[0]))
        if not exists:
            writer.writeheader()
        writer.writerows(records)
        handle.flush()


def run_replay(era5, labels_path, output, *, target, label_role, feature_delay_hours,
               label_delay_hours=None, settings=None, until=None, resume=None):
    """Replay available inputs; preserve pending labels and optimizer on resume."""
    cfg=validate_config(settings or {})
    labels,label_receipt=read_labels(labels_path,target=target,label_role=label_role,assumed_delay_hours=label_delay_hours)
    sites=list(labels[["lat","lon"]].drop_duplicates().itertuples(index=False,name=None))
    features,source_receipt=load_era5(era5,sites,feature_delay_hours=feature_delay_hours)
    output=Path(output)
    if output.exists():
        raise ValueError("Choose a new private output directory; resume writes a new run folder")
    state=load_checkpoint(resume) if resume else initialize(features,labels,cfg,target=target,label_role=label_role)
    if state.target!=target or state.label_role!=label_role or state.config!=cfg:
        raise ValueError("Resume target, evidence and frozen configuration must match")
    start=state.last_day+pd.Timedelta(days=1) if state.last_day is not None else state.train_end
    end=utc(until) if until is not None else features.time.max().floor("D")+pd.Timedelta(days=1)
    if end!=end.floor("D") or end<=start or (end-start).days>3660:
        raise ValueError("Use a later exclusive UTC midnight within a bounded replay interval")
    output.mkdir(parents=True)
    predictions_path=output/"predictions.csv"
    append_predictions(predictions_path,state.predictions)
    checkpoints=[]
    for day in pd.date_range(start,end-pd.Timedelta(days=1),freq="D"):
        batch=features.loc[features.time.dt.floor("D").eq(day)]
        _,metrics=process_day(state,batch,labels,day,before_update=lambda rows:append_predictions(predictions_path,rows))
        elapsed=(day+pd.Timedelta(days=1)-state.train_end).days
        if elapsed%cfg["checkpoint_days"]==0:
            checkpoint=output/f"{target}_{day.date().isoformat()}.joblib"
            checkpoints.append(dict(file=checkpoint.name,**save_checkpoint(state,checkpoint)))
        if metrics["drift_warning"]:
            print(f"DRIFT WARNING {metrics['date']}: rolling Brier increased beyond {cfg['drift_brier_increase']}",flush=True)
    checkpoint=output/f"{target}_{state.last_day.date().isoformat()}_final.joblib"
    checkpoints.append(dict(file=checkpoint.name,**save_checkpoint(state,checkpoint)))
    pd.DataFrame(state.metrics).to_csv(output/"metrics.csv",index=False)
    pd.DataFrame(state.scored).rename(columns={"score":target+"_risk_uncal"}).to_csv(output/"scored_predictions.csv",index=False)
    with (output/"audit.jsonl").open("w") as handle:
        for event in state.audit:
            handle.write(json.dumps(event,allow_nan=False)+"\n")
    receipt=dict(schema_version=SCHEMA,status="RESEARCH_REPLAY_COMPLETED_UNCALIBRATED",target=target,label_role=label_role,
        context=source_receipt,labels=label_receipt,config=cfg,checkpoints=checkpoints,
        resume_parent_sha256=sha256(resume) if resume else None,
        prediction_rows=len(state.predictions),mature_scored_rows=len(state.scored),pending_labels=len(state.pending),
        update_batches=sum(e["action"]=="UPDATE" for e in state.audit),model_version=state.version,
        fixed_class_weights=state.class_weights,fixed_scaler_sha256=state.scaler_sha256,
        last_day=state.last_day.isoformat(),baseline_brier=state.baseline_brier,
        deployment_approved=False,calibrated=False,empirical_accuracy_claimed=False,
        as_issued_weather_availability_verified=False,task="RETROSPECTIVE_CONTEMPORANEOUS_CLASSIFICATION_NOT_ADVANCE_WARNING",
        six_sensor_product_changed=False,background_live_service=False,
        limitations=["IMERG threshold labels remain satellite proxies, not independently verified local cloudbursts",
            "Warm-up/reference and rolling scores do not certify real hazard detection or probability calibration",
            "Overlapping model/satellite grids and related event hours are not independent event samples",
            "Reference baseline waits for all finite reference predictions to have mature labels",
            "Rolling window ends at latest mature scored outcome, not falsely at the live date",
            "Frozen holdout scores exclude pre-holdout predictions; online adaptive scores are prequential evaluation",
            "Label availability is user-declared/assumed and source/negative-monitoring admission remains unverified"])
    (output/"manifest.json").write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n")
    print(f"{target}: {len(state.predictions)} issued scores, {len(state.scored)} mature labels, {receipt['update_batches']} incremental batches; UNCALIBRATED")
    print("Saved research replay:",output)
    return receipt


def main():
    """Read explicit source/evidence/availability settings and execute replay."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--era5",type=Path,nargs="+",required=True)
    p.add_argument("--labels",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--target",choices=["cloudburst","snowstorm"],required=True)
    p.add_argument("--label-role",choices=["satellite_proxy","observed_event_unverified","synthetic_test"],required=True)
    p.add_argument("--feature-delay-hours",type=float,required=True)
    p.add_argument("--label-delay-hours",type=float)
    p.add_argument("--config",type=Path,default=ROOT/"configs/online_storm_research_v1.json")
    p.add_argument("--until",help="Exclusive timezone-aware UTC midnight; optionally drain delayed labels")
    p.add_argument("--resume",type=Path,help="Operator-trusted local checkpoint, never an untrusted downloaded pickle")
    args=p.parse_args()
    config=json.loads(args.config.read_text())
    if config.get("schema_version")!=SCHEMA:
        p.error("Unknown configuration schema")
    try:
        run_replay(args.era5,args.labels,args.output,target=args.target,label_role=args.label_role,
            feature_delay_hours=args.feature_delay_hours,label_delay_hours=args.label_delay_hours,
            settings=config["settings"],until=args.until,resume=args.resume)
    except (ValueError,FileNotFoundError) as exc:
        p.error(str(exc))


if __name__=="__main__":
    main()

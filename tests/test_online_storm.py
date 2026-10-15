"""Synthetic online causality/availability contracts, never real hazard accuracy."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.hazard_context.online import (initialize, load_checkpoint, process_day,
    rolling_metrics, save_checkpoint, scaler_digest)
from ml.hazard_context.online_data import FEATURES, key, load_era5, read_labels


def frames(days=48):
    """Create independent synthetic feature/label tables with two-day delay."""
    rng=np.random.default_rng(7)
    times=pd.date_range("2024-01-01",periods=days*24,freq="h",tz="UTC")
    data=pd.DataFrame(rng.normal(size=(len(times),len(FEATURES))),columns=FEATURES)
    data["time"],data["lat"],data["lon"]=times,31.7,76.9
    data["feature_available_at"]=times+pd.Timedelta(minutes=30)
    data["key"]=[key(t,31.7,76.9) for t in times]
    labels=data[["key","time","lat","lon"]].copy()
    labels["label"]=(np.arange(len(times))%7==0).astype(float)
    labels["available_at"]=times+pd.Timedelta(days=2)
    return data,labels


def replay(features,labels,end=None,config=None):
    """Run the public state machine in consecutive observation-day order."""
    state=initialize(features,labels,config or {},target="cloudburst",label_role="synthetic_test")
    stop=pd.Timestamp(end or features.time.max().floor("D"))
    for day in pd.date_range(state.train_end,stop,freq="D"):
        process_day(state,features.loc[features.time.dt.floor("D").eq(day)],labels,day)
    return state


def test_future_rows_labels_and_class_balance_cannot_change_earlier_predictions():
    features,labels=frames()
    stop="2024-02-05T00:00:00Z"
    a=replay(features,labels,stop)
    poisoned=features.copy()
    poisoned.loc[poisoned.time>=pd.Timestamp("2024-02-06T00:00:00Z"),FEATURES]=10000.
    future=labels.copy()
    future.loc[future.time>=pd.Timestamp("2024-02-06T00:00:00Z"),"label"]=1.
    b=replay(poisoned,future,stop)
    assert a.predictions==b.predictions
    assert a.audit==b.audit
    assert a.class_weights==b.class_weights
    np.testing.assert_array_equal(a.model.coef_,b.model.coef_)
    np.testing.assert_array_equal(a.scaler.mean_,b.scaler.mean_)


def test_predictions_are_recorded_before_update_and_labels_are_mature():
    features,labels=frames()
    state=initialize(features,labels,{},target="cloudburst",label_role="synthetic_test")
    fixed=scaler_digest(state.scaler)
    for day in pd.date_range(state.train_end,periods=12,freq="D"):
        version=state.version
        def before_update(records):
            assert state.version==version
            assert state.audit[-1]["action"]=="PREDICT"
            assert all(r["model_version"]==version for r in records)
            assert all(pd.Timestamp(r["trained_through"])<day for r in records)
        process_day(state,features.loc[features.time.dt.floor("D").eq(day)],labels,day,before_update=before_update)
        assert scaler_digest(state.scaler)==fixed
    for event in state.audit:
        if event["action"]=="UPDATE":
            assert pd.Timestamp(event["maximum_label_available_at"])<=pd.Timestamp(event["at"])
    for day in sorted({e["day"] for e in state.audit if "day" in e}):
        actions=[e["action"] for e in state.audit if e.get("day")==day]
        if "UPDATE" in actions:
            assert actions.index("PREDICT")<actions.index("SCORE_STORED_PREDICTIONS")<actions.index("UPDATE")
    assert state.baseline_brier is not None
    assert state.baseline_established_at>state.warmup_end.isoformat()


def test_labels_not_yet_available_are_never_used_and_insufficient_warmup_fails():
    features,labels=frames()
    state=initialize(features,labels,{},target="cloudburst",label_role="synthetic_test")
    withheld=labels.copy()
    withheld.loc[withheld.time>=state.train_end,"available_at"]=pd.Timestamp("2026-01-01T00:00:00Z")
    before=state.model.coef_.copy()
    for day in pd.date_range(state.train_end,periods=8,freq="D"):
        process_day(state,features.loc[features.time.dt.floor("D").eq(day)],withheld,day)
    np.testing.assert_array_equal(state.model.coef_,before)
    assert not state.scored and state.baseline_brier is None
    assert state.metrics[-1]["brier_score"] is None
    assert state.metrics[-1]["roc_auc"] is None
    no_positives=labels.copy()
    no_positives["label"]=0.
    with pytest.raises(ValueError,match="NOT_READY"):
        initialize(features,no_positives,{},target="cloudburst",label_role="synthetic_test")


def test_checkpoint_resume_matches_uninterrupted_optimizer_and_rejects_tamper(tmp_path):
    features,labels=frames()
    state=replay(features,labels,"2024-02-03T00:00:00Z")
    path=tmp_path/"cloudburst_2024-02-03.joblib"
    save_checkpoint(state,path)
    resumed=load_checkpoint(path)
    for day in pd.date_range("2024-02-04T00:00:00Z","2024-02-06T00:00:00Z",freq="D"):
        batch=features.loc[features.time.dt.floor("D").eq(day)]
        process_day(state,batch,labels,day)
        process_day(resumed,batch,labels,day)
    assert state.predictions==resumed.predictions
    assert state.metrics==resumed.metrics
    np.testing.assert_array_equal(state.model.coef_,resumed.model.coef_)
    assert state.model.t_==resumed.model.t_
    with path.open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ValueError,match="hash mismatch"):
        load_checkpoint(path)


def test_frozen_holdout_excludes_adaptive_scores_and_stops_all_updates():
    features,labels=frames()
    state=replay(features,labels,config={"holdout_start":"2024-02-05T00:00:00Z"})
    holdout=[r for r in state.predictions if r["evaluation_role"]=="FROZEN_HOLDOUT"]
    assert len({r["model_version"] for r in holdout})==1
    assert not [a for a in state.audit if a["action"]=="UPDATE" and a["day"]>="2024-02-05T00:00:00+00:00"]
    assert state.metrics[-1]["rows"]==len([r for r in state.scored if r["evaluation_role"]=="FROZEN_HOLDOUT"])
    assert not state.metrics[-1]["calibrated"]


def test_bad_order_or_accidental_scaler_refit_rejected():
    features,labels=frames()
    state=initialize(features,labels,{},target="cloudburst",label_role="synthetic_test")
    day=state.train_end
    batch=features.loc[features.time.dt.floor("D").eq(day)]
    process_day(state,batch,labels,day)
    with pytest.raises(ValueError,match="once in order"):
        process_day(state,batch,labels,day)
    state.scaler.fit(features[FEATURES].to_numpy())
    next_day=day+pd.Timedelta(days=1)
    with pytest.raises(ValueError,match="scaler changed"):
        process_day(state,features.loc[features.time.dt.floor("D").eq(next_day)],labels,next_day)


def test_drift_warning_single_class_auc_and_missing_features_are_explicit():
    features,labels=frames()
    state=initialize(features,labels,{},target="cloudburst",label_role="synthetic_test")
    day=state.train_end
    batch=features.loc[features.time.dt.floor("D").eq(day)].copy()
    batch.loc[batch.index[0],FEATURES[0]]=np.nan
    records,_=process_day(state,batch,labels,day)
    assert records[0]["cloudburst_risk_uncal"] is None
    assert records[0]["status"]=="MISSING_OR_UNAVAILABLE_FEATURES"
    assert records[0]["key"] not in state.pending
    state.baseline_brier=0.
    state.scored=[dict(time=day.isoformat(),label=0,score=.3,evaluation_role="PREQUENTIAL_ADAPTIVE")]
    metrics=rolling_metrics(state,day+pd.Timedelta(days=1),day)
    assert metrics["drift_warning"]
    assert metrics["roc_auc"] is None
    assert not metrics["empirical_accuracy_claimed"]


def test_real_netcdf_loader_units_missing_values_label_roles_and_public_cli(tmp_path):
    pytest.importorskip("xarray")
    from ml.hazard_context.online_demo import create_inputs
    nc,paths=create_inputs(tmp_path/"inputs",days=40)
    labels,receipt=read_labels(paths["cloudburst"],target="cloudburst",label_role="synthetic_test")
    data,source=load_era5([nc],[(31.7,76.9)],feature_delay_hours=.5)
    assert data.columns[:10].tolist()==FEATURES
    assert source["physical_sensor_channels_added"]==0
    assert not source["as_issued_feature_availability_verified"]
    assert receipt["independent_observed_admission"] is False
    with pytest.raises(ValueError,match="not snowstorm"):
        read_labels(paths["cloudburst"],target="snowstorm",label_role="satellite_proxy")
    with pytest.raises(ValueError,match="distance"):
        load_era5([nc],[(30.,76.9)],feature_delay_hours=.5)
    import xarray as xr
    with xr.open_dataset(nc) as ds:
        bad=ds.load()
    bad["sp"].attrs["units"]="hPa"
    bad.to_netcdf(tmp_path/"bad.nc")
    with pytest.raises(ValueError,match="units"):
        load_era5([tmp_path/"bad.nc"],[(31.7,76.9)],feature_delay_hours=.5)
    spec=importlib.util.spec_from_file_location("online_storm_test",Path(__file__).resolve().parents[1]/"scripts/online_storm_risk.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result=module.run_replay([nc],paths["cloudburst"],tmp_path/"run",target="cloudburst",label_role="synthetic_test",feature_delay_hours=.5)
    assert result["update_batches"]>0 and not result["empirical_accuracy_claimed"]
    predictions=pd.read_csv(tmp_path/"run/predictions.csv")
    assert "cloudburst_risk_uncal" in predictions
    assert (predictions["status"]=="EXPERIMENTAL_UNCALIBRATED").all()
    assert (tmp_path/"run/metrics.csv").is_file()
    assert list((tmp_path/"run").glob("*.joblib"))


def test_unknown_labels_stay_unknown_and_missing_availability_requires_explicit_delay(tmp_path):
    rows=pd.DataFrame(dict(time=["2024-01-01T00:00:00Z","2024-01-01T01:00:00Z"],lat=[31.7]*2,lon=[76.9]*2,label=[0,np.nan]))
    path=tmp_path/"labels.csv"
    rows.to_csv(path,index=False)
    with pytest.raises(ValueError,match="explicit label delay"):
        read_labels(path,target="cloudburst",label_role="satellite_proxy")
    labels,_=read_labels(path,target="cloudburst",label_role="satellite_proxy",assumed_delay_hours=48)
    assert labels.label.isna().sum()==1
    rows["available_at"]=["2024-01-01T00:00:00Z",None]
    rows.to_csv(path,index=False)
    with pytest.raises(ValueError,match="hour ends"):
        read_labels(path,target="cloudburst",label_role="satellite_proxy")

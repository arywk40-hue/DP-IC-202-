"""Fit/test India-only numeric models; no Beijing weights or hazard proxies are loaded."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
import xgboost as xgb

from ml.india_mandi.data import ROOT
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS, PHYSICAL_RANGES
from ml.six_sensor_forecast.data import sha256
from ml.six_sensor_forecast.features import build_features, future_targets, split_masks
from ml.six_sensor_forecast.train import train, scores


def arrays(cfg):
    root=Path(cfg['data']);manifest=json.loads((root/'dataset_manifest.json').read_text())
    if manifest.get('country_code')!='IN' or manifest.get('evidence_kind')!='MODELED_GRID_RETROSPECTIVE' or manifest['observations_sha256']!=sha256(root/'observations.csv'):
        raise ValueError('Immutable Mandi modeled-data provenance required')
    frame,features=build_features(pd.read_csv(root/'observations.csv'))
    truth=future_targets(frame,cfg['horizon_hours'])
    masks=split_masks(frame,6,cfg['validation_start'],cfg['test_start'],[],temporal_only=True)
    good=np.isfinite(features.to_numpy()).all(axis=1)&np.isfinite(truth.to_numpy()).all(axis=1)
    masks={k:v&good for k,v in masks.items()}
    if any(v.sum()<2 for v in masks.values()):raise ValueError('Insufficient complete-history chronological labels')
    return frame,features,truth,masks,manifest


def fit(cfg):
    root=Path(cfg['models'])
    if root.exists() and any(root.iterdir()):raise ValueError('Model output exists; test it or choose a new versioned config')
    # From-scratch six-head fit on Mandi modeled numbers. No foreign pretrained model.
    report=train(Path(cfg['data']),root,6,cfg['validation_start'],cfg['test_start'],[],
                 cfg['teacher_max_rounds'],cfg['threads'],cfg['seed'],RAW_SENSOR_COLUMNS,
                 temporal_only=True,require_complete_history=True)
    frame,features,truth,masks,_=arrays(cfg)
    x=features.to_numpy(dtype=float);y=truth.to_numpy(dtype=float)-frame[RAW_SENSOR_COLUMNS].to_numpy(dtype=float)
    mean=x[masks['train']].mean(axis=0);std=x[masks['train']].std(axis=0);std[std==0]=1.
    normalized=(x-mean)/std
    coefficients,intercepts,choices=[],[],{}
    for j,target in enumerate(RAW_SENSOR_COLUMNS):
        trials=[]
        for alpha in cfg['ridge_alpha_candidates']:
            learner=Ridge(alpha=alpha,solver='svd').fit(normalized[masks['train']],y[masks['train'],j])
            current=frame.loc[masks['validation'],target].to_numpy()
            predicted=np.clip(current+learner.predict(normalized[masks['validation']]),*PHYSICAL_RANGES[target])
            metric=scores(truth.loc[masks['validation'],target].to_numpy(),predicted)
            trials.append((metric['mae'],alpha,learner,metric))
        _,alpha,chosen,metric=min(trials,key=lambda v:(v[0],-v[1]))
        coefficients.append(chosen.coef_);intercepts.append(chosen.intercept_)
        choices[target]={'alpha':alpha,'validation':metric,'candidates':[{'alpha':a,'validation_mae':m} for m,a,_,_ in trials]}
    path=root/'temporal_ridge.npz'
    np.savez(path,mean=mean,std=std,coefficients=np.asarray(coefficients),intercepts=np.asarray(intercepts))
    ridge=dict(model_country='IN',evidence_kind='MODELED_GRID_RETROSPECTIVE',features=features.columns.tolist(),
               targets=RAW_SENSOR_COLUMNS,artifact=path.name,sha256=sha256(path),choices=choices,
               architecture='Six independent standardized residual ridge heads over 66 causal six-channel/history features',
               normalization='Training-only feature means/stds; no imputation, full history required',
               rows_by_role={k:int(v.sum()) for k,v in masks.items()},deployment_approved=False)
    (root/'ridge_report.json').write_text(json.dumps(ridge,indent=2,allow_nan=False)+'\n')
    report['model_country']='IN';report['evidence_kind']='MODELED_GRID_RETROSPECTIVE'
    report['china_data_or_weights_used']=False;report['experiment_config_sha256']=cfg['_config_sha256']
    (root/'training_report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


def metric(truth,predicted,current):
    out=scores(truth,predicted);base=scores(truth,current)
    out['persistence_mae']=base['mae'];out['mae_skill_vs_persistence']=1-out['mae']/base['mae'] if base['mae'] else None
    return out


def head_path(root,relative,digest):
    p=(root/relative).resolve()
    if not p.is_relative_to(root.resolve()) or sha256(p)!=digest:raise ValueError('Model artifact/path checksum mismatch')
    return p


def evaluate(cfg):
    frame,features,truth,masks,manifest=arrays(cfg)
    root=Path(cfg['models']);report=json.loads((root/'training_report.json').read_text())
    if report.get('model_country')!='IN' or report.get('china_data_or_weights_used') is not False or report.get('experiment_config_sha256')!=cfg['_config_sha256'] or report['source']['observations_sha256']!=manifest['observations_sha256']:
        raise ValueError('Only the matching India/Mandi-trained profile may be evaluated')
    ridge=json.loads((root/'ridge_report.json').read_text())
    path=head_path(root,ridge['artifact'],ridge['sha256'])
    with np.load(path,allow_pickle=False) as data:
        if set(data.files)!={'mean','std','coefficients','intercepts'}:raise ValueError('Unexpected ridge serialization')
        x=(features[ridge['features']].to_numpy(dtype=float)-data['mean'])/data['std']
        residuals=x@data['coefficients'].T+data['intercepts']
    fresh=masks['future_test']&(frame.timestamp_utc>=pd.Timestamp(cfg['fresh_test_start'])).to_numpy()
    results,choices,predictions={}, {},{}
    for j,target in enumerate(RAW_SENSOR_COLUMNS):
        entry=report['models'][target];current=frame[target].to_numpy(dtype=float)
        predictions[target]={'persistence':current,'temporal_ridge':np.clip(current+residuals[:,j],*PHYSICAL_RANGES[target])}
        for kind in ['teacher','student']:
            model=xgb.Booster(params={'nthread':cfg['threads']});model.load_model(head_path(root,entry[kind+'_file'],entry[kind+'_sha256']))
            columns=report['architecture'][kind+'_features']
            inputs=features[columns] if kind=='teacher' else frame[columns].astype(np.float32)
            predictions[target][kind]=np.clip(current+entry[kind+'_weight']*model.predict(xgb.DMatrix(inputs,feature_names=columns)),*PHYSICAL_RANGES[target])
        results[target]={}
        for name,mask in {**masks,'fresh_future_test':fresh}.items():
            if not mask.any():continue
            results[target][name]={kind:metric(truth.loc[mask,target].to_numpy(),p[mask],current[mask]) for kind,p in predictions[target].items()}
        # Persistence first resolves ties safely; all selection uses validation only.
        choices[target]=min(predictions[target],key=lambda k:results[target]['validation'][k]['mae'])
    mask=masks['future_test'];examples=[]
    for index in np.flatnonzero(mask)[:3]:
        examples.append({'input_timestamp_utc':frame.timestamp_utc.iloc[index].isoformat(),
                         'forecast_timestamp_utc':(frame.timestamp_utc.iloc[index]+pd.Timedelta(hours=6)).isoformat(),
                         'input':{t:float(frame[t].iloc[index]) for t in RAW_SENSOR_COLUMNS},
                         'student_prediction':{t:float(predictions[t]['student'][index]) for t in RAW_SENSOR_COLUMNS},
                         'validation_selected_prediction':{t:float(predictions[t][choices[t]][index]) for t in RAW_SENSOR_COLUMNS},
                         'later_api_value':{t:float(truth[t].iloc[index]) for t in RAW_SENSOR_COLUMNS}})
    split={role:dict(rows=int(m.sum()),first_issue_utc=frame.loc[m,'timestamp_utc'].min().isoformat(),last_issue_utc=frame.loc[m,'timestamp_utc'].max().isoformat()) for role,m in {**masks,'fresh_future_test':fresh}.items() if m.any()}
    return dict(experiment=cfg['experiment_id'],model_country='IN',china_weights_loaded=0,china_rows_used=0,
                evidence_kind='MODELED_GRID_RETROSPECTIVE',source_manifest=manifest,config_sha256=cfg['_config_sha256'],
                source_period=dict(start=cfg['start_date'],end=cfg['end_date']),split=split,
                input_channels=RAW_SENSOR_COLUMNS,temporal_features=features.columns.tolist(),
                results=results,validation_selected_heads=choices,examples=examples,
                hazard_results={t:dict(status='NOT_EVALUABLE_NO_ADMITTED_EVENT_LABELS',trained=False,accuracy=None,
                                      reason='Modeled weather/rain cannot supply independent Himalayan occurrence labels or monitored negatives')
                                for t in ['cloudburst','storm','flash_flood','landslide','snowstorm']},
                geographic_validation='NOT_EVALUATED_SINGLE_MANDI_GRID',field_accuracy='NOT_ESTABLISHED',deployment_approved=False,
                test_exposure_note=cfg['test_exposure_note'])


def indian_transfer_tests(cfg):
    """Existing India-trained profiles on both original Indian and Mandi modeled outcomes."""
    outputs=[]
    mandi,mandi_features,mandi_truth,mandi_masks,_=arrays(cfg)
    native=ROOT/'ml/data/india_cpcb_research/observations.csv'
    readable=native.exists() and not (getattr(native.stat(),'st_flags',0)&0x40000000)
    local_frame=local_features=None
    if readable:local_frame,local_features=build_features(pd.read_csv(native))
    for profile in ['india_cpcb_5sensor_6h','india_cpcb_pm_6h']:
        root=ROOT/'ml/models'/profile;report=json.loads((root/'training_report.json').read_text())
        if not report['source']['source_name'].startswith('Indian CPCB'):
            raise ValueError('Unexpected non-Indian transfer model source')
        sensors=report['sensor_profile'];native_truth=native_masks=None
        if readable:
            if sha256(native)!=report['source']['observations_sha256']:raise ValueError('Indian source snapshot changed')
            native_truth=future_targets(local_frame,6);s=report['split']
            native_masks=split_masks(local_frame,6,s['validation_start'],s['test_start'],s['holdout_locations'])
        for target,entry in report['models'].items():
            for kind in ['teacher','student']:
                model=xgb.Booster(params={'nthread':cfg['threads']});model.load_model(head_path(root,entry[kind+'_file'],entry[kind+'_sha256']))
                cols=report['architecture'][kind+'_features']
                cohorts=[('Mandi_modeled_future_test',mandi,mandi_features,mandi_truth,mandi_masks['future_test'],'India-trained transfer diagnostic; completed-hour training means versus Mandi modeled instantaneous values')]
                if readable:
                    cohorts.extend((split,local_frame,local_features,native_truth,native_masks[split],'Original held-out Indian secondary observations; source timezone assumption remains') for split in ['future_test','geographic_test'])
                for split,f,features,labels,mask,evidence in cohorts:
                    mask=mask&np.isfinite(f[sensors].to_numpy()).all(axis=1)&np.isfinite(labels[target].to_numpy())
                    if not mask.any():continue
                    values=features.loc[mask,cols] if kind=='teacher' else f.loc[mask,cols].astype(np.float32)
                    current=f.loc[mask,target].to_numpy(dtype=float)
                    predicted=np.clip(current+entry[kind+'_weight']*model.predict(xgb.DMatrix(values,feature_names=cols)),*PHYSICAL_RANGES[target])
                    outputs.append(dict(profile=profile,model_country='IN',kind=kind,target=target,split=split,evidence=evidence,
                                        sensors=sensors,metrics=metric(labels.loc[mask,target].to_numpy(),predicted,current)))
    return outputs

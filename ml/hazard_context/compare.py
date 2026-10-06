"""Matched S/SB measurement research, isolated from deployment and frozen results."""
import hashlib
import json

import numpy as np
import pandas as pd

from ml.hazard_context.era5 import FEATURES, join_context
from ml.hazard_context.output import fresh_directory
from ml.india_sensor.features import build, feature_columns
from ml.india_sensor.labels import measured_future
from ml.india_sensor.metrics import metrics,cluster_brier_interval
from ml.india_sensor.splits import station_roles, row_roles
from ml.india_sensor.thresholds import decision_metrics
from ml.india_sensor.train import fit_head


def paired_brier_interval(y,a,b,groups,seed=42,repeats=200):
    y,a,b=np.asarray(y),np.asarray(a),np.asarray(b);groups=np.asarray(groups)
    ids=np.unique(groups)
    if len(ids)<2:return None
    totals=np.array([(((b[groups==g]-y[groups==g])**2-(a[groups==g]-y[groups==g])**2).sum(),int((groups==g).sum())) for g in ids])
    samples=np.random.default_rng(seed).integers(0,len(ids),size=(repeats,len(ids)))
    sums=totals[samples].sum(axis=1)
    return np.quantile(sums[:,0]/sums[:,1],[.025,.975]).tolist()


def run(observations,background,cfg,manifest,output,scope='national',allow_fixture=False):
    if manifest.get('evidence')=='SYNTHETIC_CONTRACT_ONLY' and not allow_fixture:raise ValueError('Synthetic context is not real model evidence')
    if manifest.get('rights_status')!='approved_open' or not manifest.get('raw_file_sha256'):
        raise ValueError('Reviewed open background rights and provenance required for clean comparison')
    if manifest.get('dataset')!='era5_land' or manifest.get('provider')!='ECMWF/Copernicus' or manifest.get('country')!='IN':
        raise ValueError('Unexpected background provenance')
    f=build(observations,cfg)
    labels=measured_future(f,cfg)
    joined=join_context(f,background,manifest.get('mode','retrospective_background_context'))
    # Exact same selected rows/sites/labels in both tracks; no missing-background advantage.
    common=joined[FEATURES].notna().all(axis=1)&joined[['temperature_c','relative_humidity_pct','wind_speed_mps']].notna().all(axis=1)
    if not common.any():raise ValueError('No matched real background; do not fit an empty/fictional comparison')
    f=f.loc[common].reset_index(drop=True);context=joined.loc[common].reset_index(drop=True);labels=labels.loc[common].reset_index(drop=True)
    stations=f[['location_id','physical_site_id','latitude','longitude','elevation_m']].drop_duplicates('physical_site_id')
    roles=station_roles(stations,scope,cfg);masks=row_roles(f,roles,cfg)
    s=feature_columns(f,geographical=True)
    if any(c.startswith('era5_') for c in s):raise AssertionError('Track S contamination')
    sb=[*s,*FEATURES]
    frame=pd.concat([f,context[FEATURES],labels[list(cfg['threshold_targets'])]],axis=1)
    output=fresh_directory(output)
    report={'evidence':manifest.get('evidence','REAL_PROVIDER_CONTEXT_RESEARCH'),'mode':manifest.get('mode','retrospective_background_context'),
            'matched_rows':len(f),'station_roles':roles,'feature_tracks':{'S':s,'SB':sb},'targets':{},'seed':cfg['seed'],
            'matched_key_sha256':hashlib.sha256(pd.util.hash_pandas_object(f[['physical_site_id','timestamp_utc']],index=False).values.tobytes()).hexdigest(),
            'background_manifest':manifest,'background_usage':{'used_for_training':True,'used_for_validation':True,'used_for_labels':False},
            'config_snapshot':cfg, 'sensor_frame_sha256':hashlib.sha256(pd.util.hash_pandas_object(observations,index=True).values.tobytes()).hexdigest(),
            'disaster_outputs':'DISABLED','deployment_approved':False,
            'label_type':'Future measured NOAA thresholds, not independent disasters','full_s_baseline_not_overwritten':True}
    for target in cfg['threshold_targets']:
        results={};heads={}
        for track,columns in [('S',s),('SB',sb)]:
            fit,head=fit_head(frame,target,masks,columns,cfg,output/(target+'_'+track+'.ubj'))
            heads[track]=head
            if fit is not None:
                y=frame.loc[fit['test_mask'],target].to_numpy()
                measured=metrics(y,fit['probabilities'])
                measured['brier_station_bootstrap_95ci']=cluster_brier_interval(y,fit['probabilities'],frame.loc[fit['test_mask'],'physical_site_id'].to_numpy(),cfg['seed'])
                results[track]={'metrics':measured,
                                'validation_cutoff_metrics':decision_metrics(y,fit['raw_test']-fit['raw_thresholds'],0.,cfg['cadence_seconds']) if (head.get('threshold_selection') or {}).get('raw_threshold') is not None else {'status':'NO_VALIDATED_THRESHOLD'},
                                'probability_status':head['probability_status'],'metadata':head}
            else:results[track]={'status':head['status']}
            heads[track]['prediction_bundle']=fit
        if all(h['prediction_bundle'] is not None for h in heads.values()):
            a,b=[heads[k].pop('prediction_bundle') for k in ['S','SB']]
            if not np.array_equal(a['test_mask'],b['test_mask']):raise AssertionError('Unmatched S/SB test rows')
            y=frame.loc[a['test_mask'],target].to_numpy();groups=frame.loc[a['test_mask'],'physical_site_id'].to_numpy()
            results['paired_brier_delta_SB_minus_S_95ci']=paired_brier_interval(y,a['probabilities'],b['probabilities'],groups,cfg['seed'])
        else:
            for h in heads.values():h.pop('prediction_bundle',None)
        report['targets'][target]=results
    (output/'comparison.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report

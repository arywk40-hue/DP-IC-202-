"""Research hazard association fits only after independent admission and episode screens."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ml.hazard_context.episodes import evaluate
from ml.hazard_context.output import fresh_directory
from ml.hazard_context.events import admit
from ml.hazard_context.matching import group_events, match
from ml.hazard_context.policy import training_gate, purge_groups
from ml.india_sensor.features import build, feature_columns
from ml.india_sensor.metrics import metrics,cluster_brier_interval
from ml.hazard_context.diagnostics import operating_curve
from ml.india_sensor.splits import station_roles, row_roles
from ml.india_sensor.train import fit_head


def targets(frame,matched,target,horizon):
    """Associate exact future observed windows, not issue-time weak rules."""
    records=[]
    for (site,time),rows in matched[matched.event_type.eq(target)].groupby(['physical_site_id','timestamp_utc']):
        positive=rows[rows.label.eq(1)]
        if len(positive):
            groups=positive.event_group_id.unique()
            if len(groups)!=1:raise ValueError('Overlapping unmerged episodes require adjudication')
            label=1.;group=groups[0];start=positive.event_start_utc.min()
        elif rows.label.eq(0).all():label=0.;group=rows.event_group_id.iloc[0];start=None
        else:label=np.nan;group=None;start=None
        records.append(dict(physical_site_id=site,timestamp_utc=pd.Timestamp(time)-pd.Timedelta(hours=horizon),
                            label=label,event_group_id=group,event_start_utc=start))
    future=pd.DataFrame(records)
    if future.empty:return frame[['physical_site_id','timestamp_utc']].assign(label=np.nan,event_group_id=None,event_start_utc=None)
    return frame[['physical_site_id','timestamp_utc']].merge(future,on=['physical_site_id','timestamp_utc'],how='left',validate='one_to_one')


def run(events,sources,stations,observations,monitoring,cfg,output,target_names,scope='national',restricted=False,matching_cfg=None):
    reviewed=group_events([admit(e,sources.get(e['source_dataset'],{}),restricted) for e in events],matching_cfg)
    matched=match(reviewed,stations,observations,monitoring,cfg=matching_cfg,restricted=restricted)
    output=fresh_directory(Path(output)/('restricted' if restricted else 'clean'))
    report={'targets':{},'disaster_outputs':'DISABLED','deployment_approved':False,
            'label_semantics':'Independently observed nearby-event association at exact future window, not disaster at station',
            'source_registry':sources,'matching_config':matching_cfg,'scope':scope,'seed':cfg['seed'],'config_snapshot':cfg,'training_view':'restricted' if restricted else 'clean'}
    for target in target_names:
        gate=training_gate(reviewed,matched,target)
        report['targets'][target]=gate
        if not gate['can_fit_research']:continue
        f=build(observations,cfg)
        truth=targets(f,matched,target,cfg['forecast_hours'])
        frame=pd.concat([f,truth[['label','event_group_id','event_start_utc']]],axis=1)
        roles=station_roles(stations,scope,cfg)
        masks,purge=purge_groups(frame,row_roles(f,roles,cfg),24,cfg['forecast_hours'],24)
        by_role={r:{'positive_events':frame.loc[m & frame.label.eq(1),'event_group_id'].nunique(),
                    'negative_episodes':frame.loc[m & frame.label.eq(0),'event_group_id'].nunique()} for r,m in masks.items()}
        # Episode—not hourly—support required in every actual fold before fit/calibration.
        minimum={'train':20,'validation':10,'calibration':10,'test':10}
        if any(by_role[r]['positive_events']<n or by_role[r]['negative_episodes']<10 for r,n in minimum.items()):
            gate.update(status='NOT_ENOUGH_DATA',can_fit_research=False,split_support=by_role,purge=purge);continue
        prediction,head=fit_head(frame,'label',masks,feature_columns(f,geographical=True),cfg,output/(target+'_research.ubj'))
        if prediction is None:
            gate.update(status='NOT_ENOUGH_DATA',model=head);continue
        y=frame.loc[prediction['test_mask'],'label'].to_numpy()
        test=frame.loc[prediction['test_mask']].copy()
        # Decisions always use the frozen validation raw cutoff; no test retuning.
        cutoff=(head.get('threshold_selection') or {}).get('raw_threshold')
        episode=None
        if cutoff is not None:
            test['issue_time_utc']=test.timestamp_utc
            test['target_time_utc']=test.timestamp_utc+pd.Timedelta(hours=cfg['forecast_hours'])
            test['score']=prediction['raw_test']
            episode=evaluate(test,cutoff)
        measured=metrics(y,prediction['probabilities'])
        measured['brier_episode_bootstrap_95ci']=cluster_brier_interval(y,prediction['probabilities'],test.event_group_id.to_numpy(),cfg['seed'])
        curve=operating_curve(frame,head,masks['validation'],cfg['forecast_hours'])
        gate.update(status='RESEARCH_ONLY',validation_operating_curve=curve,model=head,split_support=by_role,purge=purge,
                    test_metrics=measured,episode_metrics=episode)
    (output/'hazard_status.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report

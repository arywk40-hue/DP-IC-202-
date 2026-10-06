"""Observed episode diagnostics; unknown periods never count as false alerts."""
import numpy as np
import pandas as pd


def evaluate(frame,threshold,cadence_seconds=3600):
    required={'physical_site_id','issue_time_utc','target_time_utc','event_group_id','event_start_utc','label','score'}
    if not required<=set(frame) or not np.isfinite(threshold) or not 0<=threshold<=1:raise ValueError('Explicit episode predictions required')
    f=frame.copy()
    from ml.hazard_context.events import utc
    f.issue_time_utc=[utc(v) for v in f.issue_time_utc];f.target_time_utc=[utc(v) for v in f.target_time_utc]
    if (f.issue_time_utc>f.target_time_utc).any() or f.duplicated(['physical_site_id','issue_time_utc']).any():raise ValueError('Duplicate/future issue timestamp')
    if not f.score.between(0,1).all() or not f.label.dropna().isin([0,1]).all():raise ValueError('Invalid probability/observed label')
    f['alert']=f.score>=threshold
    positive=f[f.label.eq(1)]
    if positive.event_group_id.isna().any():raise ValueError('Positive event requires group identity')
    events=[]
    for group,rows in positive.groupby('event_group_id'):
        flagged=rows[rows.alert]
        starts=pd.to_datetime(rows.event_start_utc.dropna(),utc=True)
        events.append({'event_group_id':group,'detected':bool(len(flagged)),'sites':rows.physical_site_id.nunique(),
                       'first_alert_lead_hours':(starts.min()-flagged.issue_time_utc.min()).total_seconds()/3600 if len(flagged) and len(starts) else None})
    true=false=unknown=0
    for _,rows in f.sort_values(['physical_site_id','issue_time_utc']).groupby('physical_site_id'):
        blocks=(~rows.alert | (rows.issue_time_utc.diff().dt.total_seconds()>cadence_seconds)).cumsum()
        for _,episode in rows[rows.alert].groupby(blocks):
            if episode.label.eq(1).any():true+=1
            elif episode.label.isna().any():unknown+=1
            else:false+=1
    detected=sum(e['detected'] for e in events)
    return {'positive_event_groups':len(events),'detected_event_groups':detected,'event_recall':detected/len(events) if events else None,
            'missed_event_rate':1-detected/len(events) if events else None,'true_alert_episodes':true,'false_alert_episodes':false,'unknown_alert_episodes':unknown,
            'event_precision':true/(true+false) if true+false else None,'events':events,
            'note':'Matched nearby-event associations; not field alerts. Unknown/unmonitored periods excluded from false-alert precision.'}

"""Observed episode diagnostics; unknown periods never count as false alerts."""
import numpy as np
import pandas as pd


def evaluate(frame,threshold,cadence_seconds=3600,warning_only=False):
    required={'physical_site_id','issue_time_utc','target_time_utc','event_group_id','event_start_utc','label','score'}
    if not required<=set(frame) or not np.isfinite(threshold) or not 0<=threshold<=1:raise ValueError('Explicit episode predictions required')
    f=frame.copy()
    from ml.hazard_context.events import utc
    f.issue_time_utc=[utc(v) for v in f.issue_time_utc];f.target_time_utc=[utc(v) for v in f.target_time_utc]
    if (f.issue_time_utc>f.target_time_utc).any() or f.duplicated(['physical_site_id','issue_time_utc']).any():raise ValueError('Duplicate/future issue timestamp')
    if not f.score.between(0,1).all() or not f.label.dropna().isin([0,1]).all():raise ValueError('Invalid probability/observed label')
    if isinstance(cadence_seconds,bool) or not isinstance(cadence_seconds,int) or cadence_seconds<=0:raise ValueError('Positive integer evaluation cadence required')
    f['alert']=f.score>=threshold
    positive=f[f.label.eq(1)]
    if positive.event_group_id.isna().any():raise ValueError('Positive event requires group identity')
    if warning_only:
        starts=pd.Series([utc(v) for v in positive.event_start_utc],index=positive.index,dtype='datetime64[ns, UTC]')
        if starts.isna().any() or (starts<=positive.issue_time_utc).any():raise ValueError('Warning positives must precede onset')
        if {'event_onset_min_utc','event_onset_max_utc'}<=set(positive):
            lows=pd.Series([utc(v) for v in positive.event_onset_min_utc],index=positive.index,dtype='datetime64[ns, UTC]')
            highs=pd.Series([utc(v) for v in positive.event_onset_max_utc],index=positive.index,dtype='datetime64[ns, UTC]')
            if (lows<=positive.issue_time_utc).any() or (highs>positive.target_time_utc).any() or (lows>starts).any() or (highs<starts).any():raise ValueError('Onset uncertainty must lie wholly within the warning window')
    events=[]
    for group,rows in positive.groupby('event_group_id'):
        flagged=rows[rows.alert]
        starts=pd.to_datetime(rows.event_start_utc.dropna(),utc=True)
        entry={'event_group_id':group,'detected':bool(len(flagged)),'sites':rows.physical_site_id.nunique(),
               'first_alert_lead_hours':(starts.min()-flagged.issue_time_utc.min()).total_seconds()/3600 if len(flagged) and len(starts) else None}
        if warning_only and len(flagged) and {'event_onset_min_utc','event_onset_max_utc'}<=set(rows):
            earliest=pd.to_datetime(rows.event_onset_min_utc,utc=True).min()
            latest=pd.to_datetime(rows.event_onset_max_utc,utc=True).min()
            if pd.isna(earliest) or pd.isna(latest) or earliest<=flagged.issue_time_utc.min():raise ValueError('Verified pre-onset uncertainty bounds required')
            entry['first_alert_lead_min_hours']=(earliest-flagged.issue_time_utc.min()).total_seconds()/3600
            entry['first_alert_lead_max_hours']=(latest-flagged.issue_time_utc.min()).total_seconds()/3600
        events.append(entry)
    true=false=unknown=0
    for _,rows in f.sort_values(['physical_site_id','issue_time_utc']).groupby('physical_site_id'):
        blocks=(~rows.alert | (rows.issue_time_utc.diff().dt.total_seconds()>cadence_seconds)).cumsum()
        for _,episode in rows[rows.alert].groupby(blocks):
            if episode.label.eq(1).any():true+=1
            elif episode.label.isna().any():unknown+=1
            else:false+=1
    detected=sum(e['detected'] for e in events)
    negative_days=int(f.label.eq(0).sum())*cadence_seconds/86400
    return {'positive_event_groups':len(events),'detected_event_groups':detected,'event_recall':detected/len(events) if events else None,
            'missed_event_rate':1-detected/len(events) if events else None,'true_alert_episodes':true,'false_alert_episodes':false,'unknown_alert_episodes':unknown,
            'event_precision':true/(true+false) if true+false else None,'events':events,
            'eligible_monitored_negative_site_days':negative_days,
            'false_alert_episodes_per_100_monitored_site_days':100*false/negative_days if negative_days else None,
            'warning_only':warning_only,
            'negative_denominator_definition':'Eligible negative issue intervals counted once at declared cadence; overlapping target windows are not multiplied',
            'note':'Matched nearby-event associations; not field alerts. Unknown/unmonitored periods excluded from false-alert precision.'}

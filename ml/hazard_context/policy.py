"""Conservative research support screens and complete event-group isolation."""
import numpy as np
import pandas as pd

from ml.hazard_context.events import utc

MINIMUM_SUPPORT=dict(positive_events=50,positive_sites=10,positive_years=2,positive_districts=5,monitored_negative_days=30)


def support(events,matched):
    positives=matched[matched.label.eq(1)] if len(matched) else pd.DataFrame()
    negatives=matched[matched.label.eq(0)] if len(matched) else pd.DataFrame()
    ids=set(positives.event_id.dropna()) if len(positives) else set()
    participating=[r for r in events if r['event_id'] in ids]
    durations=[(utc(r['event_end_utc'])-utc(r['event_start_utc'])).total_seconds()/3600 for r in participating if r['event_start_utc'] and r['event_end_utc']]
    groups=set(positives.event_group_id.dropna()) if len(positives) else set()
    return {'positive_events':len(groups),'positive_reports':len(ids),'positive_hours':len(positives.drop_duplicates(['physical_site_id','timestamp_utc'])) if len(positives) else 0,
            'positive_sites':positives.physical_site_id.nunique() if len(positives) else 0,
            'positive_years':len({utc(r['event_start_utc']).year for r in participating if r['event_start_utc']}),
            'positive_districts':len({r['district'] for r in participating if r['district']}),'positive_states':len({r['state'] for r in participating if r['state']}),
            'median_event_duration_hours':float(np.median(durations)) if durations else None,
            'monitored_negative_days':float(negatives.drop_duplicates(['physical_site_id','timestamp_utc']).interval_seconds.sum()/86400) if len(negatives) else 0,
            'definition':'Distinct conservative leakage groups, not repeated reports/hours; days assume native hourly records'}


def training_gate(events,matched,target,minimum=None):
    minimum=minimum or MINIMUM_SUPPORT
    selected=[r for r in events if r['event_type']==target]
    subset=matched[matched.event_type.eq(target)] if len(matched) else matched
    evidence=support(selected,subset)
    reasons=[key for key,n in minimum.items() if evidence[key]<n]
    if any(r.get('label_provenance')=='SYNTHETIC_CONTRACT_ONLY' for r in selected):reasons.append('SYNTHETIC_NOT_INDEPENDENT')
    if not selected or not any(r['admission_status']=='admitted_for_training' for r in selected):reasons.append('NO_ADMITTED_INDEPENDENT_SOURCE')
    if not len(subset) or not subset.label.eq(0).any():reasons.append('NEGATIVES_UNAVAILABLE')
    status='RESEARCH_ONLY' if not reasons else 'NOT_ENOUGH_DATA'
    if target=='cloudburst' and any(r.get('cloudburst_evidence_verified') is not True for r in selected):reasons.append('CLOUDBURST_EVIDENCE_UNAVAILABLE')
    if target=='cloudburst' and reasons:status='DISABLED'
    return {'target':target,'status':status,'can_fit_research':not reasons,'minimum_support':minimum,'support':evidence,'blocked_reasons':reasons,
            'deployment_approved':False,'cloudburst_detected':'unavailable','cloudburst_prediction':'unavailable',
            'disaster_outputs':'DISABLED','screen_is_not_scientific_sufficiency':True}


def purge_groups(frame,masks,history_hours=24,forecast_hours=6,buffer_hours=24):
    """Never split a physical episode; crossing or buffered-boundary groups drop wholly."""
    masks={k:np.asarray(v,bool).copy() for k,v in masks.items()}
    if any(len(v)!=len(frame) for v in masks.values()):raise ValueError('Split mask length mismatch')
    if (sum(m.astype(int) for m in masks.values())>1).any():raise ValueError('Row belongs to multiple roles')
    assigned=np.full(len(frame),'',object)
    for role,mask in masks.items():assigned[mask]=role
    groups=frame.event_group_id
    dropped=[]
    for group,indices in frame.groupby('event_group_id',dropna=True).groups.items():
        indices=frame.index.get_indexer(indices)
        roles=set(assigned[indices])-{''}
        if len(roles)>1:
            for mask in masks.values():mask[indices]=False
            dropped.append(group)
    # Purge every row in other roles whose issue/target window touches an event
    # assigned elsewhere, then drop its own full group too (no partial episode).
    changed=True
    while changed:
        changed=False
        assigned[:]=''
        for role,mask in masks.items():assigned[mask]=role
        intervals=[]
        for group,indices in frame.groupby('event_group_id',dropna=True).groups.items():
            ix=frame.index.get_indexer(indices);roles=set(assigned[ix])-{''}
            if len(roles)==1:
                ts=pd.to_datetime(frame.iloc[ix].timestamp_utc,utc=True)
                intervals.append((group,next(iter(roles)),ts.min()-pd.Timedelta(hours=history_hours+buffer_hours),ts.max()+pd.Timedelta(hours=forecast_hours+buffer_hours)))
        for group,role,start,end in intervals:
            times=pd.to_datetime(frame.timestamp_utc,utc=True)
            for other,mask in masks.items():
                if other==role:continue
                touching=mask & (times+pd.Timedelta(hours=forecast_hours)>=start)&(times-pd.Timedelta(hours=history_hours)<=end)
                if touching.any():
                    bad=set(groups[touching].dropna())
                    remove=touching | groups.isin(bad).to_numpy()
                    for value in masks.values():value[remove]=False
                    dropped.extend(bad);changed=True
    for role,mask in masks.items():mask[groups.isna().to_numpy()]=False
    sets={role:set(groups[mask]) for role,mask in masks.items()}
    roles=list(sets)
    for i,a in enumerate(roles):
        for b in roles[:i]:
            if sets[a]&sets[b]:raise AssertionError('Event leakage after purge')
    return masks,{'dropped_groups':sorted(set(dropped)),'groups_by_role':{k:sorted(v) for k,v in sets.items()},'buffer_hours':buffer_hours}

"""WGS84 event association and explicit monitoring; absence is never a negative."""
import hashlib
from collections import Counter
import json

import numpy as np
import pandas as pd

from ml.hazard_context.events import normalize, utc

DEFAULTS = dict(spatial_radius_km=20.,pre_event_hours=6.,event_window_hours=0.,post_event_hours=12.,
                negative_sampling_window_hours=72.,event_separation_hours=24.,
                maximum_spatial_uncertainty_km=5.,maximum_temporal_uncertainty_hours=1.,max_pairs=1_000_000)


def geodesic_km(a,b,c,d):
    from geographiclib.geodesic import Geodesic
    return Geodesic.WGS84.Inverse(float(a),float(b),float(c),float(d))['s12']/1000


def distance(event,lat,lon):
    if event.get('geometry') is not None:
        from shapely.geometry import Point,shape
        from scipy.optimize import minimize_scalar
        from geographiclib.geodesic import Geodesic
        geom=shape(event['geometry'])
        if geom.geom_type=='Point':return geodesic_km(lat,lon,geom.y,geom.x)
        if geom.covers(Point(lon,lat)):return 0.
        polygons=[geom] if geom.geom_type=='Polygon' else list(geom.geoms)
        nearest=[]
        for polygon in polygons:
            for ring in [polygon.exterior,*polygon.interiors]:
                coords=list(ring.coords)
                for a,b in zip(coords,coords[1:]):
                    line=Geodesic.WGS84.InverseLine(a[1],a[0],b[1],b[0])
                    def separation(s):
                        p=line.Position(s)
                        return geodesic_km(lat,lon,p['lat2'],p['lon2'])
                    opt=minimize_scalar(separation,bounds=(0,line.s13),method='bounded')
                    nearest.append(min(separation(0),separation(line.s13),opt.fun))
        return min(nearest)
    if event.get('latitude') is None or event.get('longitude') is None:return None
    return geodesic_km(lat,lon,event['latitude'],event['longitude'])


def deduplicate(records):
    seen={};out=[]
    facts=['event_type','event_start_utc','event_end_utc','latitude','longitude','geometry','measurement_value','measurement_unit']
    for record in sorted(records,key=lambda r:(r['event_id'],r['source_provider'],r['source_dataset'],r['source_record_id'])):
        normalize(record)  # Validate without upgrading/changing the reviewed admission.
        key=(record['source_provider'],record['source_dataset'],record['source_record_id'])
        fingerprint=json.dumps({k:record[k] for k in facts},sort_keys=True)
        if key in seen:
            if seen[key]!=fingerprint:raise ValueError('Conflicting duplicate report; quarantine before matching')
            continue
        seen[key]=fingerprint;out.append(dict(record))
    repeated={key for key,n in Counter(r['event_id'] for r in out).items() if n>1}
    for record in out:
        if record['event_id'] in repeated:
            original=record['event_id']
            if record.get('event_group_id') and record['event_group_id']!=original:raise ValueError('Conflicting supplied physical event IDs require adjudication')
            record['reported_event_id']=original;record['event_group_id']=original
            ancestry='|'.join(record[k] for k in ['source_provider','source_dataset','source_record_id'])
            record['event_id']='report_'+hashlib.sha256(ancestry.encode()).hexdigest()[:24]
    return sorted(out,key=lambda r:r['event_id'])


def group_events(records,cfg=None):
    cfg={**DEFAULTS,**(cfg or {})};records=deduplicate(records)
    parent=list(range(len(records)))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def union(i,j):parent[root(j)]=root(i)
    supplied={}
    for i,r in enumerate(records):
        if r.get('event_group_id'):
            if r['event_group_id'] in supplied:union(i,supplied[r['event_group_id']])
            else:supplied[r['event_group_id']]=i
    ordered=sorted((utc(r['event_start_utc'])-pd.Timedelta(hours=r.get('temporal_uncertainty_hours') or 0),i)
                   for i,r in enumerate(records) if r.get('event_start_utc') and r.get('event_end_utc'))
    active={};pairs=0
    for start,i in ordered:
        a=records[i]
        active={j:until for j,until in active.items() if until>=start}
        for j in active:
            pairs+=1
            if pairs>cfg['max_pairs']:raise ValueError('Event grouping pair budget exceeded; adjudicate large/uncertain groups')
            b=records[j]
            point=a if a.get('latitude') is not None and a.get('longitude') is not None else b
            region=b if point is a else a
            if point.get('latitude') is None or point.get('longitude') is None:
                if a.get('geometry') is not None and b.get('geometry') is not None:
                    from shapely.geometry import shape
                    if shape(a['geometry']).intersects(shape(b['geometry'])):union(i,j)
                continue
            d=distance(region,point['latitude'],point['longitude'])
            radius=cfg['spatial_radius_km']+sum(r.get('spatial_uncertainty_km') or 0 for r in [a,b])
            if d is not None and d<=radius:union(i,j)
        active[i]=utc(a['event_end_utc'])+pd.Timedelta(hours=cfg['event_separation_hours']+(a.get('temporal_uncertainty_hours') or 0))
    members={}
    for i,r in enumerate(records):members.setdefault(root(i),[]).append(r)
    group_ids={}
    for key,rows in members.items():
        supplied=sorted({r['event_group_id'] for r in rows if r.get('event_group_id')})
        ids=supplied or sorted(r['event_id'] for r in rows)
        group_ids[key]=supplied[0] if len(supplied)==1 else 'episode_'+hashlib.sha256('|'.join(ids).encode()).hexdigest()[:24]
    for i,r in enumerate(records):r['event_group_id']=group_ids[root(i)]
    return records


def validate_monitoring(records):
    for r in records:
        for k in ['monitoring_id','physical_site_id','event_type','source_dataset','source_provider','source_version','definition','source_hash','rights_status','provider_license','rights_evidence_uri','reviewed_by','retrieved_at']:
            if not r.get(k):raise ValueError('Monitoring provenance/definition required')
        if r.get('country')!='IN' or r.get('independent_observed') is not True or r.get('complete_coverage_verified') is not True:
            raise ValueError('Verified Indian observed monitoring required')
        if r.get('negative_category') not in ['confirmed_negative','monitored_no_event']:
            raise ValueError('Unlabeled/unknown coverage cannot supply negatives')
        if r.get('monitoring_admission_status')!='admitted_for_training':raise ValueError('Monitoring review/admission required')
        utc(r['retrieved_at'])
        if not np.isfinite(r.get('spatial_coverage_radius_km',np.nan)) or r['spatial_coverage_radius_km']<0:raise ValueError('Explicit monitored spatial coverage required')
        if r['rights_status'] not in ['approved_open','approved_restricted']:
            raise ValueError('Monitoring rights unresolved')
        if len(r['source_hash'])!=64 or any(c not in '0123456789abcdef' for c in r['source_hash']):raise ValueError('Monitoring hash required')
        if utc(r['start_utc'])>=utc(r['end_utc']):raise ValueError('Reversed monitoring interval')
        if utc(r['retrieved_at'])<utc(r['end_utc']):raise ValueError('Complete monitoring cannot be recorded before coverage ends')
    return records


def match(events,stations,observations,monitoring=None,cfg=None,restricted=False):
    if set(cfg or {})-set(DEFAULTS):raise ValueError('Unknown matching parameter')
    cfg={**DEFAULTS,**(cfg or {})}
    if any(not np.isfinite(v) or v<0 for v in cfg.values()):raise ValueError('Finite nonnegative match limits required')
    events=group_events(events,cfg);monitoring=validate_monitoring(monitoring or [])
    if len(observations)*max(1,len(events))>cfg['max_pairs']:raise ValueError('Matching resource budget exceeded; partition by site/date')
    if stations.physical_site_id.duplicated().any():raise ValueError('Resolve physical aliases before matching')
    if not observations.country_code.eq('IN').all():raise ValueError('India-only observations required')
    observations=observations.copy()
    observations['timestamp_utc']=[utc(v) for v in observations.timestamp_utc]
    if observations.duplicated(['physical_site_id','timestamp_utc']).any():raise ValueError('Duplicate station timestamp')
    sites=stations.set_index('physical_site_id').to_dict('index');out=[]
    for row in observations.to_dict('records'):
        site=sites.get(row['physical_site_id'])
        if site is None:raise ValueError('Unresolved physical station')
        lat,lon=float(site['latitude']),float(site['longitude'])
        if not np.isfinite([lat,lon]).all() or not -90<=lat<=90 or not -180<=lon<=180:raise ValueError('Invalid station coordinates')
        t=utc(row['timestamp_utc']);cadence=row.get('interval_seconds',3600)
        if not isinstance(cadence,int) or isinstance(cadence,bool) or cadence<=0:raise ValueError('Positive observation interval required')
        beginning=t-pd.Timedelta(seconds=cadence)
        for target in sorted({e['event_type'] for e in events}|{m['event_type'] for m in monitoring}):
            matches=[];exclude=False
            for event in [e for e in events if e['event_type']==target]:
                d=distance(event,lat,lon)
                if d is not None and d>cfg['spatial_radius_km']+(event.get('spatial_uncertainty_km') or 0):continue
                if not event.get('event_start_utc') or not event.get('event_end_utc'):
                    exclude=True;continue
                s,e=utc(event['event_start_utc']),utc(event['event_end_utc'])
                uncertain=event.get('temporal_uncertainty_hours')
                margin=max(cfg['negative_sampling_window_hours'],cfg['event_separation_hours'],cfg['pre_event_hours'],cfg['post_event_hours'],cfg['event_window_hours'])+(uncertain or 0)
                if beginning<=e+pd.Timedelta(hours=margin) and t>s-pd.Timedelta(hours=margin):exclude=True
                if d is None:continue
                if beginning>e+pd.Timedelta(hours=max(cfg['post_event_hours'],cfg['event_window_hours'])) or t<=s-pd.Timedelta(hours=max(cfg['pre_event_hours'],cfg['event_window_hours'])):continue
                # Observation windows are [start,end). Point event matches only its containing window.
                during=(beginning<=s<t) if s==e else (beginning<e and t>s)
                nominal=d<=cfg['spatial_radius_km']
                precise=event.get('spatial_uncertainty_km') is not None and event['spatial_uncertainty_km']<=cfg['maximum_spatial_uncertainty_km'] and uncertain is not None and uncertain<=cfg['maximum_temporal_uncertainty_hours']
                label=1. if during and nominal and precise and event['admission_status']=='admitted_for_training' else None
                matches.append(dict(event_id=event['event_id'],event_group_id=event['event_group_id'],event_start_utc=event['event_start_utc'],distance_to_event_km=d,
                                    relative_event_time_hours=(t-s).total_seconds()/3600,label=label,
                                    label_quality='observed_nearby_event_association' if label==1 else 'unlabeled_event_context',
                                    spatial_uncertainty_km=event['spatial_uncertainty_km'],temporal_uncertainty_hours=uncertain,
                                    source_dataset=event['source_dataset'],source_hash=event['source_hash'],admission_status=event['admission_status']))
            base=dict(station_id=site['location_id'],physical_site_id=row['physical_site_id'],timestamp_utc=t.isoformat(),event_type=target,interval_seconds=cadence)
            if matches:
                out.extend({**base,**entry} for entry in matches);continue
            monitors=[m for m in monitoring if m['physical_site_id']==row['physical_site_id'] and m['event_type']==target and m['spatial_coverage_radius_km']>=cfg['spatial_radius_km'] and utc(m['start_utc'])<=beginning and t<=utc(m['end_utc']) and (restricted or m['rights_status']=='approved_open')]
            monitor=sorted(monitors,key=lambda m:m['monitoring_id'])[0] if monitors and not exclude else None
            block=int(t.timestamp()//(72*3600))
            out.append({**base,'event_id':None,'event_group_id':f'background_{block}' if monitor else None,'event_start_utc':None,
                        'distance_to_event_km':None,'relative_event_time_hours':None,'label':0. if monitor else None,
                        'label_quality':monitor['negative_category'] if monitor else 'unknown','monitoring_id':monitor['monitoring_id'] if monitor else None,
                        'source_dataset':monitor['source_dataset'] if monitor else None,'source_hash':monitor['source_hash'] if monitor else None,
                        'admission_status':'admitted_for_training' if monitor else 'candidate',
                        'spatial_uncertainty_km':None,'temporal_uncertainty_hours':None})
    return pd.DataFrame(out)

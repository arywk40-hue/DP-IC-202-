"""Versioned input-pattern experiments; resolution/history gates, never event truth."""
import hashlib

import numpy as np
import pandas as pd

from ml.operational.contracts import RAW_SENSOR_COLUMNS,observation,utc,canonical_bytes
from ml.event_classifier.features import _magnus_dew_point,_noaa_heat_index,_vpd_kpa,apply_event_labels,derive_event_features

CATALOG=[
 ('light_moderate_rain',['temperature_c','relative_humidity_pct','pressure_hpa','pm25_ug_m3','pm10_ug_m3'],3600,21600,None),
 ('severe_rainstorm_squall',[c for c in RAW_SENSOR_COLUMNS if c!='relative_humidity_pct'],900,21600,'storm_drop_window_seconds'),
 ('snowstorm_blizzard',RAW_SENSOR_COLUMNS,3600,21600,'scavenging_proxy'),
 ('freezing_rain_sleet',['temperature_c','relative_humidity_pct','pressure_hpa'],3600,3600,None),
 ('radiation_fog',['temperature_c','relative_humidity_pct','pm25_ug_m3','pm10_ug_m3','wind_speed_mps'],3600,0,'fog_aerosol_proxy'),
 ('ground_frost',['temperature_c','relative_humidity_pct','pressure_hpa','wind_speed_mps'],3600,3600,None),
 ('extreme_heatwave',['temperature_c','relative_humidity_pct'],3600,21600,'terrain_class'),
 ('wildfire_evaporative_risk',['temperature_c','relative_humidity_pct','wind_speed_mps'],3600,0,None),
 ('dust_storm_haboob',['relative_humidity_pct','pm25_ug_m3','pm10_ug_m3','wind_speed_mps'],3600,0,None),
 ('smoke_plume',['relative_humidity_pct','pm25_ug_m3','pm10_ug_m3','wind_speed_mps'],3600,0,None),
 ('smog_inversion_trap',['pressure_hpa','pm25_ug_m3','wind_speed_mps'],3600,21600,'pressure_baseline_hpa'),
 ('cold_frontal_passage',['temperature_c','relative_humidity_pct','pressure_hpa','wind_speed_mps'],3600,3600,'cold_front_rh_delta_pct')]


def resolution_allowed(source_seconds,requested_seconds):
    return type(source_seconds) is int and type(requested_seconds) is int and source_seconds>0 and requested_seconds>=source_seconds and requested_seconds%source_seconds==0


def catalog():
    return {'rule_version':'requested_matrix_v1','evidence_kind':'input_generated_pattern_not_independent_event','disaster_outputs':'DISABLED',
            'resolution_gate':'source_resolution_seconds <= rule_resolution_seconds AND compatible exact aggregation; never interpolate coarse data',
            'rules':[dict(event_id=n,input_channels=list(c),rule_resolution_seconds=r,history_seconds=h,undefined_parameter=p,expected_outcome='unknown') for n,c,r,h,p in CATALOG],
            'decisions':{'storm':'Pre-drop ΔP window unspecified; explicit parameter required; 15min jump/drop need genuine 15min-or-finer history',
                         'snow':'Scavenging is not directly measured; an explicitly chosen PM-decline proxy is required',
                         'fog':'Aerosol swelling undefined; optional PM threshold is only an explicit proxy, not observed swelling/fog',
                         'heat':'Plains/hills category must be supplied, not inferred from an arbitrary altitude cutoff; HI sustained over full 6h',
                         'inversion':'Local baseline unspecified; caller must provide documented baseline; six-hour strict monotonic PM rise',
                         'cold_front':'Sharp RH change unspecified; explicit percentage-point threshold required',
                         'active_lists':'Only formula-used channels required; extra T in smoke/inversion active lists is not a formula condition',
                         'pressure':'Station pressure at one fixed sensor elevation; relocation invalidates tendencies; sea-level/unknown reference rejected'}}


def evaluate(raw_records,parameters=None,issue_time_utc=None):
    parameters=parameters or {};records=[observation(r) for r in raw_records]
    if not records or len(records)>10000:raise ValueError('Bounded nonempty pattern history required')
    output=[]
    for identity in sorted({r['node_id'] for r in records}):
        rows=[r for r in records if r['node_id']==identity]
        if len({(r['latitude'],r['longitude'],r['elevation_m']) for r in rows})!=1:raise ValueError('Relocation requires a separate history/site')
        cadences={r['sample_interval_seconds'] for r in rows}
        if len(cadences)!=1:raise ValueError('One declared native cadence per history')
        cadence=next(iter(cadences));end=utc(issue_time_utc) if issue_time_utc else max(utc(r['timestamp_utc']) for r in rows)
        lookup={}
        for r in rows:
            key=(utc(r['timestamp_utc']),r['channel'])
            if key in lookup:raise ValueError('Duplicate channel/timestamp')
            if key[0]<=end:lookup[key]=r['value'] if utc(r['available_at_utc'])<=end else None
        def value(channel):return lookup.get((end,channel))
        def history(channel,seconds):
            if seconds%cadence:return None
            times=pd.date_range(end-pd.Timedelta(seconds=seconds),end,freq=pd.Timedelta(seconds=cadence))
            vals=[lookup.get((t,channel)) for t in times]
            if any(v is None for v in vals):return None
            return np.array(vals,dtype=float)
        def delta(channel,seconds):
            vals=history(channel,seconds)
            return None if vals is None else float(vals[-1]-vals[0])
        def current(names):return all(value(n) is not None for n in names)
        T,RH,P,pm25,pm10,W=[value(c) for c in RAW_SENSOR_COLUMNS]
        dew=None if T is None or RH is None or RH<=0 else float(_magnus_dew_point(np.array([T]),np.array([RH]))[0])
        hi=None if T is None or RH is None else float(_noaa_heat_index(np.array([T]),np.array([RH]))[0])
        vpd=None if T is None or RH is None else float(_vpd_kpa(np.array([T]),np.array([RH]))[0])
        ratio=None if pm25 is None or pm10 is None or pm10<=0 else pm25/pm10
        required_history={0:{'pressure_hpa':21600,'pm25_ug_m3':3600,'pm10_ug_m3':3600},1:{'pressure_hpa':parameters.get('storm_drop_window_seconds',21600),'temperature_c':900,'pm25_ug_m3':900,'pm10_ug_m3':900},2:{'pressure_hpa':21600,'pm25_ug_m3':3600,'pm10_ug_m3':3600},3:{'pressure_hpa':3600},5:{'pressure_hpa':3600},6:{'temperature_c':21600,'relative_humidity_pct':21600},10:{'pm25_ug_m3':21600},11:{'temperature_c':3600,'pressure_hpa':3600,'relative_humidity_pct':3600}}
        for index,(name,channels,resolution,span,undefined) in enumerate(CATALOG):
            status='pattern_evaluated';trigger=None;reason=None
            if not resolution_allowed(cadence,resolution):status='insufficient_temporal_resolution'
            elif not current(channels):status='missing_or_rejected_required_channel'
            elif undefined and parameters.get(undefined) is None:status='underspecified_rule';reason=undefined
            elif any(type(window) is not int or window<0 or history(c,window) is None for c,window in required_history.get(index,{}).items()):status='insufficient_history_or_gap'
            elif index in [4,5] and dew is None:status='derived_feature_unavailable'
            elif index==10 and (parameters.get('pressure_baseline_available_at_utc') is None or utc(parameters['pressure_baseline_available_at_utc'])>end):status='baseline_availability_unverified'
            else:
                if index==0:trigger=RH>=85 and delta('pressure_hpa',21600)<=-1.5 and T>3 and delta('pm25_ug_m3',3600)<0 and delta('pm10_ug_m3',3600)<0
                elif index==1:
                    window=parameters['storm_drop_window_seconds']
                    if type(window) is not int or window<900 or not resolution_allowed(cadence,window):status='underspecified_rule';reason='invalid pre-drop window'
                    elif delta('pressure_hpa',window) is None:status='insufficient_history_or_gap'
                    else:trigger=delta('pressure_hpa',window)<=-3.5 and delta('pressure_hpa',900)>=1.5 and delta('temperature_c',900)<=-3 and T>3 and W>=10 and delta('pm25_ug_m3',900)<0 and delta('pm10_ug_m3',900)<0
                elif index==2:
                    if parameters['scavenging_proxy']!='both_pm_declining_1h':status='underspecified_rule'
                    else:trigger=delta('pressure_hpa',21600)<=-3 and T<=1 and RH>=85 and W>=9 and delta('pm25_ug_m3',3600)<0 and delta('pm10_ug_m3',3600)<0
                elif index==3:trigger=delta('pressure_hpa',3600)<0 and RH>=90 and -2<=T<=.5
                elif index==4:
                    threshold=parameters['fog_aerosol_proxy']
                    if not isinstance(threshold,(int,float)) or not np.isfinite(threshold):status='underspecified_rule'
                    else:trigger=dew is not None and T-dew<=2 and RH>=95 and W<1.5 and pm25>threshold
                elif index==5:trigger=dew is not None and T<=0 and dew<=0 and W<2 and delta('pressure_hpa',3600)>=0
                elif index==6:
                    category=parameters['terrain_class']
                    if category not in ['plains','hills']:status='underspecified_rule'
                    else:
                        ts,rs=history('temperature_c',21600),history('relative_humidity_pct',21600)
                        trigger=T>=(40 if category=='plains' else 30) and np.all(_noaa_heat_index(ts,rs)>=41)
                elif index==7:trigger=vpd is not None and vpd>=2.5 and RH<=25 and W>=5
                elif index==8:trigger=ratio is not None and W>=8 and ratio<=.35 and pm10>250 and RH<40
                elif index==9:trigger=ratio is not None and pm25>150 and ratio>=.7 and RH<60 and W>1.5
                elif index==10:
                    baseline=parameters['pressure_baseline_hpa']
                    if not isinstance(baseline,(int,float)) or not np.isfinite(baseline):status='underspecified_rule'
                    else:trigger=W<1 and P>=baseline and pm25>120 and np.all(np.diff(history('pm25_ug_m3',21600))>0)
                else:
                    threshold=parameters['cold_front_rh_delta_pct']
                    if not isinstance(threshold,(int,float)) or not np.isfinite(threshold) or threshold<0:status='underspecified_rule'
                    else:trigger=delta('temperature_c',3600)<=-4 and delta('pressure_hpa',3600)>=1.5 and W>=6 and abs(delta('relative_humidity_pct',3600))>=threshold
                if index in [8,9] and ratio is None:status='invalid_pm_ratio';trigger=None
            case=hashlib.sha256((identity+name+end.isoformat()+hashlib.sha256(canonical_bytes(parameters)).hexdigest()).encode()).hexdigest()[:20]
            output.append(dict(evaluation_case_id='rulecase_'+case,event_id=name,start_time_utc=(end-pd.Timedelta(seconds=span)).isoformat(),end_time_utc=end.isoformat(),
                               node_id=identity,rule_version='requested_matrix_v1',rule_config_sha256=hashlib.sha256(canonical_bytes(parameters)).hexdigest(),
                               input_channels=list(channels),resolution_seconds=resolution,source_resolution_seconds=cadence,expected_outcome='unknown',
                               rule_output=bool(trigger) if trigger is not None and status=='pattern_evaluated' else None,status=status,reason=reason,
                               evidence_quality='independent_evidence_unavailable',evidence_kind='input_generated_rule',training_label_admissible=False,
                               derived_features=dict(dewpoint_c=dew,heat_index_c=hi,vpd_kpa=vpd,pm25_pm10_ratio=ratio),disaster_outputs='DISABLED'))
    return output


def compare_legacy(records,parameters=None):
    requested=evaluate(records,parameters);result=[]
    canonical=[observation(r) for r in records]
    for node in sorted({r['node_id'] for r in canonical}):
        rows=[r for r in canonical if r['node_id']==node]
        if {r['sample_interval_seconds'] for r in rows}!={3600}:legacy=None
        else:
            frame=pd.DataFrame(rows).pivot(index='timestamp_utc',columns='channel',values='value').reindex(columns=RAW_SENSOR_COLUMNS).reset_index()
            frame['location_id']=node;legacy=apply_event_labels(derive_event_features(frame)).iloc[-1]
        for row in [r for r in requested if r['node_id']==node]:
            old=None if legacy is None or pd.isna(legacy[row['event_id']]) else bool(legacy[row['event_id']])
            reasons=[]
            if row['status']!='pattern_evaluated':reasons.append(row['status']+': '+str(row['reason']))
            if row['event_id']=='light_moderate_rain':reasons.append('Legacy accepts zero PM change; requested requires strict decrease')
            if row['event_id']=='severe_rainstorm_squall':reasons.append('Legacy hourly drop lacks 15min pressure jump; pre-drop window unspecified')
            if row['event_id']=='extreme_heatwave':reasons.append('Legacy T>=35 OR HI>=41; requested category-specific threshold AND 6h HI duration')
            if row['event_id']=='smog_inversion_trap':reasons.append('Legacy fixed station P>=1010; requested local baseline requires documented parameter')
            result.append({**row,'legacy_rule_version':'legacy_hourly_v1','legacy_output':old,'disagree':old!=row['rule_output'] if old is not None and row['rule_output'] is not None else None,'difference_reasons':reasons})
    return result

"""Strict local-source adapters into provenance-bearing long-form observations.

No API credentials loaded. Provider exports must be acquired legitimately.
Unknown units, timezone, rights and pressure reference remain quarantined.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
from ml.datasets.registry import digest,insert_rows
from ml.six_sensor_forecast.contract import PHYSICAL_RANGES
from ml.datasets.noaa import VARIABLES,qc_good

UNITS={'temperature_c':'degC','relative_humidity_pct':'%','pressure_hpa':'hPa','wind_speed_mps':'m/s','pm25_ug_m3':'ug/m3','pm10_ug_m3':'ug/m3'}


def canonical(value,unit,variable):
    value=float(value)
    if unit==UNITS[variable]:return value
    transforms={('K','temperature_c'):lambda v:v-273.15,('Pa','pressure_hpa'):lambda v:v/100,
        ('kPa','pressure_hpa'):lambda v:v*10,('mb','pressure_hpa'):lambda v:v,('C','temperature_c'):lambda v:v,('km/h','wind_speed_mps'):lambda v:v/3.6}
    if (unit,variable) not in transforms:raise ValueError('Unverified unit conversion')
    return transforms[unit,variable](value)


def ingest_frame(db,frame,path,source_id,columns,stations,time_column='timestamp',units=None,pressure_reference='unknown',qc=None,derivations=None,mode='observed'):
    if not columns or not set(columns.values())<=set(UNITS):raise ValueError('Explicit known channel mapping required')
    if db.execute('SELECT 1 FROM sources WHERE source_id=?',(source_id,)).fetchone() is None:raise ValueError('Unknown source')
    source=dict(zip([d[0] for d in db.execute('SELECT * FROM sources LIMIT 0').description],db.execute('SELECT * FROM sources WHERE source_id=?',(source_id,)).fetchone()))
    stations=stations.set_index('location_id',verify_integrity=True);sha=digest(path)
    db.execute('INSERT OR IGNORE INTO raw_files VALUES (?,?,?,?,?)',(sha,source_id,str(path),Path(path).stat().st_size,None))
    duplicate=frame.duplicated(['location_id',time_column],keep=False) if len(frame) else pd.Series(dtype=bool)
    batch=[];counts={'approved':0,'quarantined':0}
    for index,row in enumerate(frame.to_dict('records'),2):
        sid=str(row.get('location_id',''));flags=[];metadata={}
        if duplicate.iloc[index-2]:flags.append('DUPLICATE_STATION_TIME')
        if sid not in stations.index:flags.append('UNRESOLVED_STATION')
        else:metadata=stations.loc[sid].to_dict()
        time=None
        try:
            stamp=pd.Timestamp(row[time_column])
            if pd.isna(stamp):raise ValueError('Missing time')
            if stamp.tzinfo is None:
                if not source['timezone_verified']:raise ValueError('Unverified timezone')
                stamp=stamp.tz_localize(source['timezone'],ambiguous='raise',nonexistent='raise')
            time=stamp.tz_convert('UTC').isoformat()
        except (KeyError,TypeError,ValueError):flags.append('TIME_UNRESOLVED')
        if not source['timezone_verified']:flags.append('TIMEZONE_UNVERIFIED')
        if source['interval_semantics']!='instant':flags.append('INTERVAL_SEMANTICS_UNVERIFIED')
        if source['license_class']=='unresolved':flags.append('LICENSE_UNRESOLVED')
        for raw,variable in columns.items():
            local=list(flags);value=None;unit=(units or {}).get(raw,UNITS[variable])
            try:
                value=canonical(row.get(raw),unit,variable)
                lo,hi=PHYSICAL_RANGES[variable]
                if not np.isfinite(value) or not lo<=value<=hi:raise ValueError('Range')
            except (TypeError,ValueError):value=None;local.append('INVALID_VALUE_OR_UNIT')
            if qc is not None and not qc[raw].iloc[index-2]:local.append('PROVIDER_QC_FAILED_OR_UNKNOWN')
            ref='not_applicable'
            if variable=='pressure_hpa':
                ref=pressure_reference
                if not (mode=='modeled' and ref=='grid_surface') and (ref!='station' or not source['pressure_verified']):local.append('PRESSURE_REFERENCE_UNVERIFIED')
            lat=metadata.get('latitude');lon=metadata.get('longitude')
            try:
                from ml.spatial_ensemble.model import coordinates
                lat,lon=coordinates(lat,lon)
            except ValueError:lat=lon=None;local.append('INVALID_COORDINATES')
            if metadata.get('geography_status')=='COUNTRY_LOCATION_CONFLICT':local.append('COUNTRY_LOCATION_CONFLICT')
            if 'LATITUDE' in row and 'LONGITUDE' in row:
                try:
                    if abs(float(row['LATITUDE'])-lat)>0.01 or abs(float(row['LONGITUDE'])-lon)>0.01:local.append('STATION_LOCATION_MISMATCH')
                except (TypeError,ValueError):local.append('INVALID_REPORTED_COORDINATES')
            local=sorted(set(local));status='quarantined' if local else 'approved';counts[status]+=1
            batch.append(dict(record_id=hashlib.sha256(f'{source_id}:{sha}:{row.get("raw_record_index",index-2)}:{variable}'.encode()).hexdigest(),source_id=source_id,raw_sha256=sha,source_row_id=str(row.get('raw_record_index',index-2)),
                station_id=sid,physical_site_id=metadata.get('physical_site_id',sid),instrument_id=None,
                latitude_deg=lat,longitude_deg=lon,elevation_m=metadata.get('elevation_m') if pd.notna(metadata.get('elevation_m')) else None,
                elevation_datum=metadata.get('elevation_datum'),elevation_source_id=None,elevation_asset_sha256=metadata.get('elevation_asset_sha256'),
                source_timestamp=str(row.get(time_column,'')),interval_start_utc=time,interval_end_utc=time,available_at_utc=time,
                source_metadata_json=json.dumps({key:(None if pd.isna(row[key]) else row[key]) for key in row if key.startswith(raw+'_') or key=='raw_record_index'},default=str,allow_nan=False),
                variable=variable,value=value,unit=UNITS[variable],original_value=str(row.get(raw)),original_unit=unit,
                pressure_reference=ref,measurement_height_m=None,qc_flags=json.dumps(local),observed_or_modeled=mode,uncertainty=None,status=status))
            if len(batch)>=10000:insert_rows(db,batch);db.commit();batch=[]
    insert_rows(db,batch);db.commit();return counts


def noaa(db,path,stations):
    frame=pd.read_parquet(path);frame['location_id']=frame.STATION
    # Native RH may be NOAA-derived (Measurement_Code D). Preserve the raw source,
    # do not relabel this as independent measured ground truth.
    return ingest_frame(db,frame,path,'noaa_ghcnh',VARIABLES,stations,time_column='DATE',pressure_reference='station',qc={v:qc_good(frame,v) for v in VARIABLES})


def provider_export(db,path,source_id,mapping,stations,time_column,units,pressure_reference='unknown'):
    """UCI/CPCB/Delhi/IMD/POWER/OpenAQ/Sensor.Community/CAMS export entry point.
    Explicit mappings required; no generic guessing of column names or units.
    Registry evidence gates training views even if a caller supplies aware dates.
    """
    return ingest_frame(db,pd.read_csv(path),path,source_id,mapping,stations,time_column,units,pressure_reference)


def uci_csv(db,path,stations):
    """Native PRSA station CSV; coordinates must be supplied independently.
    Raw row/DEWP/TEMP ancestry is retained for derived RH.
    """
    frame=pd.read_csv(path);frame['location_id']=frame['station']
    frame['timestamp']=pd.to_datetime(frame[['year','month','day','hour']],errors='coerce')
    t=pd.to_numeric(frame.TEMP,errors='coerce');d=pd.to_numeric(frame.DEWP,errors='coerce')
    frame['derived_RH']=100*np.exp(17.625*d/(243.04+d)-17.625*t/(243.04+t))
    frame['derived_RH_derivation']='Magnus from raw TEMP and DEWP; nearest meteorological station, not independent colocated RH'
    return ingest_frame(db,frame,path,'uci_beijing_501',{'TEMP':'temperature_c','derived_RH':'relative_humidity_pct','PRES':'pressure_hpa','WSPM':'wind_speed_mps','PM2.5':'pm25_ug_m3','PM10':'pm10_ug_m3'},stations,pressure_reference='unknown')


def cpcb_csv(db,path,stations,source_id='india_cpcb_kaggle_v2',station_id=None):
    """Existing CPCB/OpenCity exports; refuse ambiguous AT/BP units.
    Local clock and hourly interval are unapproved until provider evidence exists.
    """
    from ml.six_sensor_forecast.audit_india import read_table
    frame=read_table(Path(path));frame['location_id']=station_id or Path(path).stem
    frame['timestamp']=frame['To Date']
    possible={'AT (degree C)':'temperature_c','Temp (degree C)':'temperature_c','RH (%)':'relative_humidity_pct',
        'WS (m/s)':'wind_speed_mps','PM2.5 (ug/m3)':'pm25_ug_m3','PM10 (ug/m3)':'pm10_ug_m3'}
    columns={k:v for k,v in possible.items() if k in frame}
    if len(set(columns.values()))!=len(columns):raise ValueError('Multiple conflicting source channels')
    if not columns:raise ValueError('No explicit-unit weather/particle columns')
    return ingest_frame(db,frame,path,source_id,columns,stations)


def openaq_json(db,path,stations):
    """User-acquired v3 measurements response, per-provider rights still gated.
    No key is requested, read, logged or used by this adapter.
    """
    payload=json.loads(Path(path).read_text());results=payload.get('results')
    if not isinstance(results,list):raise ValueError('Expected OpenAQ v3 results')
    records=[]
    for result in results:
        parameter=result.get('parameter',{});name=parameter.get('name');units=parameter.get('units')
        if name not in ['pm25','pm10']:continue
        if units not in ['µg/m³','ug/m3']:raise ValueError('Unverified OpenAQ units')
        period=result.get('period',{});end=period.get('datetimeTo',{}).get('utc')
        sensor=result.get('sensorsId') or result.get('sensor',{}).get('id')
        records.append({'location_id':str(sensor),'timestamp':end,'value':result.get('value'),'variable':name,
            'value_period':period,'value_provider_metadata':result})
    total={'approved':0,'quarantined':0}
    for name,var in [('pm25','pm25_ug_m3'),('pm10','pm10_ug_m3')]:
        f=pd.DataFrame([r for r in records if r['variable']==name])
        if len(f):
            # Stable raw result indices prevent collisions across optional heads.
            f['raw_record_index']=[results.index(r['value_provider_metadata']) for r in f.to_dict('records')]
            counts=ingest_frame(db,f,path,'openaq',{'value':var},stations,units={'value':'ug/m3'})
            total={k:total[k]+counts[k] for k in total}
    return total


def imd_export(db,path,stations,mapping,units,time_column,pressure_reference='unknown'):
    return provider_export(db,path,'imd_station_catalogue',mapping,stations,time_column,units,pressure_reference)


def sensor_community_export(db,path,stations,mapping,units,time_column):
    return provider_export(db,path,'sensor_community',mapping,stations,time_column,units)


def power_json(db,path,station_id,latitude,longitude):
    payload=json.loads(Path(path).read_text())
    if payload['header'].get('time_standard')!='UTC':raise ValueError('POWER UTC response required; LST is not a timezone')
    params=payload['properties']['parameter'];metadata=payload['parameters']
    mapping={'T2M':'temperature_c','RH2M':'relative_humidity_pct','PS':'pressure_hpa','WS10M':'wind_speed_mps'}
    stamps=sorted(set.intersection(*[set(params[k]) for k in mapping]))
    frame=pd.DataFrame([{**{k:params[k][t] for k in mapping},'timestamp':pd.to_datetime(t,format='%Y%m%d%H',utc=True),'location_id':station_id} for t in stamps])
    stations=pd.DataFrame([dict(location_id=station_id,physical_site_id=station_id,latitude=latitude,longitude=longitude)])
    return ingest_frame(db,frame,path,'nasa_power',mapping,stations,units={k:metadata[k]['units'] for k in mapping},pressure_reference='grid_surface',mode='modeled')

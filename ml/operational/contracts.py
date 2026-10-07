"""Canonical weather records: raw values survive QC, auth is server-derived."""
import json
import math
from datetime import datetime, timezone

from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS, PHYSICAL_RANGES

VERSION='indra_weather_records_v1'
UNITS=dict(zip(RAW_SENSOR_COLUMNS,['degC','%','hPa','ug/m3','ug/m3','m/s']))
CORE=['temperature_c','relative_humidity_pct','pressure_hpa','wind_speed_mps']


def utc(value):
    import pandas as pd
    if not isinstance(value,(str,datetime)):raise ValueError('Explicit timestamp required')
    t=pd.Timestamp(value)
    if pd.isna(t) or t.tzinfo is None:raise ValueError('Unknown clock; explicit timezone required')
    return t.tz_convert('UTC')


def finite(value):
    if isinstance(value,bool):raise ValueError('Boolean is not a measurement')
    v=float(value)
    if not math.isfinite(v):raise ValueError('Nonfinite measurement')
    return v


def unit_value(raw,unit,channel):
    value=finite(raw)
    if unit==UNITS[channel]:return value
    conversions={('K','temperature_c'):lambda v:v-273.15,('C','temperature_c'):lambda v:v,
                 ('Pa','pressure_hpa'):lambda v:v/100,('kPa','pressure_hpa'):lambda v:v*10,
                 ('mb','pressure_hpa'):lambda v:v,('km/h','wind_speed_mps'):lambda v:v/3.6,
                 ('µg/m³','pm25_ug_m3'):lambda v:v,('µg/m³','pm10_ug_m3'):lambda v:v}
    if (unit,channel) not in conversions:raise ValueError('Unverified unit; never infer from magnitude')
    return conversions[(unit,channel)](value)


def observation(record,authenticated=False,received_at=None):
    required={'node_id','timestamp_utc','latitude','longitude','elevation_m','channel','value','unit','source','sensor_model'}
    if not isinstance(record,dict) or not required<=set(record):raise ValueError('Observation fields missing')
    for key in ['node_id','source','sensor_model']:
        if not isinstance(record[key],str) or not record[key].strip() or len(record[key])>200:raise ValueError('Invalid identity/source')
    c=record['channel']
    if c not in RAW_SENSOR_COLUMNS:raise ValueError('Unknown weather channel')
    t=utc(record['timestamp_utc']);lat,lon=finite(record['latitude']),finite(record['longitude'])
    if not -90<=lat<=90 or not -180<=lon<=180:raise ValueError('Invalid WGS84 coordinates')
    z=None;datum=record.get('elevation_datum','unknown');flags=[]
    if record['elevation_m'] is not None:
        try:
            z=finite(record['elevation_m'])
            if datum!='EGM96' or not -450<=z<=9000:z=None;flags.append('elevation_unverified')
        except (ValueError,TypeError):flags.append('elevation_unverified')
    original=record['value'];value=None
    if original is None:quality='missing'
    else:
        try:
            value=unit_value(original,record['unit'],c)
            if not PHYSICAL_RANGES[c][0]<=value<=PHYSICAL_RANGES[c][1]:value=None;quality='rejected_out_of_range'
            else:quality='valid'
        except (ValueError,TypeError):quality='rejected_value_or_unit'
    if value is not None and c=='temperature_c' and 'bme280' in record['sensor_model'].lower() and not -40<=value<=85:
        value=None;quality='rejected_sensor_operating_range'
    reference=record.get('pressure_reference','unknown')
    if c=='pressure_hpa' and reference!='station':value=None;quality='rejected_pressure_reference'
    if record.get('quality_flag') in ['rejected','missing','uncertain']:
        value=None;quality='provider_'+record['quality_flag']
    available=utc(received_at or record.get('available_at_utc') or t.isoformat())
    if available<t:raise ValueError('Receipt precedes observation; cannot backdate availability')
    interval=record.get('sample_interval_seconds',3600)
    if type(interval) is not int or not 1<=interval<=86400:raise ValueError('Invalid declared sampling interval')
    # JSON forbids NaN/inf; retain the raw representation rather than zero/clip.
    if isinstance(original,float) and not math.isfinite(original):original=repr(original)
    return dict(schema_version=VERSION,node_id=record['node_id'],timestamp_utc=t.isoformat(),available_at_utc=available.isoformat(),
                latitude=lat,longitude=lon,elevation_m=z,elevation_datum=datum,channel=c,raw_value=original,raw_unit=record['unit'],
                value=value,unit=UNITS[c],quality_flag=quality,quality_flags=flags,source=record['source'],authenticated=authenticated is True,
                ingestion_version=VERSION,model_version='not_applicable_observation',sensor_model=record['sensor_model'],pressure_reference=reference,sample_interval_seconds=interval)


def prediction(grid_id,channel,time,estimate,model_version,sources,status,interval=None,uncertainty_type=None):
    value=None if estimate is None else finite(estimate)
    lower=upper=None
    if interval is not None:
        if len(interval)!=2 or value is None:raise ValueError('Interval requires a valid estimate and two bounds')
        lower,upper=map(finite,interval)
        if not lower<=value<=upper or not uncertainty_type:raise ValueError('Invalid/unnamed uncertainty interval')
    return dict(schema_version=VERSION,grid_id=grid_id,valid_time_utc=utc(time).isoformat(),channel=channel,unit=UNITS[channel],
                estimate=value,lower=lower,upper=upper,uncertainty_available=interval is not None,
                uncertainty_type=uncertainty_type if interval is not None else 'unavailable',model_version=model_version,
                feature_sources=sources,status_flag=status)


def schemas():
    obs=observation(dict(node_id='schema',timestamp_utc='2026-10-06T00:00:00Z',latitude=31.,longitude=77.,elevation_m=None,
                         channel='temperature_c',value=None,unit='degC',source='schema',sensor_model='unknown'))
    pred=prediction('schema','temperature_c','2026-10-06T00:00:00Z',None,'schema',[], 'unavailable')
    def spec(example,title):
        properties={}
        for key,value in example.items():
            if key in ['value','estimate','raw_value']:kind=['number','string','null'] if key=='raw_value' else ['number','null']
            elif key in ['elevation_m','lower','upper']:kind=['number','null']
            elif type(value) is bool:kind='boolean'
            elif type(value) is int:kind='integer'
            elif type(value) is float:kind='number'
            elif isinstance(value,list):kind='array'
            else:kind='string'
            properties[key]={'type':kind}
        properties['channel']['enum']=RAW_SENSOR_COLUMNS
        return {'$schema':'https://json-schema.org/draft/2020-12/schema','title':title,'type':'object','additionalProperties':False,'required':list(example),'properties':properties}
    return {'observation':spec(obs,'INDRA canonical observation v1'),'prediction':spec(pred,'INDRA canonical prediction v1')}


def canonical_bytes(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def now_utc():return datetime.now(timezone.utc).isoformat()

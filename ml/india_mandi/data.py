"""Versioned public Mandi model-grid snapshots, never relabeled as sensor observations."""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import ssl
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

from ml.paths import read_config
from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS
from ml.six_sensor_forecast.data import SCHEMA, sha256

ROOT=Path(__file__).resolve().parents[2]
ENDPOINTS={'weather':'https://archive-api.open-meteo.com/v1/archive',
           'air':'https://air-quality-api.open-meteo.com/v1/air-quality'}
WEATHER={'temperature_c':'temperature_2m','relative_humidity_pct':'relative_humidity_2m',
         'pressure_hpa':'surface_pressure','wind_speed_mps':'wind_speed_10m'}
AIR={'pm25_ug_m3':'pm2_5','pm10_ug_m3':'pm10'}


def load_config(path):
    cfg=read_config(path)
    if cfg.get('schema_version')!='indra_mandi_modeled_forecast_v1' or cfg.get('country_code')!='IN':
        raise ValueError('India-only Mandi modeled-data configuration required')
    if (cfg.get('latitude'),cfg.get('longitude'))!=(31.71,76.93):
        raise ValueError('This version fixes the Mandi query location')
    if cfg.get('evidence_kind')!='MODELED_GRID_RETROSPECTIVE' or cfg.get('deployment_approved') is not False or cfg.get('hazard_training_allowed') is not False:
        raise ValueError('Retrospective modeled evidence cannot authorize field/disaster training')
    start,end=date.fromisoformat(cfg['start_date']),date.fromisoformat(cfg['end_date'])
    v,t,f=[pd.Timestamp(cfg[k]) for k in ['validation_start','test_start','fresh_test_start']]
    if not start<end or any(x.tzinfo is None or x.utcoffset().total_seconds()!=0 for x in [v,t,f]) or not pd.Timestamp(start,tz='UTC')<v<t<=f<=pd.Timestamp(end,tz='UTC'):
        raise ValueError('Ordered source/split dates required')
    if cfg['weather_model']!='ecmwf_ifs' or cfg['air_domain']!='cams_global' or cfg['horizon_hours']!=6:
        raise ValueError('Unexpected source or forecast contract')
    if cfg['teacher_max_rounds']<1 or cfg['threads']<1 or not cfg['ridge_alpha_candidates'] or any(not np.isfinite(a) or a<=0 for a in cfg['ridge_alpha_candidates']):
        raise ValueError('Invalid fitting candidates')
    for key in ['data','models','reports']:
        p=(ROOT/cfg[key]).resolve()
        if not p.is_relative_to(ROOT):raise ValueError('Outputs must stay inside the repository')
        cfg[key]=str(p)
    cfg['_config_sha256']=sha256(Path(path))
    return cfg


def month_windows(start,end):
    current=date.fromisoformat(start);stop=date.fromisoformat(end)
    while current<=stop:
        last=min(stop,date(current.year,current.month,calendar.monthrange(current.year,current.month)[1]))
        yield current,last
        current=last+timedelta(days=1)


def fetch(kind,params,cache,offline=False):
    url=ENDPOINTS[kind]+'?'+urllib.parse.urlencode(params)
    path=Path(cache)/(kind+'_'+hashlib.sha256(url.encode()).hexdigest()[:20]+'.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        if offline:raise FileNotFoundError('Missing cached public response: '+url)
        try:
            import certifi
            context=ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            context=ssl.create_default_context()
        for attempt in range(3):
            try:
                request=urllib.request.Request(url,headers={'User-Agent':'INDRA-India-research/1.0'})
                with urllib.request.urlopen(request,context=context,timeout=45) as response:
                    raw=response.read(20_000_001)
                value=json.loads(raw)
                if len(raw)>20_000_000 or value.get('error') or 'hourly' not in value:
                    raise ValueError(value.get('reason','Invalid/oversized API response'))
                path.write_bytes(raw)
                break
            except OSError:
                if attempt==2:raise
                time.sleep(2+attempt)
    value=json.loads(path.read_text())
    if value.get('error') or value.get('utc_offset_seconds')!=0:
        raise ValueError('Valid UTC response required')
    return value,dict(url=url,raw_file=path.relative_to(ROOT).as_posix(),sha256=sha256(path),
                     returned_latitude=value.get('latitude'),returned_longitude=value.get('longitude'),
                     elevation=value.get('elevation'),units=value.get('hourly_units'))


def response_frame(value,mapping):
    units=value['hourly_units']
    expected={'temperature_2m':'°C','relative_humidity_2m':'%','surface_pressure':'hPa',
              'wind_speed_10m':'m/s','pm2_5':'µg/m³','pm10':'µg/m³'}
    for name in mapping.values():
        if str(units.get(name)).replace('μ','µ')!=expected[name]:raise ValueError('Unexpected API unit: '+name)
    f=pd.DataFrame(value['hourly'])
    f['timestamp_utc']=pd.to_datetime(f.pop('time'),utc=True)
    if f.timestamp_utc.duplicated().any():raise ValueError('Duplicate API timestamps')
    return f.rename(columns={v:k for k,v in mapping.items()})


def prepare(cfg,offline=False):
    root=Path(cfg['data']);root.mkdir(parents=True,exist_ok=True)
    if (root/'dataset_manifest.json').exists():
        previous=json.loads((root/'dataset_manifest.json').read_text())
        if previous.get('experiment_config_sha256')!=cfg['_config_sha256'] or sha256(root/'observations.csv')!=previous['observations_sha256']:
            raise ValueError('Existing dataset/config differs; choose a new versioned path')
        return previous
    frames,receipts=[],[]
    for start,end in month_windows(cfg['start_date'],cfg['end_date']):
        params=dict(latitude=cfg['latitude'],longitude=cfg['longitude'],start_date=start.isoformat(),end_date=end.isoformat(),timezone='UTC')
        w,wp=fetch('weather',{**params,'models':cfg['weather_model'],'wind_speed_unit':'ms',
                              'hourly':','.join([*WEATHER.values(),'precipitation','snowfall','wind_gusts_10m'])},root/'raw',offline)
        a,ap=fetch('air',{**params,'domains':cfg['air_domain'],'hourly':','.join(AIR.values())},root/'raw',offline)
        expected=pd.date_range(start.isoformat(),end.isoformat()+'T23:00:00',freq='h',tz='UTC')
        f=response_frame(w,WEATHER).merge(response_frame(a,AIR),on='timestamp_utc',how='outer',validate='one_to_one')
        if not pd.DatetimeIndex(f.timestamp_utc).isin(expected).all():raise ValueError('API timestamps outside requested window')
        f=f.set_index('timestamp_utc').reindex(expected).rename_axis('timestamp_utc').reset_index()
        frames.append(f);receipts.append(dict(start_date=start.isoformat(),end_date=end.isoformat(),weather=wp,air=ap))
        print('Mandi API snapshot',start,end,len(f),'hourly positions',flush=True)
    raw=pd.concat(frames,ignore_index=True)
    if raw.timestamp_utc.duplicated().any():raise ValueError('Overlapping source windows')
    observations=raw[['timestamp_utc',*RAW_SENSOR_COLUMNS]].copy()
    observations.insert(1,'location_id','Mandi_OpenMeteo_Grid')
    for name,bounds in PHYSICAL_RANGES.items():
        observations[name]=pd.to_numeric(observations[name],errors='raise').where(lambda x:x.between(*bounds))
    observations.to_csv(root/'observations.csv',index=False)
    raw.to_csv(root/'context.csv',index=False)
    manifest=dict(schema_version=SCHEMA,source_name='Mandi, India: Open-Meteo/ECMWF IFS and CAMS global modeled grid',
                  country_code='IN',evidence_kind='MODELED_GRID_RETROSPECTIVE',requested_latitude=cfg['latitude'],requested_longitude=cfg['longitude'],
                  source_url='https://open-meteo.com/',license='CC BY 4.0; provider attribution required',
                  attribution='Open-Meteo; ECMWF IFS; Copernicus Atmosphere Monitoring Service (CAMS) global atmospheric composition forecasts',
                  weather_documentation='https://open-meteo.com/en/docs/historical-weather-api',air_documentation='https://open-meteo.com/en/docs/air-quality-api',
                  retrieved_at_utc=datetime.now(timezone.utc).isoformat(),experiment_config_sha256=cfg['_config_sha256'],
                  observations_sha256=sha256(root/'observations.csv'),context_sha256=sha256(root/'context.csv'),
                  sensor_columns=RAW_SENSOR_COLUMNS,rows=len(observations),locations=['Mandi_OpenMeteo_Grid'],
                  coverage_start_utc=observations.timestamp_utc.min().isoformat(),coverage_end_utc=observations.timestamp_utc.max().isoformat(),
                  complete_six_channel_rows=int(np.isfinite(observations[RAW_SENSOR_COLUMNS].to_numpy()).all(axis=1).sum()),
                  missing_measurements={k:int(v) for k,v in observations[RAW_SENSOR_COLUMNS].isna().sum().items()},
                  pressure_reference='MODELED_GRID_SURFACE; not verified station pressure',
                  temporal_resolution='Hourly API positions; CAMS global underlying product is 3-hourly, approximately 45 km',
                  co_location='Different weather/air grids; returned grid coordinates recorded in each receipt; no physical co-location claim',
                  label_provenance='Exact +6h modeled values, no observed hazard labels',
                  original_issue_time_availability='Not verified; retrospective benchmark, not replay of information known at original issue time',
                  geographically_independent_validation=False,deployment_approved=False,hazard_training_allowed=False,
                  source_receipts=receipts,china_rows_used=0,china_weights_used=False)
    (root/'dataset_manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    return manifest

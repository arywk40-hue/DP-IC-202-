"""Local-only ERA5 normalization and exact backward joins; never Track S inputs."""
import json
from contextlib import ExitStack
from pathlib import Path

import numpy as np
import pandas as pd

from ml.datasets.registry import digest
from ml.hazard_context.events import utc
from ml.hazard_context.output import new_file

VARIABLES={'t2m':('K','era5_temperature_c'),'d2m':('K','era5_dewpoint_c'),
           'sp':('Pa','era5_surface_pressure_hpa'),'u10':('m s**-1','era5_u10_mps'),'v10':('m s**-1','era5_v10_mps')}
FEATURES=[v[1] for v in VARIABLES.values()]+['era5_wind_speed_mps','era5_relative_humidity_pct','era5_dewpoint_depression_c']
MODES={'retrospective_background_context','availability_verified_context'}


def verify_requests(path='data/registry/cds_physics_requests.json'):
    import calendar
    jobs=json.loads(Path(path).read_text())['requests'];seen=set()
    for job in jobs:
        r=job['request'];year,month=int(r['year']),int(r['month'])
        if job['dataset']!='reanalysis-era5-land' or year not in [2023,2024] or not 1<=month<=12 or (year,month) in seen:
            raise ValueError('Unexpected/duplicate ERA5 period')
        if r['day']!=[f'{d:02d}' for d in range(1,calendar.monthrange(year,month)[1]+1)] or r['time']!=[f'{h:02d}:00' for h in range(24)]:
            raise ValueError('Incorrect calendar/hour coverage')
        expected=['2m_temperature','2m_dewpoint_temperature','surface_pressure','10m_u_component_of_wind','10m_v_component_of_wind']
        if r['variable']!=expected or r['area']!=[38,68,6,98.5] or r['data_format']!='netcdf' or r['download_format']!='unarchived' or r['product_type']!=['reanalysis']:
            raise ValueError('Request differs from frozen specification')
        seen.add((year,month))
    if len(seen)!=24:raise ValueError('All 24 monthly requests required')
    return {'requests':24,'years':[2023,2024],'variables':expected,'request_sha256':digest(path),'authenticated_submission_verified':False}


def coordinate_contract(ds,selectors=None):
    names={}
    for canonical,aliases in {'latitude':['latitude','lat'],'longitude':['longitude','lon'],'time':['valid_time','time']}.items():
        present=[n for n in aliases if n in ds.dims]
        if len(present)!=1:raise ValueError('Unambiguous time/latitude/longitude dimensions required')
        if present[0]!=canonical:names[present[0]]=canonical
    ds=ds.rename(names)
    for dim in list(ds.dims):
        if dim in ['time','latitude','longitude']:continue
        if dim in (selectors or {}):ds=ds.sel({dim:selectors[dim]},drop=True)
        elif ds.sizes[dim]==1:ds=ds.isel({dim:0},drop=True)
        else:raise ValueError('Ambiguous ERA5 member/version dimension requires explicit selection: '+dim)
    for name in ['latitude','longitude']:
        values=np.asarray(ds[name].values,dtype=float)
        if values.ndim!=1 or not np.isfinite(values).all() or len(values)<2:raise ValueError('Finite rectilinear grid required')
    if np.abs(ds.latitude.values).max()>90 or ds.longitude.values.min()<-180 or ds.longitude.values.max()>360:
        raise ValueError('Invalid grid coordinates')
    ds=ds.assign_coords(longitude=((ds.longitude+180)%360)-180).sortby('latitude').sortby('longitude').sortby('time')
    for key in ['time','latitude','longitude']:
        if not pd.Index(ds[key].values).is_unique:raise ValueError('Duplicate grid coordinate/time')
    t=pd.DatetimeIndex(ds.time.values)
    if t.hasnans or t.tz is not None or (t!=t.floor('h')).any():raise ValueError('CF-decoded UTC exact hourly instants required')
    # CF naive datetime values are UTC by ERA5 provider contract; arbitrary local CSV clocks are not inferred.
    for name,(unit,_) in VARIABLES.items():
        if name not in ds or set(ds[name].dims)!={'time','latitude','longitude'}:raise ValueError('Missing/unsupported ERA5 variable: '+name)
        allowed={'m s**-1','m s-1','m/s'} if unit=='m s**-1' else {unit}
        if ds[name].attrs.get('units') not in allowed:raise ValueError('Unverified ERA5 units for '+name)
    return ds


def sample(ds,lat,lon):
    if not np.isfinite([lat,lon]).all() or not -90<=lat<=90 or not -180<=lon<=180:raise ValueError('Invalid query coordinates')
    if not ds.latitude.values[0]<=lat<=ds.latitude.values[-1] or not ds.longitude.values[0]<=lon<=ds.longitude.values[-1]:
        return {name:np.full(ds.sizes['time'],np.nan) for _,name in VARIABLES.values()},'OUTSIDE_GRID'
    yi=min(max(int(np.searchsorted(ds.latitude.values,lat))-1,0),ds.sizes['latitude']-2)
    xi=min(max(int(np.searchsorted(ds.longitude.values,lon))-1,0),ds.sizes['longitude']-2)
    # Crop before loading: bounded four-pixel extraction, not a full India-year materialization.
    tile=ds.isel(latitude=slice(yi,yi+2),longitude=slice(xi,xi+2))
    yf=(lat-float(tile.latitude.values[0]))/float(tile.latitude.values[1]-tile.latitude.values[0])
    xf=(lon-float(tile.longitude.values[0]))/float(tile.longitude.values[1]-tile.longitude.values[0])
    weights=np.array([[(1-yf)*(1-xf),(1-yf)*xf],[yf*(1-xf),yf*xf]])
    out={}
    for variable,(_,name) in VARIABLES.items():
        a=np.asarray(tile[variable].transpose('time','latitude','longitude').values,dtype=float)
        # A missing zero-weight corner is irrelevant at an exact valid grid pixel.
        with np.errstate(invalid='ignore'):
            weighted=np.where(weights[None,:,:]>0,a*weights,0)
        missing=np.any((weights[None,:,:]>0)&~np.isfinite(a),axis=(1,2))
        value=np.sum(weighted,axis=(1,2));value[missing]=np.nan
        out[name]=value-273.15 if variable in ['t2m','d2m'] else value/100 if variable=='sp' else value
    return out,'GRID_CONTEXT'


def normalize_files(paths,stations,metadata,output=None,selectors=None):
    import xarray as xr
    if stations.empty or stations.physical_site_id.duplicated().any():raise ValueError('Unique physical sites required')
    if metadata.get('country')!='IN' or metadata.get('provider')!='ECMWF/Copernicus' or metadata.get('dataset')!='era5_land':
        raise ValueError('Explicit India ERA5 provenance required')
    for key in ['version','retrieved_at','license','rights_status','rights_evidence_uri']:
        if not metadata.get(key):raise ValueError('Background metadata incomplete: '+key)
    utc(metadata['retrieved_at'])
    paths=[Path(p) for p in paths]
    if not paths:raise ValueError('No ERA5 files; do not fabricate background rows')
    results=[];hashes={str(p):digest(p) for p in paths}
    with ExitStack() as stack:
        datasets=[]
        for path in paths:
            if path.suffix not in ['.nc','.nc4']:raise ValueError('Extract a legitimate NetCDF export first; GRIB/ZIP not silently converted')
            datasets.append(stack.enter_context(xr.open_dataset(path,decode_times=True,mask_and_scale=True)))
        # Complete monthly files processed separately. Partial variable files must share exact coordinates.
        ancestors=[[hashes[str(p)]] for p in paths]
        if any(not set(VARIABLES)<=set(ds.data_vars) for ds in datasets):
            owned=[name for ds in datasets for name in VARIABLES if name in ds]
            if len(owned)!=len(set(owned)):raise ValueError('Ambiguous partial files; merge explicit periods separately')
            datasets=[xr.merge(datasets,join='exact',compat='no_conflicts')]
            ancestors=[sorted(hashes.values())]
        for ds,origin in zip(datasets,ancestors):
            ds=coordinate_contract(ds,selectors)
            for site in stations.to_dict('records'):
                values,quality=sample(ds,float(site['latitude']),float(site['longitude']))
                frame=pd.DataFrame(values)
                for name,low,high in [('era5_temperature_c',-100,80),('era5_dewpoint_c',-100,80),('era5_surface_pressure_hpa',100,1200),('era5_u10_mps',-200,200),('era5_v10_mps',-200,200)]:
                    frame[name]=frame[name].where(frame[name].between(low,high))
                t,d=frame.era5_temperature_c,frame.era5_dewpoint_c
                frame['era5_wind_speed_mps']=np.hypot(frame.era5_u10_mps,frame.era5_v10_mps)
                frame['era5_relative_humidity_pct']=(100*np.exp(17.625*d/(243.04+d)-17.625*t/(243.04+t))).clip(0,100)
                frame['era5_dewpoint_depression_c']=t-d
                frame['timestamp_utc']=pd.to_datetime(ds.time.values,utc=True)
                frame['station_id']=site['location_id'];frame['physical_site_id']=site['physical_site_id']
                frame['era5_available_at_utc']=None
                frame['era5_source_hashes']=json.dumps(sorted(origin))
                frame['era5_quality_flag']=np.where(frame[FEATURES].isna().any(axis=1),'MISSING_OR_OUTSIDE_GRID',quality)
                results.append(frame)
    result=pd.concat(results,ignore_index=True).sort_values(['physical_site_id','timestamp_utc']).reset_index(drop=True)
    if result.duplicated(['physical_site_id','timestamp_utc']).any():raise ValueError('Duplicate monthly station/time; quarantine conflicting exports')
    manifest={**metadata,'raw_file_sha256':hashes,'rows':len(result),'variables':FEATURES,'grid_pressure_reference':'grid_surface_not_station_or_sea_level',
              'mode':'retrospective_background_context','used_for_training':False,'used_for_validation':False,'used_for_labels':False,
              'geographic_range':{c:[float(stations[c].min()),float(stations[c].max())] for c in ['latitude','longitude']},
              'time_range':[result.timestamp_utc.min().isoformat(),result.timestamp_utc.max().isoformat()],
              'selectors':selectors or {},'alignment':'instantaneous provider fields; UTC coordinate by documented ERA5 contract',
              'indirect_station_assimilation':'ERA5 atmospheric forcing can contain held-out observations; geographical holdout is not fully independent'}
    if output:
        p=new_file(output);new_file(p.with_suffix('.manifest.json'));result.to_parquet(p,index=False)
        manifest['normalized_sha256']=digest(p)
        p.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    return result,manifest


def join_context(observations,background,mode='retrospective_background_context'):
    if mode not in MODES:raise ValueError('Context mode must be explicit')
    if not observations.country_code.eq('IN').all():raise ValueError('India-only context')
    if any(c.startswith('era5_') for c in observations):raise ValueError('Background cannot already contaminate Track S')
    required={'physical_site_id','timestamp_utc','era5_available_at_utc',*FEATURES}
    if not required<=set(background):raise ValueError('Background schema incomplete')
    obs=observations.copy();b=background.copy()
    obs['timestamp_utc']=[utc(v) for v in obs.timestamp_utc]
    b['timestamp_utc']=[utc(v) for v in b.timestamp_utc]
    if b.duplicated(['physical_site_id','timestamp_utc']).any():raise ValueError('Duplicate background station/time')
    obs['era5_sample_time_utc']=obs.timestamp_utc-pd.Timedelta(hours=1)
    b=b.rename(columns={'timestamp_utc':'era5_sample_time_utc'}).drop(columns='station_id',errors='ignore')
    joined=obs.merge(b,on=['physical_site_id','era5_sample_time_utc'],how='left',validate='many_to_one',sort=False)
    if mode=='availability_verified_context':
        verified=[]
        for sample,available,issue in zip(joined.era5_sample_time_utc,joined.era5_available_at_utc,joined.timestamp_utc):
            if pd.isna(available):verified.append(False);continue
            a=utc(available)
            if a<sample:raise ValueError('Publication cannot precede the observation field')
            verified.append(a<=issue)
        joined.loc[~np.array(verified),FEATURES]=np.nan
    joined['context_mode']=mode
    joined['context_alignment']='exact preceding-hour instant; not a measured station hourly average; no nearest/future fill'
    return joined

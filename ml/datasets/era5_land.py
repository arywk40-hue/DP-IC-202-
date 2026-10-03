"""Generate CDS requests; adapt legitimately downloaded ERA5-Land to background.

Never downloads automatically or reads credentials. Hindcast availability is
not live availability: resulting features are unsuitable for online evaluation
unless caller supplies a verified publication/availability timestamp.
"""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd


def request(year,month,area):
    import calendar
    if len(area)!=4 or not area[0]>area[2] or not area[3]>area[1]:raise ValueError('Use [north,west,south,east]')
    return {'dataset':'reanalysis-era5-land','request':{'variable':['2m_temperature','2m_dewpoint_temperature','surface_pressure','10m_u_component_of_wind','10m_v_component_of_wind'],
        'year':str(year),'month':f'{month:02d}','day':[f'{d:02d}' for d in range(1,calendar.monthrange(year,month)[1]+1)],
        'time':[f'{h:02d}:00' for h in range(24)],'area':area,'data_format':'netcdf','download_format':'unarchived'}}


def background(path,latitude,longitude,timestamp,available_at_utc=None):
    import xarray as xr
    stamp=pd.Timestamp(timestamp)
    if stamp.tzinfo is None:raise ValueError('Explicit UTC time required')
    with xr.open_dataset(path) as ds:
        tc='valid_time' if 'valid_time' in ds.coords else 'time'
        wanted=np.datetime64(stamp.tz_convert('UTC').tz_localize(None).to_datetime64())
        # Exact time only: no nearest future timestamp, no extrapolation.
        selected=ds.sel({tc:wanted}).interp(latitude=float(latitude),longitude=float(longitude))
        def v(name,unit):
            if selected[name].attrs.get('units')!=unit:raise ValueError(f'Unverified {name} units')
            value=float(selected[name].values)
            if not np.isfinite(value):raise ValueError('Missing background pixel')
            return value
        t=v('t2m','K')-273.15;dew=v('d2m','K')-273.15;p=v('sp','Pa')/100
        rh=float(np.clip(100*np.exp(17.625*dew/(243.04+dew)-17.625*t/(243.04+t)),0,100))
        wind=float(np.hypot(v('u10','m s**-1'),v('v10','m s**-1')))
    availability=None if available_at_utc is None else pd.Timestamp(available_at_utc)
    if availability is not None and (availability.tzinfo is None or availability>stamp):raise ValueError('Background not available at prediction time')
    return {'features':dict(era5_temperature_c=t,era5_relative_humidity_pct=rh,era5_surface_pressure_hpa=p,era5_wind_speed_mps=wind),
        'source':'era5_land','mode':'hindcast_only' if availability is None else 'availability_verified',
        'grid_pressure_reference':'grid_surface_not_station','grid_resolution_deg':0.1,'available_at_utc':None if availability is None else availability.isoformat()}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--year',type=int,default=2024);p.add_argument('--output',default='data/registry/cds_requests.json');a=p.parse_args()
    jobs=[request(a.year,m,area) for area in [[38,68,6,98.5],[32.5,76,30.5,78]] for m in range(1,13)]
    Path(a.output).write_text(json.dumps({'authentication':'User CDS account, accepted dataset terms and personal API token required. No automatic download.','requests':jobs},indent=2)+'\n')

"""Public NOAA GHCNh India inventory and actual station-year coverage.

Inventory counts are reports, NOT hourly completeness. Actual completeness
is distinct UTC hour bins / all hours in requested calendar year, per variable.
Public unsigned S3 only; atomic downloads check Content-Length and SHA256.
"""
from __future__ import annotations
import argparse, calendar, hashlib, json, urllib.request, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
import pandas as pd

ROOT='https://noaa-ghcnh-pds.s3.amazonaws.com/'
NS={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}
VARIABLES={'temperature':'temperature_c','relative_humidity':'relative_humidity_pct',
           'station_level_pressure':'pressure_hpa','wind_speed':'wind_speed_mps'}


def download(key, path, max_bytes=500_000_000):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.part')
    try:
        with urllib.request.urlopen(ROOT+key,timeout=90) as response, temporary.open('wb') as out:
            expected=response.headers.get('Content-Length');total=0;sha=hashlib.sha256()
            while block:=response.read(1024*1024):
                total+=len(block)
                if total>max_bytes:raise ValueError('Download exceeds bound')
                out.write(block);sha.update(block)
            if expected is not None and total!=int(expected):raise ValueError('Truncated download')
        temporary.replace(path)
        return {'uri':ROOT+key,'bytes':total,'sha256':sha.hexdigest()}
    finally:
        temporary.unlink(missing_ok=True)


def keys(prefix):
    from urllib.parse import urlencode
    token=None
    while True:
        query={'list-type':'2','prefix':prefix,'max-keys':1000}
        if token:query['continuation-token']=token
        with urllib.request.urlopen(ROOT+'?'+urlencode(query),timeout=90) as r:root=ET.fromstring(r.read())
        for entry in root.findall('s:Contents',NS):yield entry.findtext('s:Key',namespaces=NS)
        if root.findtext('s:IsTruncated',namespaces=NS)!='true':break
        token=root.findtext('s:NextContinuationToken',namespaces=NS)
        if not token:raise ValueError('Truncated listing lacks continuation')


def qc_good(frame, variable):
    """Fail closed on unrecognized legacy QC; blank general QC passes.
    Legacy digits are accepted only for documented source families.
    """
    qc=frame.get(variable+'_Quality_Code',pd.Series('',index=frame.index)).fillna('').astype(str).str.strip()
    source=frame.get(variable+'_Source_Code',pd.Series('',index=frame.index)).fillna('').astype(str).str.replace(r'\.0$','',regex=True)
    old=source.isin(['313','314','315','322','335','343','344','346'])
    legacy=source.isin(['220','221','222','223','347','348'])
    return qc.eq('') | (old & qc.isin(['0','1','4','5','9'])) | (legacy & qc.isin(['1','4']))


def coverage(frame, year):
    date=pd.to_datetime(frame['DATE'],utc=True,errors='coerce')
    inyear=date.dt.year.eq(year)
    result={'raw_reports':len(frame),'valid_time_reports':int(inyear.sum()),
            'distinct_hours':int(date[inyear].dt.floor('h').nunique()),'variables':{}}
    denominator=8784 if calendar.isleap(year) else 8760
    for var in VARIABLES:
        value=pd.to_numeric(frame.get(var,pd.Series(np.nan,index=frame.index)),errors='coerce')
        bounds={'temperature':(-60,60),'relative_humidity':(0,100),'station_level_pressure':(300,1100),'wind_speed':(0,75)}[var]
        good=inyear & value.between(*bounds) & qc_good(frame,var)
        hours=int(date[good].dt.floor('h').nunique())
        result['variables'][var]={'valid_reports':int(good.sum()),'distinct_hours':hours,
            'calendar_hour_completeness':hours/denominator,'denominator_hours':denominator}
    return result


def registry(stations):
    candidates=stations[stations.ISO_CODE.eq('IN')].copy()
    rows=[]
    for row in candidates.itertuples():
        lat,lon=float(row.LATITUDE),float(row.LONGITUDE)
        valid=np.isfinite(lat+lon) and 6<=lat<=38 and 68<=lon<=98.5
        # Exact location aliases share a site; near locations are never silently merged.
        identity=hashlib.sha256(f'{lat:.6f}|{lon:.6f}'.encode()).hexdigest()[:16]
        rows.append(dict(location_id=row.GHCN_ID,physical_site_id='geo_'+identity,
            station_name=row.NAME,latitude=lat,longitude=lon,source='noaa_ghcnh',
            metadata_elevation_m=None if row.ELEVATION==-999.9 else row.ELEVATION,
            elevation_m=None,elevation_source=None,elevation_datum=None,slope_deg=None,
            climate_zone=None,climate_zone_source=None,
            geography_status='candidate_india_bbox' if valid else 'COUNTRY_LOCATION_CONFLICT',
            geography_note='ISO IN candidate; bbox screening is not a verified administrative boundary'))
    return pd.DataFrame(rows)


def screen(output,year=2024,workers=4):
    output=Path(output);raw=output/'raw';raw.mkdir(parents=True,exist_ok=True)
    receipt=download('hourly/doc/ghcnh-station-list.csv',raw/'station-list.csv')
    stations=registry(pd.read_csv(raw/'station-list.csv',keep_default_na=False))
    stations.to_csv(output/'stations.csv',index=False)
    # Stream full inventory; retain just IN lines with a hash of the ENTIRE response.
    sha=hashlib.sha256();total=0;inventory=[]
    with urllib.request.urlopen(ROOT+'hourly/doc/ghcnh-inventory.txt',timeout=120) as r:
        expected=r.headers.get('Content-Length')
        for line in r:
            total+=len(line);sha.update(line)
            if line.startswith(b'IN'):
                parts=line.decode().split()
                if len(parts)==14:inventory.append([parts[0],int(parts[1]),*map(int,parts[2:])])
    if expected and total!=int(expected):raise ValueError('Incomplete inventory stream')
    inv=pd.DataFrame(inventory,columns=['location_id','year',*['month_'+str(i) for i in range(1,13)]])
    inv.to_csv(output/'india_report_inventory.csv',index=False)
    manifest={'station_list':receipt,'inventory':{'uri':ROOT+'hourly/doc/ghcnh-inventory.txt','bytes':total,'sha256':sha.hexdigest()},
        'screen_year':year,'country_candidates':len(stations),'hourly_completeness_scope':'requested year only; historical inventory is report counts'}
    listing=list(keys(f'hourly/access/by-year/{year}/parquet/GHCNh_IN'))
    lookup={k.split('/')[-1].removeprefix('GHCNh_').removesuffix(f'_{year}.parquet'):k for k in listing}
    def station_report(row):
        sid=row.location_id;years=inv[inv.location_id.eq(sid)]
        result={'location_id':sid,'inventory_years':years.year.tolist(),
            'first_inventory_year':int(years.year.min()) if len(years) else None,
            'last_inventory_year':int(years.year.max()) if len(years) else None,
            'inventory_reports':int(years.filter(like='month_').to_numpy().sum()),'measured_year':year}
        if sid not in lookup:return dict(result,status='NO_FILE_FOR_REQUESTED_YEAR')
        try:
            path=raw/lookup[sid].split('/')[-1]
            rec=download(lookup[sid],path,50_000_000)
            frame=pd.read_parquet(path)
            return dict(result,status='OBSERVATIONS_SCREENED',receipt=rec,coverage=coverage(frame,year))
        except Exception as exc:return dict(result,status='DOWNLOAD_OR_PARSE_FAILED',error=f'{type(exc).__name__}: {exc}')
    reports=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i,r in enumerate(pool.map(station_report,stations.itertuples()),1):
            reports.append(r)
            if i%25==0:print('stations screened',i,flush=True)
    manifest['stations']=reports
    (output/'coverage.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',default='data/noaa_ghcnh');p.add_argument('--year',type=int,default=2024)
    a=p.parse_args();screen(a.output,a.year)

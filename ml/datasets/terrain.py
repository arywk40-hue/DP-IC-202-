"""True SRTM GL1 v3 (EGM96) and Köppen-Geiger 1991–2020 point sampling.

Unsigned public assets. Missing pixels fail closed; NOAA catalog elevation is
never passed off as SRTM. Slope is a 3x3 central finite-difference estimate.
"""
from __future__ import annotations
import argparse, math, json
from pathlib import Path
import numpy as np
import pandas as pd

SRTM='https://opentopography.s3.sdsc.edu/raster/SRTM_GL1/SRTM_GL1_srtm/'
CLIMATE='https://data.naturalcapitalalliance.stanford.edu/download/global/koppen_geiger_climatezones/koppen_geiger_climatezones_1991_2020_1km.tif'
CLASSES=['unknown','Af','Am','Aw','BWh','BWk','BSh','BSk','Csa','Csb','Csc','Cwa','Cwb','Cwc','Cfa','Cfb','Cfc','Dsa','Dsb','Dsc','Dsd','Dwa','Dwb','Dwc','Dwd','Dfa','Dfb','Dfc','Dfd','ET','EF']


def tile(latitude,longitude):
    from ml.spatial_ensemble.model import coordinates
    lat,lon=coordinates(latitude,longitude)
    if not -56<=lat<60:raise ValueError('Outside SRTM domain')
    a,b=math.floor(lat),math.floor(lon)
    return f'{"N" if a>=0 else "S"}{abs(a):02d}{"E" if b>=0 else "W"}{abs(b):03d}.tif'


def sample(latitude,longitude,cache='data/terrain',climate=True):
    import rasterio
    from rasterio.windows import Window
    from ml.datasets.noaa import download
    lat,lon=float(latitude),float(longitude);asset=SRTM+tile(lat,lon)
    path=Path(cache)/tile(lat,lon);path.parent.mkdir(parents=True,exist_ok=True)
    receipt_path=path.with_suffix('.receipt.json')
    if not path.exists() or not receipt_path.exists():
        # This archive is tiled but not assumed COG. Download full tile for immutable hash.
        import urllib.request,hashlib
        tmp=path.with_suffix('.part');sha=hashlib.sha256();total=0
        try:
            with urllib.request.urlopen(asset,timeout=60) as r,tmp.open('wb') as f:
                expected=r.headers.get('Content-Length')
                while block:=r.read(1024*1024):
                    total+=len(block)
                    if total>100_000_000:raise ValueError('Terrain tile exceeds size limit')
                    f.write(block);sha.update(block)
                if expected and total!=int(expected):raise ValueError('Truncated terrain tile')
            tmp.replace(path);receipt_path.write_text(json.dumps({'uri':asset,'sha256':sha.hexdigest(),'bytes':total}))
        finally:tmp.unlink(missing_ok=True)
    with rasterio.open(path) as ds:
        row,col=ds.index(lon,lat)
        grid=ds.read(1,window=Window(col-1,row-1,3,3),boundless=True,masked=True)
        if grid.mask.any() or not np.isfinite(grid).all():raise ValueError('SRTM pixel neighborhood missing')
        dx=abs(ds.transform.a)*111320*math.cos(math.radians(lat));dy=abs(ds.transform.e)*111320
        slope=math.degrees(math.atan(math.hypot((float(grid[1,2])-float(grid[1,0]))/(2*dx),(float(grid[2,1])-float(grid[0,1]))/(2*dy))))
        result={'elevation_m':float(grid[1,1]),'slope_deg':slope,'elevation_datum':'EGM96',
            'elevation_source':'srtm_gl1','elevation_asset_sha256':json.loads(receipt_path.read_text())['sha256'],'elevation_asset_uri':asset}
    if climate:
        with rasterio.Env(GDAL_HTTP_TIMEOUT=30,GDAL_HTTP_MAX_RETRY=1,CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif',GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'):
            with rasterio.open(CLIMATE) as ds:
                value=next(ds.sample([(lon,lat)],masked=True))[0]
                if np.ma.is_masked(value) or not 1<=int(value)<=30:raise ValueError('Missing climate class')
                result.update(climate_zone=CLASSES[int(value)],climate_zone_source=CLIMATE)
    return result


def enrich(input_path,output_path,climate=True,cache="data/terrain"):
    from concurrent.futures import ThreadPoolExecutor
    import rasterio
    frame=pd.read_csv(input_path).astype(object);errors=[];groups={}
    for i,row in frame.iterrows():
        try:groups.setdefault(tile(row.latitude,row.longitude),[]).append((i,row))
        except Exception as exc:errors.append({'location_id':row.location_id,'error':str(exc)})
    def group_sample(entries):
        results=[]
        for i,row in entries:
            try:results.append((i,sample(row.latitude,row.longitude,cache=cache,climate=False),None))
            except Exception as exc:results.append((i,{},f'{type(exc).__name__}: {exc}'))
        # Bound disk usage: immutable receipts survive; generated raster is
        # removed after every site in this tile has been sampled.
        if entries:
            first=entries[0][1]
            (Path(cache)/tile(first.latitude,first.longitude)).unlink(missing_ok=True)
        return results
    with ThreadPoolExecutor(max_workers=4) as pool:
        for n,results in enumerate(pool.map(group_sample,groups.values()),1):
            for i,values,error in results:
                for key,value in values.items():
                    if key not in frame:frame[key]=pd.Series(index=frame.index,dtype='object')
                    frame.loc[i,key]=value
                frame.loc[i,'terrain_status']='UNRESOLVED' if error else 'VERIFIED_ASSET_SAMPLED'
                if error:errors.append({'location_id':frame.loc[i,'location_id'],'error':error})
            if n%10==0:print('terrain tiles',n,'/',len(groups),flush=True)
    if climate:
        try:
            with rasterio.Env(GDAL_HTTP_TIMEOUT=30,GDAL_HTTP_MAX_RETRY=1,GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'):
                with rasterio.open(CLIMATE) as ds:
                    for i,value in enumerate(ds.sample(list(zip(frame.longitude,frame.latitude)),masked=True)):
                        code=value[0]
                        if not np.ma.is_masked(code) and 1<=int(code)<=30:
                            frame.loc[i,'climate_zone']=CLASSES[int(code)];frame.loc[i,'climate_zone_source']=CLIMATE
                        else:errors.append({'location_id':frame.loc[i,'location_id'],'error':'Missing climate pixel'})
        except Exception as exc:errors.append({'scope':'climate raster','error':str(exc)})
    Path(output_path).parent.mkdir(parents=True,exist_ok=True);frame.to_csv(output_path,index=False)
    Path(str(output_path)+'.errors.json').write_text(json.dumps(errors,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--no-climate',action='store_true');p.add_argument('--cache',default='data/terrain')
    a=p.parse_args();enrich(a.input,a.output,not a.no_climate,a.cache)

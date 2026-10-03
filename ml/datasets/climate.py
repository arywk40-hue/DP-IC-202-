"""Bounded India-window Köppen raster read, with a hashed derived crop.
Avoid hundreds of independent remote random-pixel range requests.
"""
import argparse,json,hashlib
from pathlib import Path
import pandas as pd,numpy as np
from ml.datasets.terrain import CLIMATE,CLASSES


def enrich(path):
    import rasterio
    from rasterio.windows import from_bounds
    from ml.datasets.registry import digest
    crop=Path('data/terrain/climate_india.tif');crop.parent.mkdir(parents=True,exist_ok=True)
    if not crop.exists():
        with rasterio.Env(GDAL_HTTP_TIMEOUT=60,GDAL_HTTP_MAX_RETRY=3,GDAL_HTTP_RETRY_DELAY=1,GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'):
            with rasterio.open(CLIMATE) as ds:
                window=from_bounds(67,3,100,39,ds.transform).round_offsets().round_lengths()
                data=ds.read(1,window=window,masked=True);profile=ds.profile.copy()
                profile.update(width=data.shape[1],height=data.shape[0],transform=ds.window_transform(window),compress='deflate')
                with rasterio.open(crop.with_suffix('.building.tif'),'w',**profile) as dst:dst.write(data.filled(ds.nodata or 0),1)
        crop.with_suffix('.building.tif').replace(crop)
        crop.with_suffix('.receipt.json').write_text(json.dumps({'source_uri':CLIMATE,'derived_crop_sha256':digest(crop),'bounds_wgs84':[67,3,100,39],'license':'CC-BY-4.0','primary':'https://www.gloh2o.org/koppen/','note':'hash is clipped derivative, not the full global asset'},indent=2)+'\n')
    frame=pd.read_csv(path).astype(object);errors=[]
    with rasterio.open(crop) as ds:
        for i,value in enumerate(ds.sample(list(zip(frame.longitude,frame.latitude)),masked=True)):
            code=value[0]
            if not np.ma.is_masked(code) and 1<=int(code)<=30:
                frame.loc[i,'climate_zone']=CLASSES[int(code)];frame.loc[i,'climate_zone_source']=CLIMATE
            else:errors.append({'location_id':frame.loc[i,'location_id'],'reason':'No climate pixel'})
    frame.to_csv(path,index=False);Path(str(path)+'.climate_errors.json').write_text(json.dumps(errors,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stations',default='data/registry/india_stations.csv');a=p.parse_args();enrich(a.stations)

"""Read only verified cached SRTM assets; never download or invent query height."""
import json
from pathlib import Path

from ml.datasets.registry import digest
from ml.datasets.terrain import tile


class CachedTerrain:
    def __init__(self,folder):self.folder=Path(folder);self.datasets={};self.hashes={}
    def sample(self,lat,lon,height_above_ground=2.):
        import rasterio
        name=tile(lat,lon);path=self.folder/name;receipt=path.with_suffix('.receipt.json')
        if name not in self.datasets:
            if not path.is_file() or not receipt.is_file():return None,{'status':'terrain_unavailable','source':'none'}
            proof=json.loads(receipt.read_text());sha=digest(path)
            if sha!=proof['sha256']:raise ValueError('Terrain bytes differ from receipt')
            ds=rasterio.open(path)
            if ds.crs.to_epsg()!=4326:ds.close();raise ValueError('Expected WGS84 SRTM tile')
            self.datasets[name]=ds;self.hashes[name]=sha
        ds=self.datasets[name]
        from rasterio.windows import Window
        row,col=ds.index(lon,lat)
        value=ds.read(1,window=Window(col,row,1,1),boundless=True,masked=True)[0,0]
        import numpy as np
        if np.ma.is_masked(value) or not np.isfinite(value):return None,{'status':'terrain_pixel_missing','source':name}
        return float(value)+height_above_ground,{'status':'cached_srtm_sample','source':name,'sha256':self.hashes[name],
                                                'datum':'EGM96','ground_elevation_m':float(value),'query_height_above_ground_m':height_above_ground}
    def close(self):
        for ds in self.datasets.values():ds.close()
        self.datasets.clear()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

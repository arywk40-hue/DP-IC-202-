"""Synthetic engineering inputs only; random labels measure no weather skill."""
from pathlib import Path

import numpy as np
import pandas as pd

from ml.hazard_context.online_data import VARIABLES


def create_inputs(directory, days=100, seed=42):
    """Write small ERA5-shaped NetCDF and delayed, explicitly synthetic labels."""
    import xarray as xr

    if not 40<=days<=366:
        raise ValueError("Use a bounded demo with sufficient warm-up/reference")
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=False)
    rng=np.random.default_rng(seed)
    times=pd.date_range("2024-01-01",periods=days*24,freq="h")
    shape=(len(times),2,2)
    t=283.+rng.normal(0,5,shape)
    u,v=rng.normal(0,4,shape),rng.normal(0,4,shape)
    values=dict(cape=rng.gamma(2,300,shape),cin=rng.gamma(2,30,shape),tcwv=rng.normal(30,5,shape),
        t2m=t,d2m=t-rng.gamma(2,2,shape),sp=85000+rng.normal(0,1000,shape),
        u10=u,v10=v,gust=np.hypot(u,v)+rng.gamma(1,2,shape),blh=rng.uniform(50,2000,shape))
    arrays={VARIABLES[k][0][0]:(("time","latitude","longitude"),a,{"units":sorted(VARIABLES[k][1])[0]}) for k,a in values.items()}
    ds=xr.Dataset(arrays,coords=dict(time=times,latitude=[31.7,31.8],longitude=[76.9,77.0]),
        attrs=dict(evidence="SYNTHETIC_ENGINEERING_ONLY_NOT_REAL_ERA5"))
    nc=directory/"synthetic_era5_shape.nc"
    ds.to_netcdf(nc)
    paths={}
    for target,rate in (("cloudburst",.08),("snowstorm",.06)):
        rows=[]
        for lat,lon in ((31.7,76.9),(31.8,77.0)):
            stamps=times.tz_localize("UTC")
            labels=rng.binomial(1,rate,len(stamps))
            rows.extend(dict(time=t.isoformat(),lat=lat,lon=lon,label=int(y),available_at=(t+pd.Timedelta(hours=48)).isoformat(),
                target=target) for t,y in zip(stamps,labels))
        path=directory/f"{target}_synthetic_labels.csv"
        pd.DataFrame(rows).sort_values(["time","lat","lon"]).to_csv(path,index=False)
        paths[target]=path
    return nc,paths

"""Small functional ERA5 pilot, preserving existing full-archive request definitions."""
import json
from pathlib import Path

from ml.datasets.era5_land import request


def jobs():
    regions={'himalaya_mandi':[32.,76.5,31.5,77.5],'plains_delhi':[29.,76.8,28.3,77.8],'coastal_mumbai':[19.4,72.5,18.7,73.3]}
    result=[]
    for name,area in regions.items():
        job=request(2024,8,area);job['request']['day']=['01','02','03'];job['request']['product_type']=['reanalysis'];job['region']=name
        result.append(job)
    return {'purpose':'FUNCTIONAL_INGESTION_PILOT_NOT_MODEL_EFFICACY','selection':'Fixed geographic/type pilot; dates are not asserted independent hazard events',
            'authentication':'Own CDS credentials and manually accepted terms required; no download attempted','status':'BLOCKED_BY_ACCESS',
            'variables':'Existing justified five variables only; no soil/radiation/precipitation requests','requests':result,
            'period':'2024-08-01 through 2024-08-03, all UTC hours','background_mode':'retrospective_background_context'}


def grid_provenance(ds,stations):
    """Preserve exact bracketing coordinates/weights for rectilinear pilot files."""
    import numpy as np
    from ml.hazard_context.era5 import coordinate_contract
    ds=coordinate_contract(ds);result=[]
    for station in stations.to_dict('records'):
        lat,lon=station['latitude'],station['longitude'];ys=ds.latitude.values;xs=ds.longitude.values
        if not ys[0]<=lat<=ys[-1] or not xs[0]<=lon<=xs[-1]:
            result.append({'physical_site_id':station['physical_site_id'],'status':'OUTSIDE_GRID'});continue
        yi=min(max(int(np.searchsorted(ys,lat))-1,0),len(ys)-2);xi=min(max(int(np.searchsorted(xs,lon))-1,0),len(xs)-2)
        yf=(lat-ys[yi])/(ys[yi+1]-ys[yi]);xf=(lon-xs[xi])/(xs[xi+1]-xs[xi])
        result.append({'physical_site_id':station['physical_site_id'],'query_latitude':float(lat),'query_longitude':float(lon),
                       'grid_latitudes':ys[yi:yi+2].tolist(),'grid_longitudes':xs[xi:xi+2].tolist(),
                       'weights':[[float((1-yf)*(1-xf)),float((1-yf)*xf)],[float(yf*(1-xf)),float(yf*xf)]],
                       'method':'exact_rectilinear_bilinear_four_corners','status':'MATCHED'})
    return result


if __name__=='__main__':
    p=Path('configs/era5_operational_pilot.json');p.write_text(json.dumps(jobs(),indent=2)+'\n');print(p)

"""Network geometry guards and explicitly named terrain/background features."""
import numpy as np
from scipy.spatial import ConvexHull, QhullError
from ml.spatial_ensemble.model import coordinates, snapshot_features

ERA5_FEATURES=['era5_temperature_c','era5_relative_humidity_pct','era5_surface_pressure_hpa','era5_wind_speed_mps']
EXTRA_FEATURES=['query_elevation_m','query_slope_deg','idw_node_elevation_m','elevation_difference_m',*ERA5_FEATURES]


def distances_km(lat,lon,positions):
    coordinates(lat,lon)
    positions=np.asarray(positions,dtype=float).reshape(-1,2)
    for a,b in positions:coordinates(a,b)
    a=np.radians(positions[:,0]);da=np.radians(positions[:,0]-lat);db=np.radians(positions[:,1]-lon)
    h=np.sin(da/2)**2+np.cos(np.radians(lat))*np.cos(a)*np.sin(db/2)**2
    return 6371.0088*2*np.arcsin(np.sqrt(np.clip(h,0,1)))


def guard(nodes,latitude,longitude,timestamp,max_distance_km=20):
    import pandas as pd
    if not np.isfinite(max_distance_km) or max_distance_km<=0:raise ValueError('Positive maximum distance required')
    coordinates(latitude,longitude)
    positions=[]
    for node in nodes:
        try:
            if pd.Timestamp(node['timestamp_utc'])!=pd.Timestamp(timestamp):continue
            positions.append(coordinates(node['latitude'],node['longitude']))
        except (KeyError,ValueError,TypeError):continue
    positions=np.unique(np.asarray(positions,dtype=float).reshape(-1,2),axis=0)
    if not len(positions):return {'allowed':False,'reason':'NO_CURRENT_NODES','inside_convex_hull':False,'nearest_distance_km':None}
    distance=float(distances_km(latitude,longitude,positions).min())
    # Local equirectangular plane is explicit; intended for Indian regional networks.
    origin=np.mean(positions,axis=0);scale=np.array([1,np.cos(np.radians(origin[0]))])
    points=(positions-origin)*scale;query=(np.array([latitude,longitude])-origin)*scale
    inside=False
    try:
        if len(points)>=3:
            hull=ConvexHull(points);inside=bool(np.all(hull.equations[:,:2]@query+hull.equations[:,2]<=1e-10))
    except QhullError:pass
    if distance<1e-6:inside=True
    reason='OK' if inside and distance<=max_distance_km else ('MAXIMUM_DISTANCE' if distance>max_distance_km else 'OUTSIDE_CONVEX_HULL')
    return dict(allowed=reason=='OK',reason=reason,inside_convex_hull=inside,nearest_distance_km=distance,max_distance_km=max_distance_km)


def named_features(nodes,latitude,longitude,timestamp,query_elevation_m=None,query_slope_deg=None,background=None):
    base,idw,counts=snapshot_features(nodes,latitude,longitude,timestamp)
    import pandas as pd
    pairs=[]
    for node in nodes:
        try:
            elev=float(node['elevation_m'])
            if not np.isfinite(elev) or pd.Timestamp(node['timestamp_utc'])!=pd.Timestamp(timestamp):continue
            distance=distances_km(latitude,longitude,[[node['latitude'],node['longitude']]])[0]
            pairs.append((distance,elev))
        except (KeyError,ValueError,TypeError):continue
    z=np.nan
    if pairs:
        d,elev=np.array(pairs).T;exact=d<1e-6;w=exact.astype(float) if exact.any() else (d.min()/d)**2;z=float(w@elev/w.sum())
    q=np.nan if query_elevation_m is None else float(query_elevation_m)
    slope=np.nan if query_slope_deg is None else float(query_slope_deg)
    background=background or {}
    extra=[q,slope,z,q-z,*[float(background.get(k,np.nan)) for k in ERA5_FEATURES]]
    return np.r_[base,extra],idw,counts


def distance_distribution(stations):
    pairs=[]
    for i,row in stations.iterrows():
        rest=stations.iloc[i+1:]
        pairs.extend(distances_km(row.latitude,row.longitude,rest[['latitude','longitude']].to_numpy()).tolist())
    edges=[0,1,5,20,50,100,250,500,1000,float('inf')]
    hist=np.histogram(pairs,bins=edges)[0]
    return {'scope':'unique static station pairs, not co-observed training pairs','total_pairs':len(pairs),
        'bins_km':['0–1','1–5','5–20','20–50','50–100','100–250','250–500','500–1000','1000+'],
        'counts':hist.tolist(),'mesh_1_to_20_km_pairs':int(((np.asarray(pairs)>=1)&(np.asarray(pairs)<=20)).sum())}

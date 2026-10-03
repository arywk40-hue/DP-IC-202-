"""Spherical short A–B segment geometry (WGS84 coordinates, mean Earth radius).
Limits apply to distance from the CLAMPED segment and beyond each endpoint.
Not an ellipsoidal survey; use surveyed sensor coordinates for close deployment.
"""
import numpy as np
from ml.spatial_ensemble.model import coordinates

DEFAULT_LIMITS={'max_segment_distance_km':1.,'max_beyond_a_km':.25,'max_beyond_b_km':.25,'max_node_separation_km':20.}
R=6371.0088

def limits(values=None):
    out={**DEFAULT_LIMITS,**(values or {})}
    if set(out)!=set(DEFAULT_LIMITS):raise ValueError('Unknown corridor limit')
    for key,value in out.items():
        if not np.isfinite(value) or value<0 or (key=='max_node_separation_km' and value==0):raise ValueError('Finite nonnegative corridor limits required')
    return out

def xyz(p):
    p=np.radians(np.asarray(p,float));lat,lon=p[...,0],p[...,1]
    return np.stack([np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)],axis=-1)

def metrics(a,b,q,configuration=None):
    config=limits(configuration);a,b,q=np.broadcast_arrays(np.asarray(a,float),np.asarray(b,float),np.asarray(q,float))
    if a.shape[-1]!=2 or not np.isfinite(a).all() or not np.isfinite(b).all() or not np.isfinite(q).all():raise ValueError('Finite lat/lon pairs required')
    for p in [a,b,q]:
        if np.any(np.abs(p[...,0])>90) or np.any(np.abs(p[...,1])>180):raise ValueError('Invalid coordinates')
    u,v,w=xyz(a),xyz(b),xyz(q);normal=np.cross(u,v);norm=np.linalg.norm(normal,axis=-1);angle=np.arctan2(norm,np.sum(u*v,axis=-1));length=R*angle
    good=(length>=.001)&(angle<np.pi-1e-6)
    normal=np.divide(normal,norm[...,None],out=np.zeros_like(normal),where=norm[...,None]>1e-12);tangent=np.cross(normal,u)
    along=R*np.arctan2(np.sum(w*tangent,axis=-1),np.sum(w*u,axis=-1));cross=R*np.abs(np.arcsin(np.clip(np.sum(w*normal,axis=-1),-1,1)))
    to_a=R*np.arctan2(np.linalg.norm(np.cross(w,u),axis=-1),np.sum(w*u,axis=-1));to_b=R*np.arctan2(np.linalg.norm(np.cross(w,v),axis=-1),np.sum(w*v,axis=-1))
    beyond_a=np.maximum(-along,0);beyond_b=np.maximum(along-length,0);segment=np.where(along<0,to_a,np.where(along>length,to_b,cross))
    inside=good&(segment<=config['max_segment_distance_km']+1e-9)&(beyond_a<=config['max_beyond_a_km']+1e-9)&(beyond_b<=config['max_beyond_b_km']+1e-9)&(length<=config['max_node_separation_km']+1e-9)
    return dict(allowed=inside,segment_distance_km=segment,cross_track_km=cross,along_track_km=along,beyond_a_km=beyond_a,beyond_b_km=beyond_b,node_separation_km=length,nearest_distance_km=np.minimum(to_a,to_b),nondegenerate=good)

def corridor(a,b,q,configuration=None):
    config=limits(configuration);raw=metrics(a,b,q,config);out={k:bool(v) if k in ['allowed','nondegenerate'] else float(v) for k,v in raw.items()}
    reasons=[]
    if not out['nondegenerate']:reasons.append('DEGENERATE_SEGMENT')
    for metric,limit,reason in [('segment_distance_km','max_segment_distance_km','OFF_SEGMENT'),('beyond_a_km','max_beyond_a_km','BEYOND_A'),('beyond_b_km','max_beyond_b_km','BEYOND_B'),('node_separation_km','max_node_separation_km','NODE_SEPARATION')]:
        if out[metric]>config[limit]+1e-9:reasons.append(reason)
    return {**out,'reason':'OK' if out['allowed'] else ','.join(reasons),'limits':config,'method':'short_great_circle_segment'}

def guard_two(nodes,latitude,longitude,timestamp,configuration=None):
    import pandas as pd
    stamp=pd.Timestamp(timestamp);positions=[]
    for node in nodes:
        try:
            t=pd.Timestamp(node['timestamp_utc'])
            if t.tzinfo is None or pd.isna(t) or t!=stamp:continue
            positions.append(coordinates(node['latitude'],node['longitude']))
        except (KeyError,TypeError,ValueError):continue
    if len(positions)!=2:return {'allowed':False,'reason':'NEED_TWO_CURRENT_CONTRIBUTORS','nearest_distance_km':None}
    return corridor(positions[0],positions[1],coordinates(latitude,longitude),configuration)

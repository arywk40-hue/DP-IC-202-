"""Run from repository root: python -m reports.practicum.demo
A synthetic safety demonstration; not a performance evaluation or live mesh.
"""
import json
from ml.spatial_ensemble.physics_serving import predict_snapshot

def main():
    timestamp='2024-12-01T12:00:00Z'
    nodes=[dict(latitude=lat,longitude=lon,elevation_m=z,timestamp_utc=timestamp,temperature_c=15-.0065*z,relative_humidity_pct=60,pressure_hpa=1013.25*((288.15-.0065*z)/288.15)**(9.80665/(287.05*.0065)),wind_speed_mps=2) for lat,lon,z in [(31.68,76.89,600),(31.75,76.89,1000),(31.71,76.98,1200)]]
    args=dict(latitude=31.71,longitude=76.93,timestamp=timestamp,query_elevation_m=763)
    cases={'inside':predict_snapshot(nodes,**args),'far':predict_snapshot(nodes,32.5,77.5,timestamp,763),'one_offline':predict_snapshot(nodes[:-1],**args),'missing_query_elevation':predict_snapshot(nodes,**{**args,'query_elevation_m':None}),'suspect_pressure':predict_snapshot([{**n,'pressure_ok':False} for n in nodes],**args)}
    print(json.dumps({'warning':'Synthetic physics-only demo; no trained model or checked bands loaded','cases':cases},indent=2,allow_nan=False))
if __name__=='__main__':main()

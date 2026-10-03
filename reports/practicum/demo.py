"""A/B JSON demo: python -m reports.practicum.demo --input readings.json
Without --input, run the explicitly synthetic example. No hidden C readings.
"""
import argparse,json
from pathlib import Path
from ml.spatial_ensemble.physics_serving import predict_two_nodes
from ml.spatial_ensemble.corridor import DEFAULT_LIMITS
from ml.spatial_ensemble.residual_artifact import load

def example():
    timestamp='2024-12-01T12:00:00Z'
    def node(id,lat,lon,z):
        return dict(node_id=id,latitude=lat,longitude=lon,elevation_m=z,timestamp_utc=timestamp,temperature_c=15-.0065*z,relative_humidity_pct=60,pressure_hpa=1013.25*((288.15-.0065*z)/288.15)**(9.80665/(287.05*.0065)),wind_speed_mps=2)
    return {'nodes':{'A':node('A',31.7,76.90,600),'B':node('B',31.7,76.98,1000)},'query':{'latitude':31.7,'longitude':76.94,'elevation_m':763,'timestamp_utc':timestamp},'synthetic':True}

def run(payload,model_path=None,configuration=None,outside_policy='refuse'):
    if not isinstance(payload,dict) or set(payload.get('nodes',{}))!={'A','B'}:raise ValueError('Exactly nodes A and B required; hidden C readings forbidden')
    q=payload['query']
    if set(q)-{'latitude','longitude','elevation_m','timestamp_utc','slope_deg'}:raise ValueError('Query metadata only: hidden readings must not enter prediction')
    model,bands=load(model_path) if model_path else (None,None)
    if model is not None and model.neighbor_count!=2:raise ValueError('Demo needs a freshly trained 2-neighbor model')
    result=predict_two_nodes(payload['nodes']['A'],payload['nodes']['B'],q['latitude'],q['longitude'],q['timestamp_utc'],q['elevation_m'],query_slope_deg=q.get('slope_deg'),model=model,bands=bands,corridor_limits=configuration,outside_policy=outside_policy)
    result['warning']='Synthetic input; no field performance evidence' if payload.get('synthetic') else 'Input provenance/authentication supplied by caller; missing checked bands print null'
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--input');p.add_argument('--model');p.add_argument('--outside-policy',choices=['refuse','flag'],default='refuse')
    for key,value in DEFAULT_LIMITS.items():p.add_argument('--'+key.replace('_','-'),type=float,default=value)
    a=p.parse_args();payload=json.loads(Path(a.input).read_text()) if a.input else example()
    result=run(payload,a.model,{key:getattr(a,key) for key in DEFAULT_LIMITS},a.outside_policy)
    print(json.dumps(result,indent=2,allow_nan=False))
if __name__=='__main__':main()

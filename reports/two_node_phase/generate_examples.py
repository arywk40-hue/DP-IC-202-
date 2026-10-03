"""Deterministic synthetic fixtures: calibration/scoring smoke tests only."""
from pathlib import Path
import json,pandas as pd
from reports.practicum.demo import example

def main():
    root=Path('reports/two_node_phase/examples');root.mkdir(exist_ok=True)
    (root/'readings.json').write_text(json.dumps(example(),indent=2)+'\n')
    for phase,n in [('colocated',60),('field',12)]:
        records=[]
        for i in range(n):
            date='2024-01-01T00:00Z' if phase=='colocated' else '2024-01-02T00:00Z';t=(pd.Timestamp(date)+pd.Timedelta(minutes=i)).strftime('%Y-%m-%dT%H:%M:%SZ')
            for id in 'ABC':
                bias={'A':1,'B':-2,'C':0}[id];position={'A':76.90,'B':76.98,'C':76.94}
                records.append(dict(timestamp_utc=t,node_id=id,latitude=31.7,longitude=76.9 if phase=='colocated' else position[id],elevation_m=600,pressure_reference='station',temperature_c=15+bias,relative_humidity_pct=60+bias,pressure_hpa=940+bias,wind_speed_mps=3+bias))
        pd.DataFrame(records).to_csv(root/(phase+'.csv'),index=False)
if __name__=='__main__':main()

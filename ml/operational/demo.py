"""Generate offline read-only GPS map bundles; no live authentication claims."""
import argparse
import json
from pathlib import Path

from ml.operational.map_data import build,fixture
from ml.operational.map_view import write_html
from ml.operational.terrain import CachedTerrain
from ml.operational.contracts import schemas


def run(output,input_path=None,count=2,terrain_cache=None,model=None):
    folder=Path(output)
    if folder.exists() and any(folder.iterdir()):raise ValueError('Use a fresh output directory; preserve prior demo snapshots')
    folder.mkdir(parents=True,exist_ok=True)
    terrain=CachedTerrain(terrain_cache) if terrain_cache else None
    try:
        payload=json.loads(Path(input_path).read_text()) if input_path else fixture(count,terrain)
        data=build(payload,terrain,model)
        public_payload={**payload,'observations':[r for r in payload['observations'] if r.get('node_id') not in data['hidden_test_nodes_excluded']]}
        (folder/'observations.json').write_text(json.dumps(public_payload,indent=2,allow_nan=False)+'\n')
        (folder/'map.json').write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
        (folder/'contracts.json').write_text(json.dumps(schemas(),indent=2)+'\n')
        write_html(data,folder/'index.html')
        return dict(output=str(folder),mode=data['mode'],model=data['model_status'],nodes=len(data['nodes']),cells=len(data['cells']),
                    available_by_channel={c:sum(q['channels'][c]['estimate'] is not None for q in data['cells']) for c in data['cells'][0]['channels']},
                    checked_intervals=sum(r['uncertainty_available'] for q in data['cells'] for r in q['channels'].values()),
                    disaster_outputs='DISABLED',hardware_validated=False)
    finally:
        if terrain:terrain.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--input');p.add_argument('--nodes',type=int,choices=[2,3],default=2)
    p.add_argument('--terrain-cache');p.add_argument('--model');a=p.parse_args()
    print(json.dumps(run(a.output,a.input,a.nodes,a.terrain_cache,a.model),indent=2))

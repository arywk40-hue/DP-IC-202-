import json
from pathlib import Path
import shutil

from fastapi.testclient import TestClient

from server.dashboard import create_app


def test_storm_run_api_uses_only_configured_outputs_and_rejects_tampering(tmp_path):
    source = Path(__file__).resolve().parents[1] / 'fixtures/storm_risk_ui'
    run = tmp_path / 'run'
    shutil.copytree(source, run)
    with TestClient(create_app(tmp_path / 'nodes.sqlite', storm_risk_run=run)) as client:
        report = client.get('/api/storm-risk/report').json()
        assert report['configured'] and not report['calibrated']
        scores = client.get('/api/storm-risk/scores').json()
        assert len(scores['rows']) == 4 and scores['rows'][0]['anomaly_flag']
        assert sum(r['neighbour_confirmed'] for r in scores['rows']) == 3
        heatmap = client.get('/api/storm-risk/heatmap?feature=t2m').json()
        assert heatmap['values'] == [[18, 19], [20, 21]]
        assert client.get('/api/storm-risk/heatmap?feature=../../secret').status_code == 422
        assert client.get('/api/storm-risk/scores?limit=10000').status_code == 422
        path = next((run / 'heatmaps').glob('*.npz'))
        path.write_bytes(path.read_bytes() + b'tamper')
        assert client.get('/api/storm-risk/heatmap').status_code == 422
        raw = json.loads((run / 'report.json').read_text())
        raw['calibrated'] = True
        (run / 'report.json').write_text(json.dumps(raw))
        assert client.get('/api/storm-risk/report').status_code == 422


def test_storm_api_explicitly_unconfigured(tmp_path):
    with TestClient(create_app(tmp_path / 'nodes.sqlite')) as client:
        assert client.get('/api/storm-risk/report').json()['status'] == 'NOT_CONFIGURED'
        assert client.get('/api/storm-risk/scores').json()['rows'] == []
        assert client.get('/api/storm-risk/heatmap').json()['cells'] == []

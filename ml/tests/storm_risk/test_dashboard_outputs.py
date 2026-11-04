from pathlib import Path

from fastapi.testclient import TestClient

from server.dashboard import create_app


def test_research_storm_run_is_not_connected_to_the_mandi_dashboard(tmp_path):
    source = Path(__file__).resolve().parents[1] / 'fixtures/storm_risk_ui'
    assert (source / 'report.json').is_file()
    with TestClient(create_app(tmp_path / 'nodes.sqlite')) as client:
        assert client.get('/api/storm-risk/report').status_code == 404
        assert client.get('/api/storm-risk/scores').status_code == 404
        assert client.get('/api/storm-risk/heatmap').status_code == 404


def test_storm_api_explicitly_unconfigured(tmp_path):
    with TestClient(create_app(tmp_path / 'nodes.sqlite')) as client:
        assert client.get('/api/storm-risk/report').status_code == 404
        assert client.get('/api/storm-risk/scores').status_code == 404
        assert client.get('/api/storm-risk/heatmap').status_code == 404

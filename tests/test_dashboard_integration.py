"""Exercise saved-model results, evidence states and the teammate HTTP contract."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile

from fastapi.testclient import TestClient
import pytest

from server.dashboard import Store, assess, create_app, demo_observations
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS

NOW = "2026-10-15T06:00:00Z"


@pytest.fixture(scope="module")
def assessed():
    return assess(demo_observations(NOW), now=NOW)


def test_saved_india_model_and_rule_evidence_have_distinct_meaning(assessed):
    assert len(assessed) == 4
    for node in assessed:
        assert set(node["sensors"]) == set(RAW_SENSOR_COLUMNS)
        assert set(node["forecast6h"]) == set(RAW_SENSOR_COLUMNS)
        assert node['forecastModel']['configuredId'] == 'india_mandi_tabular_v2'
        assert not node["forecastModel"]["fieldValidated"]
        assert node["probability"] is None
        assert node["syntheticDemo"]
        assert node["battery"] is None
        for risk in node["risks"].values():
            assert risk["probability"] is None
            assert risk["lead_time_h"] is None
            assert not risk["warning_candidate"]
            assert risk["dispatch_state"] == "DISABLED"
    assert assessed[0]["risks"]["rain"]["score"] == 1
    assert assessed[1]["risks"]["snowstorm"]["score"] == 1
    assert assessed[2]["risks"]["cloudburst_risk"]["level"] == "local_warning_candidate"
    assert assessed[3]["risks"]["cloudburst_risk"]["abstain"]
    assert all(n['forecastModel']['id'] == 'india_mandi_tabular_v2' and n['forecastStatus'] == 'HYBRID_READY' for n in assessed[:3])
    assert assessed[3]['forecastStatus'] == 'WARMING_UP_PERSISTENCE'
    assert assessed[3]['forecast6h'] == assessed[3]['sensors']
    json.dumps(assessed, allow_nan=False)


def test_five_endpoint_handoff_and_restart_staleness(assessed):
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp)/"nodes.sqlite"
        store = Store(db)
        store.replace(assessed)
        epoch = assessed[0]["timestamp"]/1000
        with TestClient(create_app(db, clock=lambda: epoch)) as client:
            assert client.get("/api/status").json()["appVersion"] == "0.5.0"
            assert client.get('/api/status').json()['forecastModel'] == 'india_mandi_tabular_v2'
            assert len(client.get("/api/nodes").json()) == 4
            provenance = client.get('/api/provenance').json()
            assert provenance['status'] == 'LOCAL_ONLY'
            assert provenance['on_chain_verified'] is False
            assert provenance['count'] >= 1
            telemetry = client.get("/api/nodes/demo-03/telemetry").json()
            assert telemetry["assessmentUsableNow"]
            assert telemetry["risks"]["cloudburst_risk"]["probability"] is None
            assert client.get("/api/kriging/heatmap").json()["features"]
            assert client.post("/api/rpc/demo-01", json={"command": 1}).status_code == 501
            assert client.get("/api/nodes/missing/telemetry").status_code == 404
        with TestClient(create_app(db, clock=lambda: epoch+86400)) as client:
            old = client.get("/api/nodes/demo-03/telemetry").json()
            assert old["stale"] and not old["assessmentUsableNow"]
            assert client.get("/api/status").json()["staleNodes"] == 4


def test_bad_import_never_replaces_store_and_missing_channel_abstains(assessed):
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp)/"nodes.sqlite")
        store.replace(assessed)
        bad = demo_observations(NOW)
        bad[0]["measurements"]["seventh_sensor"] = 1
        with pytest.raises(ValueError):
            store.replace(assess(bad, now=NOW))
        assert store.all() == assessed
    raw = demo_observations(NOW)
    for record in raw:
        record["measurements"]["pm10_ug_m3"] = None
    result = assess(raw, now=NOW)
    assert all(n["forecast6h"]["temperature_c"] is None for n in result)
    assert all(n["risks"]["rain"]["abstain"] for n in result)


def test_future_duplicate_relocation_and_forecast_checksum_fail_closed(tmp_path):
    raw = demo_observations(NOW)
    with pytest.raises(ValueError, match="Future"):
        assess(raw, now="2026-10-14T00:00:00Z")
    with pytest.raises(ValueError, match="Duplicate"):
        assess([*raw, copy.deepcopy(raw[0])], now=NOW)
    moved = copy.deepcopy(raw)
    moved[0]["latitude"] += .01
    with pytest.raises(ValueError, match="fixed site"):
        assess(moved, now=NOW)
    root = Path(__file__).resolve().parents[1]
    import shutil
    shutil.copytree(root/"ml/models/india_mandi_hybrid_6h_v1", tmp_path/"model")
    with (tmp_path/"model/ensemble_weights.json").open("ab") as f:
        f.write(b"tamper")
    with pytest.raises(ValueError, match="checksum"):
        assess(raw, now=NOW, model_dir=tmp_path/"model")


def test_original_teammate_handoff_preserved():
    root = Path(__file__).resolve().parents[1]/"docs/reference/dp_mesh_dashboard_handoff"
    for entry in json.loads((root/"original_manifest.json").read_text())["files"]:
        assert hashlib.sha256((root/entry["path"]).read_bytes()).hexdigest() == entry["sha256"]

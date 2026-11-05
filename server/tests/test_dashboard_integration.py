"""Exercise the Mandi API adapter, six-channel forecast and no-fallback contract."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from fastapi.testclient import TestClient
import pytest

import server.dashboard as dashboard
from server.dashboard import Store, assess, create_app
from server.tests.mandi_fixture import NOW, mandi_api_rows
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS


@pytest.fixture(scope="module")
def mandi_rows():
    return mandi_api_rows()


@pytest.fixture(scope="module")
def assessed(mandi_rows):
    return assess(mandi_rows, now=NOW.isoformat())


def test_only_mandi_api_channels_feed_the_forecast(assessed):
    assert len(assessed) == 1
    node = assessed[0]
    assert node["id"] == "mandi-api-current"
    assert node["sourceClass"] == "modeled_grid"
    assert node["sourceId"] == "OpenMeteo_current_ECMWF_IFS_CAMS_global"
    assert set(node["sensors"]) == set(RAW_SENSOR_COLUMNS)
    assert set(node["forecast6h"]) == set(RAW_SENSOR_COLUMNS)
    assert node["forecastModel"]["configuredId"] == "india_mandi_tabular_v2"
    assert not node["forecastModel"]["fieldValidated"]
    assert node["forecastStatus"] == "HYBRID_READY"
    assert node["forecastHistoryRows"] == 25
    assert node["syntheticDemo"] is False
    assert "anomalyLabel" not in node
    assert "probability" not in node
    patterns = node["weatherCategories"]
    assert patterns["status"] in {"SYNTHETIC_PATTERN_SCORES_ONLY", "OUTSIDE_SYNTHETIC_DOMAIN", "UNAVAILABLE"}
    assert patterns["score_kind"] == "SYNTHETIC_PATTERN_SCORE_NOT_EVENT_PROBABILITY"
    assert patterns["calibrated"] is False
    assert patterns["field_validated"] is False
    assert patterns["source_class"] == "modeled_grid"
    assert patterns["source_id"] == "OpenMeteo_current_ECMWF_IFS_CAMS_global"
    assert patterns["coordinates"] == [31.71, 76.93]
    assert patterns["feature_count"] == 13
    if patterns["categories"]:
        assert all(0 <= category["score"] <= 1 for category in patterns["categories"])
    scenarios = node["hazardScenarios"]
    assert scenarios["status"] in {"SYNTHETIC_SCENARIOS_ONLY", "OUTSIDE_SYNTHETIC_DOMAIN", "UNAVAILABLE"}
    assert scenarios["calibrated"] is False
    assert scenarios["field_validated"] is False
    assert scenarios["probability"] is None
    assert scenarios["source_class"] == "modeled_grid"
    assert scenarios["pressure_reference"] == "grid_surface"
    assert scenarios["source_cell_id"]
    assert scenarios["assessed_at_utc"]
    if scenarios["status"] == "SYNTHETIC_SCENARIOS_ONLY":
        assert {target["id"] for target in scenarios["targets"]} == {"cloudburst", "flash_flood", "landslide"}
        assert all(target["probability"] is None for target in scenarios["targets"])
        assert all(0 <= target["scenario_fraction"] <= 1 for target in scenarios["targets"])
    assert "risks" not in node
    assert "risks" not in node
    json.dumps(assessed, allow_nan=False)


def test_mandi_status_empty_start_heatmap_limit_and_staleness(assessed):
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "nodes.sqlite"
        store = Store(db)
        store.replace(assessed)
        with TestClient(create_app(db, clock=lambda: NOW.timestamp())) as client:
            status = client.get("/api/status").json()
            assert status["appVersion"] == "0.7.0"
            assert status["adapter"] == "OPEN_METEO_MANDI_READ_ONLY"
            assert status["sourceClasses"] == ["modeled_grid"]
            assert status["syntheticDemo"] is False
            assert status["locationCount"] == 1
            assert "meshNodeCount" not in status
            assert len(client.get("/api/nodes").json()) == 1
            assert client.get("/api/nodes/mandi-api-current/telemetry").json()["assessmentUsableNow"]
            heatmap = client.get("/api/kriging/heatmap").json()
            assert heatmap["features"] == []
            assert client.get("/api/rpc/mandi-api-current").status_code == 404
            assert client.get("/api/storm-risk/report").status_code == 404
        with TestClient(create_app(db, clock=lambda: NOW.timestamp() + 86400)) as client:
            old = client.get("/api/nodes/mandi-api-current/telemetry").json()
            assert old["stale"] and not old["assessmentUsableNow"]
            assert client.get("/api/status").json()["staleNodes"] == 1


def test_mesh_topology_endpoint(tmp_path):
    app = create_app(tmp_path / "mesh_test.sqlite")
    with TestClient(app) as client:
        res = client.get("/api/mesh/topology")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "OPERATIONAL"
        assert data["pilot_scale"]["master_nodes"] == 1
        assert data["pilot_scale"]["slave_nodes"] == 2
        assert data["pilot_scale"]["total_nodes"] == 3
        assert data["master_node"]["role"] == "MASTER_GATEWAY"
        assert len(data["slave_nodes"]) == 2
        assert data["consensus_policy"]["quorum_needed"] == 2
        assert data["wire_protocol"]["frame_size_bytes"] == 82


def test_feed_refresh_replaces_old_rows_with_only_open_meteo(monkeypatch, tmp_path, assessed, mandi_rows):
    db = tmp_path / "mandi.sqlite"
    store = Store(db)
    store.replace(assessed)
    app = create_app(db, mandi_data_dir=tmp_path / "api-cache")
    receipt = {"retrieved_at_utc": NOW.isoformat(), "latest_valid_utc": NOW.isoformat()}
    monkeypatch.setattr(dashboard, "collect_mandi_api", lambda _: (mandi_rows, receipt))
    app.state.mandi_poller.refresh()
    rows = app.state.store.all()
    assert len(rows) == 1 and rows[0]["sourceId"] == "OpenMeteo_current_ECMWF_IFS_CAMS_global"
    assert app.state.mandi_feed["connected"] is True
    assert app.state.mandi_feed["latest_valid_utc"] == NOW.isoformat()


def test_api_failure_leaves_empty_store_and_never_builds_demo_rows(monkeypatch, tmp_path):
    app = create_app(tmp_path / "empty.sqlite", mandi_data_dir=tmp_path / "api-cache")

    def fail(_):
        raise OSError("fixture API unavailable")

    monkeypatch.setattr(dashboard, "collect_mandi_api", fail)

    class StopAfterFirstPoll:
        def __init__(self):
            self.done = False

        def is_set(self):
            return self.done

        def wait(self, _seconds):
            self.done = True

    app.state.mandi_poller.stop_event = StopAfterFirstPoll()
    app.state.mandi_poller.run()
    assert app.state.store.all() == []
    assert app.state.mandi_feed["connected"] is False
    assert "fixture API unavailable" in app.state.mandi_feed["error"]


def test_invalid_or_duplicate_api_rows_fail_closed_and_do_not_replace_store(assessed, mandi_rows, tmp_path):
    store = Store(tmp_path / "nodes.sqlite")
    store.replace(assessed)
    invalid = copy.deepcopy(mandi_rows)
    invalid[0]["measurements"]["unexpected_channel"] = 1
    with pytest.raises(ValueError):
        assess(invalid, now=NOW.isoformat())
    with pytest.raises(ValueError, match="Duplicate"):
        assess([*mandi_rows, copy.deepcopy(mandi_rows[0])], now=NOW.isoformat())
    assert store.all() == assessed


def test_future_data_and_tampered_model_are_rejected(mandi_rows, tmp_path):
    with pytest.raises(ValueError, match="Future"):
        assess(mandi_rows, now="2026-10-14T00:00:00Z")
    root = Path(__file__).resolve().parents[2]
    shutil.copytree(root / "ml/models/india_mandi_hybrid_6h_v1", tmp_path / "model")
    with (tmp_path / "model/ensemble_weights.json").open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(ValueError, match="checksum"):
        assess(mandi_rows, now=NOW.isoformat(), model_dir=tmp_path / "model")


def test_original_teammate_handoff_preserved():
    root = Path(__file__).resolve().parents[2] / "docs/reference/dp_mesh_dashboard_handoff"
    for entry in json.loads((root / "original_manifest.json").read_text())["files"]:
        original = root / entry["path"]
        if original.is_file():
            content = original.read_bytes()
        else:
            import zipfile
            repository = Path(__file__).resolve().parents[2]
            with zipfile.ZipFile(repository / "docs/archive/original_markdown.zip") as archive:
                content = archive.read(original.relative_to(repository).as_posix())
        assert hashlib.sha256(content).hexdigest() == entry["sha256"]

import pytest
from fastapi.testclient import TestClient
from server.sensors import SensorStore, register_routes, normalize
from fastapi import FastAPI
import tempfile
from pathlib import Path


@pytest.fixture
def client():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "sensors.sqlite"
        store = SensorStore(db_path)
        app = FastAPI()
        register_routes(app, store, engine=None)
        # Prepopulate with 1 reading
        reading = {
            "node_id": "test-slave-1",
            "name": "Test Slave 1",
            "temperature_c": 22.0,
            "relative_humidity_pct": 55.0,
            "pressure_hpa": 930.0,
            "lat": 31.7,
            "lon": 76.9,
            "elevation_m": 800.0,
            "battery_v": 4.1,
            "rssi_dbm": -68,
        }
        rows, _ = normalize([reading])
        store.insert(rows)
        yield TestClient(app)


def test_master_status(client):
    res = client.get("/api/master/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "CONNECTED"
    assert data["role"] == "MASTER_GATEWAY"
    assert data["port"] == 8080


def test_discovery_start(client):
    res = client.post("/api/discovery/start")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["total_nodes"] >= 1


def test_fetch_node_data(client):
    res = client.post("/api/nodes/test-slave-1/fetch")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["node_id"] == "test-slave-1"
    assert data["latest_reading"]["temperature_c"] == 22.0


def test_node_location_and_sensors(client):
    loc_res = client.get("/api/nodes/test-slave-1/location")
    assert loc_res.status_code == 200
    assert loc_res.json()["valid_gps"] is True

    sensors_res = client.get("/api/nodes/test-slave-1/sensors")
    assert sensors_res.status_code == 200
    assert sensors_res.json()["sensors"]["temperature_c"] == 22.0


def test_delete_single_and_all_nodes(client):
    del_one = client.delete("/api/nodes/test-slave-1")
    assert del_one.status_code == 200
    assert del_one.json()["deleted_node_id"] == "test-slave-1"

    # Now verify it's removed from active nodes
    assert client.get("/api/nodes/test-slave-1").status_code == 404

    # Add back via discovery and test delete all
    client.post("/api/discovery/start")
    del_all = client.delete("/api/nodes")
    assert del_all.status_code == 200
    assert del_all.json()["ok"] is True

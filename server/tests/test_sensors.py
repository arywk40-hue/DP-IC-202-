"""Physical sensor ingest -> storage -> combined view, through the real FastAPI app."""
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from server.dashboard import create_app
from server.sensors import CHANNELS, iso


def firmware_payload(node, values, *, lat, lon, elev, stamp=None):
    """Exactly what esp32/operational_node/include/weather_payload.h prints."""
    stamp = stamp or iso(datetime.now(timezone.utc))
    return {"schema_version": "indra_weather_records_v1", "observations": [
        {"node_id": node, "timestamp_utc": stamp, "latitude": lat, "longitude": lon,
         "elevation_m": elev, "elevation_datum": "EGM96", "channel": c, "value": v,
         "unit": "x", "quality_flag": "valid" if v is not None else "missing",
         "source": "INDRA_NODE_LIVE_NOT_FIELD_VALIDATED", "sensor_model": "BME280",
         "pressure_reference": "station", "sample_interval_seconds": 1}
        for c, v in zip(CHANNELS, values)]}


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path / "grid.sqlite", mandi_data_dir=tmp_path / "cache",
                     sensor_db_path=tmp_path / "sensors.sqlite", ingest_token="")
    return TestClient(app)


def test_two_nodes_combine_into_network_view(client):
    r1 = client.post("/api/ingest", json=firmware_payload(
        "ridge-01", [14.8, 86, 873.2, 16, 24, 6.8], lat=31.725, lon=76.942, elev=1280))
    r2 = client.post("/api/ingest", json={
        "node_id": "basin-02", "temperature_c": 18.8, "relative_humidity_pct": 82,
        "pressure_hpa": 935.8, "pm25_ug_m3": 34, "pm10_ug_m3": 51, "wind_speed_mps": 1.8,
        "lat": 31.698, "lon": 76.918, "elevation_m": 710, "battery_v": 4.05})
    assert r1.status_code == r2.status_code == 200, (r1.text, r2.text)

    view = client.get("/api/sensors/combined").json()
    assert view["source"] == "PHYSICAL_SENSORS"
    assert view["node_count"] == 2 and view["online"] == 2
    temp = view["network"]["channels"]["temperature_c"]
    assert temp["mean"] == pytest.approx(16.8) and temp["spread"] == pytest.approx(4.0)
    assert view["network"]["spatial"]["lapse_rate_c_per_km"] == pytest.approx(-7.018, abs=1e-3)
    basin = next(n for n in view["nodes"] if n["node_id"] == "basin-02")
    assert basin["battery_v"] == 4.05 and basin["reading"]["timestamp_source"] == "server_receive"
    assert basin["forecast_6h"]["status"] == "WARMING_UP_PERSISTENCE"

    status = client.get("/api/status").json()
    assert status["physicalSensors"]["ONLINE"] == 2
    topo = client.get("/api/mesh/topology").json()
    assert topo["data_source"] == "STATIC_REFERENCE_LAYOUT" and topo["live"]["online"] == 2


def test_history_hourly_and_real_forecast(client):
    now = datetime.now(timezone.utc)
    batch = [{"node_id": "hist-01", "timestamp_utc": iso(now - timedelta(minutes=m)),
              "temperature_c": 12 + (m % 60) / 30, "relative_humidity_pct": 70,
              "pressure_hpa": 887, "pm25_ug_m3": 15, "pm10_ug_m3": 30, "wind_speed_mps": 1.5}
             for m in range(0, 26 * 60, 15)]
    assert client.post("/api/ingest", json=batch).json()["accepted"] == len(batch)
    assert len(client.get("/api/sensors/hist-01/history?hours=2").json()["readings"]) >= 8
    assert len(client.get("/api/sensors/hist-01/hourly?hours=30").json()["hours"]) >= 25
    forecast = client.get("/api/sensors/hist-01/forecast").json()
    assert forecast["status"] == "HYBRID_READY", forecast
    assert forecast["model_id"] == "india_mandi_tabular_v2"
    assert all(forecast["values"][c] is not None for c in CHANNELS)


def test_rejects_bad_payloads(client):
    assert client.post("/api/ingest", json={"node_id": "UNCONFIGURED", "temperature_c": 1}).status_code == 400
    future = iso(datetime.now(timezone.utc) + timedelta(hours=2))
    assert client.post("/api/ingest", json={"node_id": "n1", "temperature_c": 1, "timestamp_utc": future}).status_code == 400
    r = client.post("/api/ingest", json={"node_id": "n1", "temperature_c": 500, "relative_humidity_pct": 40})
    assert r.status_code == 200 and r.json()["rejected_values"] == 1
    assert client.get("/api/sensors/n1/latest").json()["temperature_c"] is None
    assert client.get("/api/sensors/missing/history").status_code == 404


def test_ingest_token_and_signed_packets(tmp_path, monkeypatch):
    key = bytes(range(32))
    monkeypatch.setenv("INDRA_INGEST_HMAC_KEY", key.hex())
    app = create_app(tmp_path / "grid.sqlite", mandi_data_dir=tmp_path / "cache",
                     sensor_db_path=tmp_path / "sensors.sqlite", ingest_token="s3cret")
    client = TestClient(app)
    body = {"node_id": "sig-01", "temperature_c": 9.5}
    assert client.post("/api/ingest", json=body).status_code == 401
    assert client.post("/api/ingest", json=body, headers={"X-Indra-Token": "s3cret"}).status_code == 200

    payload = json.dumps({"node_id": "sig-01", "temperature_c": 9.7})
    sent, nonce = iso(datetime.now(timezone.utc)), "nonce-0123456789ab"
    signature = hmac.new(key, "\n".join(["sig-01", nonce, sent, payload]).encode(), hashlib.sha256).hexdigest()
    envelope = {"protocol": "indra_hmac_v1", "node_id": "sig-01", "nonce": nonce, "sent_at_utc": sent,
                "payload_base64": base64.b64encode(payload.encode()).decode(), "signature_hex": signature}
    headers = {"X-Indra-Token": "s3cret"}
    assert client.post("/api/ingest", json=envelope, headers=headers).status_code == 200
    assert client.post("/api/ingest", json={**envelope, "signature_hex": "0" * 64}, headers=headers).status_code == 400


def test_cors_only_when_configured(tmp_path):
    plain = TestClient(create_app(tmp_path / "a.sqlite", mandi_data_dir=tmp_path / "c"))
    assert "access-control-allow-origin" not in plain.get("/api/sensors", headers={"Origin": "http://x.test"}).headers
    cors = TestClient(create_app(tmp_path / "b.sqlite", mandi_data_dir=tmp_path / "c",
                                 cors_origins="http://localhost:3000"))
    r = cors.get("/api/sensors", headers={"Origin": "http://localhost:3000"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_distant_node_does_not_distort_lapse_rate(client):
    client.post("/api/ingest", json={"node_id": "ridge-01", "temperature_c": 14.8, "lat": 31.725, "lon": 76.942, "elevation_m": 1280})
    client.post("/api/ingest", json={"node_id": "basin-02", "temperature_c": 18.8, "lat": 31.698, "lon": 76.918, "elevation_m": 710})
    client.post("/api/ingest", json={"node_id": "delhi-09", "temperature_c": 26.2, "lat": 28.61, "lon": 77.21, "elevation_m": 216})
    spatial = client.get("/api/sensors/combined?forecast=false").json()["network"]["spatial"]
    assert spatial["nodes_used"] == ["basin-02", "ridge-01"]
    assert spatial["lapse_rate_c_per_km"] == pytest.approx(-7.018, abs=1e-3)


def test_sensor_heatmap_transect_area_and_sync_window(client):
    base = {"relative_humidity_pct": 80, "pm25_ug_m3": 20, "pm10_ug_m3": 30, "wind_speed_mps": 2}
    assert client.get("/api/sensors/heatmap").json()["status"] == "UNAVAILABLE"
    # master, ridge and basin along one valley -> transect (line), with an elevation warning
    for node, lat, lon, el, t in (("master-00", 31.710, 76.930, 760, 18.4), ("ridge-01", 31.725, 76.942, 1280, 14.8),
                                  ("basin-02", 31.698, 76.918, 710, 18.8)):
        client.post("/api/ingest", json={"node_id": node, "temperature_c": t, "pressure_hpa": 900, "lat": lat,
                                         "lon": lon, "elevation_m": el, **base})
    line = client.get("/api/sensors/heatmap?channel=temperature_c").json()
    assert line["status"] == "LINE_ESTIMATE" and line["features"]
    assert line["minimum"] == pytest.approx(14.8) and line["maximum"] == pytest.approx(18.8)
    assert "elevation" in line["elevation_note"]
    # a reading far older than the others is left out, not mixed in
    old = iso(datetime.now(timezone.utc) - timedelta(minutes=10))
    client.post("/api/ingest", json={"node_id": "old-09", "timestamp_utc": old, "temperature_c": 30, "lat": 31.6,
                                     "lon": 77.1, **base})
    maps = client.get("/api/sensors/parameter-maps").json()
    assert {"id": "old-09", "reason": "OLDER_THAN_SYNC_WINDOW"} in maps["excluded_nodes"]


def test_sensor_heatmap_area_for_spread_nodes(client):
    for node, lat, lon in (("a", 31.70, 76.90), ("b", 31.75, 76.95), ("c", 31.70, 77.00)):
        client.post("/api/ingest", json={"node_id": node, "temperature_c": 17, "pm25_ug_m3": 20, "lat": lat, "lon": lon})
    area = client.get("/api/sensors/heatmap?channel=pm25_ug_m3").json()
    assert area["status"] == "AREA_ESTIMATE" and len(area["features"]) > 50
    assert client.get("/api/sensors/heatmap?channel=bogus").status_code == 422


def test_two_nodes_10km_apart_get_a_full_area_map(client):
    import math
    km_lon = 1 / (111.195 * math.cos(math.radians(31.71)))
    client.post("/api/ingest", json={"node_id": "master-00", "pm25_ug_m3": 30, "lat": 31.71, "lon": 76.93})
    client.post("/api/ingest", json={"node_id": "slave-01", "pm25_ug_m3": 10, "lat": 31.71, "lon": 76.93 + 10 * km_lon})
    area = client.get("/api/sensors/heatmap?channel=pm25_ug_m3").json()
    assert area["status"] == "AREA_ESTIMATE" and area["mode"] == "radius"
    assert area["radius_km"] == pytest.approx(7.5)          # 0.75 x 10 km spacing: the gap is covered
    values = [f["properties"]["value"] for f in area["features"]]
    assert len(values) > 500 and 10 <= min(values) and max(values) <= 30   # never outside measured range
    assert all(0 <= f["properties"]["confidence"] <= 1 and f["properties"]["distance_km"] <= 7.5
               for f in area["features"])
    wider = client.get("/api/sensors/heatmap?channel=pm25_ug_m3&radius_km=12").json()
    assert wider["radius_km"] == 12 and len(wider["features"]) > len(values) * 0.9
    strict = client.get("/api/sensors/heatmap?channel=pm25_ug_m3&mode=hull").json()
    assert strict["mode"] == "hull" and strict["status"] == "LINE_ESTIMATE"
    assert client.get("/api/sensors/heatmap?radius_km=500").status_code == 422


def test_three_nodes_master_two_slaves_any_spacing(client):
    """Master + 2 slaves: full area map whether they are ~300 m (ESP-NOW) or ~5 km apart."""
    import math
    k, d = 1 / (111.195 * math.cos(math.radians(31.71))), 1 / 111.195
    for sep in (0.3, 5.0):
        for n, dx, dy, pm in (("master-00", 0, 0, 30), ("slave-01", sep, 0, 12), ("slave-02", sep / 2, sep * 0.8, 20)):
            client.post("/api/ingest", json={"node_id": n, "pm25_ug_m3": pm, "lat": 31.71 + dy * d, "lon": 76.93 + dx * k})
        area = client.get("/api/sensors/heatmap?channel=pm25_ug_m3").json()
        assert area["status"] == "AREA_ESTIMATE" and area["node_count"] == 3
        assert area["radius_km"] == pytest.approx(min(max(0.75 * sep, 0.25), 25), rel=0.1)
        values = [f["properties"]["value"] for f in area["features"]]
        assert len(values) > 500 and 12 <= min(values) and max(values) <= 30

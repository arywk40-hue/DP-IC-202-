"""Geographic support, synthetic-category provenance and end-to-end API checks."""

import copy
import json
import shutil

import numpy as np
import pytest
from fastapi.testclient import TestClient

from ml.himachal.parameter_maps import geojson, idw, parameter_maps
from ml.himachal.weather_categories import (
    MODEL,
    WeatherCategories,
    episode_features,
    synthetic_episodes,
)
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from server.dashboard import assess, create_app, weather_demo_observations

NOW = "2026-10-21T06:00:00Z"


def points():
    return [
        {
            "id": str(i),
            "physicalSiteId": str(i),
            "lat": 31.7 + a,
            "lng": 76.9 + b,
            "timestamp": 1000000,
            "stale": False,
            "sourceClass": "synthetic_demo",
            "sourceId": "test_fixture",
            "sourceCellId": None,
            "pressureReference": "station",
            "sensors": dict(
                zip(
                    RAW_SENSOR_COLUMNS, [20 + i, 60 + i, 930 + i, 30 + i, 60 + i, 3 + i]
                )
            ),
        }
        for i, (a, b) in enumerate([(0, 0), (0, 0.02), (0.02, 0), (0.02, 0.02)])
    ]


def test_idw_reproduces_known_measurements_and_midpoint_without_overshoot():
    xy = np.array([[0, 0], [10, 0]])
    np.testing.assert_allclose(
        idw(xy, [10, 30], [[0, 0], [5, 0], [10, 0]]), [10, 20, 30]
    )
    np.testing.assert_array_equal(
        idw(xy, [90, 90], [[1.1, 0], [3.7, 0], [9.2, 0]]), [90, 90, 90]
    )


def test_all_six_surfaces_have_units_and_conservative_geographic_support():
    bundle = parameter_maps(points(), 12)
    assert bundle["status"] == "AREA_ESTIMATE" and set(bundle["layers"]) == set(
        RAW_SENSOR_COLUMNS
    )
    assert bundle["probability"] is None and not bundle["field_validated"]
    for name, layer in bundle["layers"].items():
        assert layer["supported_cells"] == 144 and layer["node_count"] == 4
        assert layer["minimum"] >= points()[0]["sensors"][name]
        assert layer["maximum"] <= points()[-1]["sensors"][name]
        shape = geojson(bundle, name)
        assert len(shape["features"]) == 144
        assert shape["features"][0]["geometry"]["type"] == "Polygon"
    # A missing corner is not extrapolated into the unsupported half-square.
    triangle = parameter_maps(points()[:3], 12)
    assert 0 < triangle["layers"]["temperature_c"]["supported_cells"] < 144
    assert triangle["layers"]["temperature_c"]["values"][-1][-1] is None
    json.dumps(bundle, allow_nan=False)


def test_two_points_support_only_a_line_and_one_point_never_an_area():
    bundle = parameter_maps(points()[:2], 8)
    assert bundle["status"] == "LINE_ESTIMATE" and bundle["shape"] == [1, 8]
    assert all(
        f["geometry"]["type"] == "LineString"
        for f in geojson(bundle, "temperature_c")["features"]
    )
    one = parameter_maps(points()[:1])
    assert not one["layers"]


def test_no_mixed_sources_stale_or_duplicate_cell_can_invent_coverage():
    p = points()
    p[0]["sourceClass"] = "modeled_grid"
    assert parameter_maps(p)["status"] == "UNAVAILABLE"
    p = points()
    for n in p:
        n.update(sourceClass="modeled_grid", sourceCellId="same-provider-cell")
    assert len(parameter_maps(p)["nodes"]) == 1
    p = points()
    p[0]["timestamp"] += 1000
    assert (
        not parameter_maps(p)["layers"]
        and len(parameter_maps(p)["excluded_nodes"]) == 3
    )
    p = points()
    for n in p:
        n["stale"] = True
    assert parameter_maps(p)["stale"] and "Historical" in parameter_maps(p)["reason"]


def test_channel_missingness_changes_its_own_support_only():
    p = points()
    for n in p[1:]:
        n["sensors"]["pm25_ug_m3"] = None
    b = parameter_maps(p)
    assert b["layers"]["pm25_ug_m3"]["supported_cells"] == 0
    assert b["layers"]["temperature_c"]["supported_cells"] > 0
    for resolution in [0, 41, 2.5]:
        with pytest.raises(ValueError):
            parameter_maps(p, resolution)
    with pytest.raises(ValueError):
        geojson(b, "rainfall")


def test_synthetic_episodes_are_reproducible_independent_and_bounded():
    a, x, y = synthetic_episodes(500, 55)
    b, _, _ = synthetic_episodes(500, 55)
    np.testing.assert_array_equal(a, b)
    assert x.shape == (500, 13) and y.shape == (500, 10)
    assert not np.array_equal(a, synthetic_episodes(500, 56)[0])
    assert np.all(a[:, :, 3] <= a[:, :, 4]) and np.isfinite(x).all()
    np.testing.assert_array_equal(x, episode_features(a))


def test_runtime_abstains_on_missing_history_gaps_and_domain():
    e = WeatherCategories()
    raw = weather_demo_observations(NOW)

    def history(node):
        return [
            dict(timestamp=r["timestamp_utc"], **r["measurements"])
            for r in raw
            if r["node_id"] == node
        ]

    heat = history("demo-05")
    r = e.predict(heat, 3600)
    assert (
        r["status"] == "SYNTHETIC_PATTERN_SCORES_ONLY"
        and "heatwave_like" in r["matched"]
    )
    assert not r["field_validated"] and r["probability"] is None and not r["calibrated"]
    assert len(r["categories"]) == 10 and all(
        0 <= v["score"] <= 1 for v in r["categories"]
    )
    assert e.predict(heat[-1:], 3600)["status"] == "UNAVAILABLE"
    assert e.predict(heat[:-3] + heat[-2:], 3600)["status"] == "UNAVAILABLE"
    altered = copy.deepcopy(heat)
    altered[-1]["pm10_ug_m3"] = None
    assert e.predict(altered, 3600)["status"] == "UNAVAILABLE"
    altered = copy.deepcopy(heat)
    altered[-1]["temperature_c"] = 70
    assert e.predict(altered, 3600)["status"] == "OUTSIDE_SYNTHETIC_DOMAIN"


def test_classifier_artifact_tampering_fails_closed(tmp_path):
    shutil.copytree(MODEL, tmp_path / "model")
    p = tmp_path / "model/rainstorm.txt"
    p.write_text(p.read_text() + " ")
    with pytest.raises(ValueError, match="checksum"):
        WeatherCategories(tmp_path / "model")


def test_complete_feature_api_and_persisted_migration(tmp_path):
    with TestClient(
        create_app(tmp_path / "nodes.sqlite", clock=lambda: 1792562400)
    ) as client:
        client.app.state.store.replace(assess(weather_demo_observations(NOW), now=NOW))
        b = client.get("/api/parameter-heatmaps").json()
        assert b["status"] == "AREA_ESTIMATE" and len(b["layers"]) == 6
        for name in RAW_SENSOR_COLUMNS:
            response = client.get("/api/kriging/heatmap", params={"channel": name})
            assert response.status_code == 200 and response.json()["features"]
        assert client.get("/api/kriging/heatmap?channel=rainfall").status_code == 422
        assert client.get("/api/parameter-heatmaps?resolution=1000").status_code == 422
        c = client.get("/api/nodes/demo-05/telemetry").json()["weatherCategories"]
        assert "heatwave_like" in c["matched"] and c["probability"] is None
        stored = client.app.state.store.all()
        for n in stored:
            n.pop("weatherCategories")
        client.app.state.store.replace(stored)
    with TestClient(create_app(tmp_path / "nodes.sqlite")) as restarted:
        assert restarted.get("/api/nodes/demo-05/telemetry").json()[
            "weatherCategories"
        ]["profile_sha256"]

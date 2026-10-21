"""Synthetic physics, time contracts, provenance and dashboard wiring."""

import copy
import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from ml.himachal.hazard_scenarios import (
    CONFIG,
    HazardScenarios,
    event_outcomes,
    simulate,
)
from ml.himachal.weather_categories import synthetic_episodes
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS


def history(cadence=3600):
    times = pd.date_range(
        "2026-10-21T00:00Z", "2026-10-21T06:00Z", freq=pd.Timedelta(seconds=cadence)
    )
    return [
        dict(
            timestamp=t.isoformat(),
            **dict(
                zip(RAW_SENSOR_COLUMNS, [20, 95, 930 - i / len(times) * 6, 20, 40, 12])
            ),
        )
        for i, t in enumerate(times)
    ]


def test_published_rain_threshold_and_runoff_units_with_known_cases():
    cfg = json.loads(CONFIG.read_text())
    # 100 mm/h, 1 km2, runoff coefficient 0.95 => 26.39 m3/s > 20.
    for intensity, expected_cloud in [(0, False), (99.9, False), (100, True)]:
        rain = np.full((1, 1, 12), intensity)
        one = np.ones((1, 1))
        out = event_outcomes(
            rain, one, one * 100, one * 0.2, one * 20, one, one, one.astype(bool), cfg
        )
        assert bool(out[0, 0, 0]) is expected_cloud
        assert bool(out[0, 0, 1]) is (intensity > 0)
        assert bool(out[0, 0, 2]) is (intensity > 0)
    # At six-hour rainfall duration, threshold equals 73.9 * 6^-0.79.
    assert cfg["landslide_id_coefficient"] * 6 ** cfg[
        "landslide_id_exponent"
    ] == pytest.approx(17.94340876)
    assert cfg["landslide_duration_hours"] == [5, 6]


def test_simulation_is_reproducible_and_keeps_latents_separate_from_inputs():
    episodes, x, _ = synthetic_episodes(8, 811)
    a = simulate(episodes, seed=1, draws=256, retain=True)
    b = simulate(episodes, seed=1, draws=256, retain=True)
    assert x.shape == (8, 13)
    for family in a:
        for k in a[family]:
            np.testing.assert_array_equal(a[family][k], b[family][k])
        np.testing.assert_allclose(a[family]["fraction"], a[family]["outcomes"].mean(1))
        assert a[family]["outcomes"].shape == (8, 256, 3)
        assert np.isfinite(a[family]["fraction"]).all()
    # Paired worlds isolate prior sensitivity instead of confounding it with fresh RNG.
    assert np.all(a["drier"]["fraction"] <= a["central"]["fraction"])
    assert np.all(a["central"]["fraction"] <= a["wetter"]["fraction"])
    changed = simulate(episodes, seed=2, draws=256)
    assert not np.array_equal(a["central"]["fraction"], changed["central"]["fraction"])


def test_same_sensors_different_unobserved_conditions_change_simulated_outcomes():
    ep = np.array([[[20, 96, 940 - tick, 20, 40, 15] for tick in range(7)]])
    out = simulate(ep, seed=333, draws=4096)
    assert (out["wetter"]["fraction"] - out["drier"]["fraction"])[0, 1] > 0.1
    assert (out["wetter"]["fraction"] - out["drier"]["fraction"])[0, 2] > 0.1


def test_complete_native_history_provenance_no_probabilities_or_alerts():
    engine = HazardScenarios()
    for cadence in [900, 3600]:
        h = history(cadence)
        a = engine.predict(h, cadence)
        assert a == engine.predict(h, cadence)
        assert a["status"] == "SYNTHETIC_SCENARIOS_ONLY"
        assert a["implementation_sha256"] == engine.implementation_sha256
        assert a["probability"] is None and not a["public_alerts_enabled"]
        assert not a["calibrated"] and not a["field_validated"]
        assert (
            len(a["targets"]) == 3
            and a["forecast_timestamp"] == "2026-10-21T12:00:00+00:00"
        )
        assert all(t["probability"] is None for t in a["targets"])
        # Removing even a native non-hourly reading must abstain.
        assert engine.predict(h[:1] + h[2:], cadence)["status"] == "UNAVAILABLE"
        json.dumps(a, allow_nan=False)
    h = history()
    h[-1]["pm25_ug_m3"] = 500
    assert engine.predict(h, 3600)["status"] == "OUTSIDE_SYNTHETIC_DOMAIN"


def test_bad_inputs_and_no_fake_rainfall_measurements():
    engine = HazardScenarios()
    for invalid in [0, 3601, 701, True]:
        with pytest.raises(ValueError):
            engine.predict(history(), invalid)
    h = history()
    for value in [None, float("inf"), float("nan")]:
        bad = copy.deepcopy(h)
        bad[2]["pressure_hpa"] = value
        assert engine.predict(bad, 3600)["status"] == "UNAVAILABLE"
    assert engine.predict([], 3600)["status"] == "UNAVAILABLE"
    with pytest.raises(ValueError):
        engine.predict(h + [h[-1]], 3600)
    assert set(h[0]) == {"timestamp", *RAW_SENSOR_COLUMNS}


def test_backend_migrates_stored_nodes_without_changing_forecast_or_event_gates(
    tmp_path,
):
    from server.dashboard import Store, assess, create_app, demo_observations

    nodes = assess(
        demo_observations("2026-10-21T06:00:00Z"), now="2026-10-21T06:00:00Z"
    )
    original = copy.deepcopy(nodes[0]["forecast6h"])
    assert nodes[0]["hazardScenarios"]["status"] == "SYNTHETIC_SCENARIOS_ONLY"
    for i, n in enumerate(nodes):
        if i == 0:
            n["hazardScenarios"]["implementation_sha256"] = "old-code-fingerprint"
        else:
            n.pop("hazardScenarios")
    db = tmp_path / "nodes.sqlite"
    Store(db).replace(nodes)
    with TestClient(create_app(db)) as client:
        t = client.get("/api/nodes/demo-01/telemetry").json()
        assert t["forecast6h"] == original
        assert t["hazardScenarios"]["source_class"] == "synthetic_demo"
        assert (
            t["hazardScenarios"]["implementation_sha256"]
            == HazardScenarios().implementation_sha256
        )
        assert t["hazardScenarios"]["status"] == "SYNTHETIC_SCENARIOS_ONLY"
        assert client.get("/api/status").json()["empiricalHazardModels"] == "NOT_READY"

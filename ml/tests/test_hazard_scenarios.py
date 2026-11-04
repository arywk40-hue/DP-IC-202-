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
        assert a["range_kind"] == "ASSUMPTION_SENSITIVITY_NOT_CONFIDENCE_INTERVAL"
        assert {source["id"] for source in a["research_sources"]} == {
            "singh_thapliyal_2022", "dahal_hasegawa_2008", "txdot_rational_method",
            "wmo_ffg_guide", "manali_2023_case",
        }
        assert a["parameter_provenance"]["thresholds_and_methods"][
            "cloudburst_threshold_mm_in_1h"
        ]["kind"] == "published_definition_transferred_as_threshold"
        assert (
            len(a["targets"]) == 3
            and a["forecast_timestamp"] == "2026-10-21T12:00:00+00:00"
        )
        assert all(t["probability"] is None for t in a["targets"])
        for target in a["targets"]:
            assert set(target["assumption_cases"]) == {"drier", "central", "wetter"}
            assert target["scenario_fraction"] == target["families"]["central"]
            assert target["assumption_range"] == [
                min(target["families"].values()), max(target["families"].values())
            ]
            assert all(
                target["assumption_cases"][case]["scenario_fraction"]
                == target["families"][case]
                for case in target["families"]
            )
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


def test_live_mandi_adapter_exposes_simulated_hazards_separately_from_forecast(tmp_path):
    from server.dashboard import Store, assess, create_app
    from server.tests.mandi_fixture import NOW, mandi_api_rows

    nodes = assess(mandi_api_rows(), now=NOW.isoformat())
    original = copy.deepcopy(nodes[0]["forecast6h"])
    assert nodes[0]["sourceClass"] == "modeled_grid"
    assert nodes[0]["hazardScenarios"]["source_class"] == "modeled_grid"
    assert nodes[0]["hazardScenarios"]["status"] == "SYNTHETIC_SCENARIOS_ONLY"
    assert nodes[0]["hazardScenarios"]["probability"] is None
    assert nodes[0]["hazardScenarios"]["source_id"] == "OpenMeteo_current_ECMWF_IFS_CAMS_global"
    assert nodes[0]["hazardScenarios"]["coordinates"] == [31.71, 76.93]
    assert nodes[0]["weatherCategories"]["source_class"] == "modeled_grid"
    assert nodes[0]["weatherCategories"]["feature_count"] == 13
    assert nodes[0]["weatherCategories"]["training_rows_by_role"] == {
        "train": 16000, "validation": 4000, "test": 4000
    }
    assert nodes[0]["weatherCategories"]["score_kind"] == "SYNTHETIC_PATTERN_SCORE_NOT_EVENT_PROBABILITY"
    db = tmp_path / "nodes.sqlite"
    Store(db).replace(nodes)
    with TestClient(create_app(db)) as client:
        telemetry = client.get("/api/nodes/mandi-api-current/telemetry").json()
        assert telemetry["forecast6h"] == original
        assert telemetry["hazardScenarios"]["status"] == "SYNTHETIC_SCENARIOS_ONLY"
        assert telemetry["hazardScenarios"]["calibrated"] is False
        assert telemetry["weatherCategories"]["calibrated"] is False


def test_missing_hours_and_gap_abstention():
    """Missing hourly observations or irregular intervals must abstain completely."""
    engine = HazardScenarios()
    h = history(3600)
    assert len(h) == 7  # 6-hour span: 0h, 1h, 2h, 3h, 4h, 5h, 6h

    # Dropping any middle hour leaves a gap: must return UNAVAILABLE
    for i in range(1, 6):
        gap = h[:i] + h[i + 1:]
        res = engine.predict(gap, 3600)
        assert res["status"] == "UNAVAILABLE"
        assert "six_complete_hours_of_native_measurements" in res["missing_features"] or "cadence" in res["reason"]

    # History too short (< 6 hours total)
    short = h[2:]  # only 4 hours
    res = engine.predict(short, 3600)
    assert res["status"] == "UNAVAILABLE"

    # Particulate domain violation (PM2.5 > PM10) must abstain
    inverted_pm = copy.deepcopy(h)
    inverted_pm[-1]["pm25_ug_m3"] = 80
    inverted_pm[-1]["pm10_ug_m3"] = 40
    res = engine.predict(inverted_pm, 3600)
    assert res["status"] == "OUTSIDE_SYNTHETIC_DOMAIN"

    # Out-of-bounds temperature (-30 C is below -25 C lower bound)
    extreme_temp = copy.deepcopy(h)
    extreme_temp[-1]["temperature_c"] = -30
    res = engine.predict(extreme_temp, 3600)
    assert res["status"] == "OUTSIDE_SYNTHETIC_DOMAIN"


def test_deterministic_repeatability_and_provenance():
    """Identical history and configuration must produce identical seeds and outcomes."""
    engine = HazardScenarios()
    h1 = history(3600)
    h2 = copy.deepcopy(h1)

    res1 = engine.predict(h1, 3600)
    res2 = engine.predict(h2, 3600)

    assert res1["seed"] == res2["seed"]
    assert res1["config_sha256"] == res2["config_sha256"]
    assert res1["implementation_sha256"] == res2["implementation_sha256"]
    assert res1["field_validated"] is False
    assert res1["calibrated"] is False
    assert res1["public_alerts_enabled"] is False

    for t1, t2 in zip(res1["targets"], res2["targets"]):
        assert t1["id"] == t2["id"]
        assert t1["scenario_fraction"] == t2["scenario_fraction"]
        assert t1["assumption_range"] == t2["assumption_range"]
        assert t1["assumption_cases"] == t2["assumption_cases"]
        assert t1["mc_standard_error"] == t2["mc_standard_error"]

    # Changing any past measurement alters the deterministic seed
    modified = copy.deepcopy(h1)
    modified[0]["temperature_c"] += 0.5
    res_mod = engine.predict(modified, 3600)
    assert res_mod["seed"] != res1["seed"]


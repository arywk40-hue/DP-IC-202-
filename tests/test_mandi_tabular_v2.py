"""V2 runtime, validation simplex and tamper checks; no raw source needed in CI."""

import json
import shutil
import numpy as np
import pandas as pd
import pytest

from ml.india_mandi.tabular_v2 import DEFAULT_MODEL, FAMILIES, TabularV2, convex_weights
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS


def frame():
    f = pd.DataFrame(
        np.tile([20.0, 60.0, 930.0, 30.0, 60.0, 3.0], (30, 1)),
        columns=RAW_SENSOR_COLUMNS,
    )
    f["location_id"] = "synthetic-runtime-check"
    f["timestamp_utc"] = pd.date_range("2026-01-01", periods=30, freq="h", tz="UTC")
    return f


def test_v2_runs_six_outputs_and_preserves_missing_history():
    e = TabularV2()
    f = frame()
    out = e.predict(f)
    assert (
        out.iloc[-1].model_id == "india_mandi_tabular_v2"
        and out.iloc[-1].status == "HYBRID_READY"
    )
    assert out.iloc[0].status == "WARMING_UP_PERSISTENCE"
    assert np.isfinite(
        out.filter(like="forecast_").drop(columns=["forecast_timestamp_utc"]).to_numpy()
    ).all()
    f.loc[len(f) - 1, "pm25_ug_m3"] = np.nan
    assert e.predict(f).iloc[-1].status == "MISSING_CURRENT_SENSOR"
    assert e.predict(frame().drop(index=25)).iloc[-1].status == "WARMING_UP_PERSISTENCE"


def test_validation_solver_retains_pure_family_and_convex_contract():
    truth = np.arange(60.0).reshape(10, 6)
    candidates = {k: truth + (i + 1) for i, k in enumerate(FAMILIES)}
    candidates["mlp_v2"] = truth.copy()
    w = convex_weights(candidates, truth)
    assert all(
        h["weights"]["mlp_v2"] == pytest.approx(1)
        and h["validation_mae"] == pytest.approx(0)
        for h in w["heads"].values()
    )
    candidates["lightgbm"] = np.zeros((2, 6))
    with pytest.raises(ValueError):
        convex_weights(candidates, truth)


def test_v2_tampered_weights_and_manifest_omission_fail_closed(tmp_path):
    folder = tmp_path / "model"
    shutil.copytree(DEFAULT_MODEL, folder)
    p = folder / "ensemble_weights.json"
    p.write_text(p.read_text() + " ")
    with pytest.raises(ValueError, match="checksum"):
        TabularV2(folder)
    shutil.copyfile(DEFAULT_MODEL / "ensemble_weights.json", p)
    profile = json.loads((folder / "profile.json").read_text())
    profile["files"].pop("online_scaler.npz")
    (folder / "profile.json").write_text(json.dumps(profile))
    with pytest.raises(ValueError, match="manifest"):
        TabularV2(folder)


def test_default_backend_model_lab_and_shadow_state_are_distinct_from_replay(tmp_path):
    from fastapi.testclient import TestClient
    from server.dashboard import create_app
    from ml.india_mandi.hybrid import DEFAULT_MODEL as legacy

    with TestClient(
        create_app(tmp_path / "nodes.sqlite", online_state=tmp_path / "online.sqlite")
    ) as client:
        assert (
            client.get("/api/status").json()["forecastModel"]
            == "india_mandi_tabular_v2"
        )
        lab = client.get("/api/model-lab").json()
        assert (
            lab["data_rows"] == 35520
            and lab["features"] == 66
            and not lab["field_validated"]
        )
        assert lab["online"]["enabled"] and lab["online"]["updates"] == 0
        assert lab["online"]["role"] == "SHADOW_ONLY_OFFLINE_OUTPUTS_UNCHANGED"
    with TestClient(create_app(tmp_path / "legacy.sqlite", model_dir=legacy)) as client:
        assert not client.get("/api/model-lab").json()["configured"]

"""Delayed-label learning and checkpoint causality; synthetic fixtures only."""

import json

import numpy as np
import pandas as pd
import pytest

from ml.india_mandi.online import OnlineLearner

START = pd.Timestamp("2026-01-01", tz="UTC")
BASE = np.array([20.0, 60.0, 930.0, 30.0, 60.0, 3.0])


def learner(path):
    return OnlineLearner(
        path, "frozen-test-model", np.zeros(66), np.ones(66), np.ones(6)
    )


def event(l, h, *, late=False, ns="station", values=None, features=True):
    t = START + pd.Timedelta(hours=h)
    return l.observe(
        ns,
        t,
        t,
        BASE + 1 if values is None else values,
        np.ones(66) if features else None,
        BASE if features else None,
        t + pd.Timedelta(days=3) if late else t,
    )


def test_forecast_before_update_and_exact_six_hour_delay(tmp_path):
    l = learner(tmp_path / "state.sqlite")
    for h in range(6):
        event(l, h)
        assert l.summary()["updates"] == 0
    event(l, 6)
    with l.connect() as db:
        revision, scored, learned = db.execute(
            "SELECT revision,scored,learned_at FROM forecasts WHERE issue=?",
            (int(START.timestamp()),),
        ).fetchone()
        current_revision = db.execute(
            "SELECT revision FROM forecasts WHERE issue=?",
            (int((START + pd.Timedelta(hours=6)).timestamp()),),
        ).fetchone()[0]
    assert (
        revision == 0
        and scored == 1
        and learned == int((START + pd.Timedelta(hours=6)).timestamp())
    )
    assert current_revision == 0  # Forecast at this step precedes the matured update.
    assert l.summary()["updates"] == 1


def test_duplicate_idempotence_and_conflicting_revision_rejected(tmp_path):
    l = learner(tmp_path / "state.sqlite")
    for h in range(12):
        event(l, h)
    before = l.summary()["updates"]
    assert event(l, 0)["duplicate"]
    assert l.observe(
        "station",
        START,
        START + pd.Timedelta(hours=1),
        BASE + 1,
        np.ones(66),
        BASE,
        START + pd.Timedelta(days=1),
    )["duplicate"]
    assert l.summary()["updates"] == before
    with pytest.raises(ValueError, match="revision"):
        event(l, 0, values=BASE + 2)


def test_late_historical_data_does_not_become_live_learning(tmp_path):
    l = learner(tmp_path / "state.sqlite")
    for h in range(12):
        event(l, h, late=True)
    s = l.summary()
    assert (
        s["updates"] == 0
        and s["eligible_forecasts"] == 0
        and s["historical_ineligible_forecasts"] == 12
    )
    assert s["status"] == "HISTORICAL_ONLY_NO_LIVE_UPDATE"


def test_missing_exact_truth_never_uses_nearest_hour_or_null(tmp_path):
    l = learner(tmp_path / "state.sqlite")
    event(l, 0)
    event(l, 7, features=False)
    assert l.summary()["updates"] == 0
    missing = BASE.tolist()
    missing[0] = None
    event(l, 8, values=missing, features=False)
    assert l.summary()["updates"] == 0


def test_restart_reproduces_sgd_state_and_sources_are_separate(tmp_path):
    a = learner(tmp_path / "a.sqlite")
    b = learner(tmp_path / "b.sqlite")
    for h in range(20):
        event(a, h)
        if h == 10:
            b = learner(tmp_path / "b.sqlite")
        event(b, h)
    with a.connect() as db:
        ca = json.loads(db.execute("SELECT checkpoint FROM state").fetchone()[0])
    with b.connect() as db:
        cb = json.loads(db.execute("SELECT checkpoint FROM state").fetchone()[0])
    np.testing.assert_array_equal(ca["coef"], cb["coef"])
    event(a, 0, ns="other-source")
    assert len(a.summary()["namespaces"]) == 2
    assert (
        next(
            s["updates"] for s in a.summary()["namespaces"] if s["id"] == "other-source"
        )
        == 0
    )


def test_future_perturbation_preserves_recorded_predictions(tmp_path):
    l = learner(tmp_path / "a.sqlite")
    for h in range(6):
        event(l, h)
    with l.connect() as db:
        before = db.execute("SELECT shadow FROM forecasts ORDER BY issue").fetchall()
    for h in range(6, 12):
        event(l, h, values=BASE + 10)
    with l.connect() as db:
        after = db.execute(
            "SELECT shadow FROM forecasts ORDER BY issue LIMIT 6"
        ).fetchall()
    assert before == after


def test_scaler_identity_and_processing_clock_fail_closed(tmp_path):
    path = tmp_path / "state.sqlite"
    l = learner(path)
    event(l, 5)
    with pytest.raises(ValueError, match="clock"):
        event(l, 4)
    with pytest.raises(ValueError, match="different model/scaler"):
        OnlineLearner(path, "changed-model", np.zeros(66), np.ones(66), np.ones(6))
    with pytest.raises(ValueError, match="scaler"):
        OnlineLearner(
            tmp_path / "bad.sqlite", "model", np.zeros(66), np.zeros(66), np.ones(6)
        )


def test_native_worker_reuses_persisted_history_and_learns_after_target_arrives(
    tmp_path,
):
    from ml.india_mandi.online import ingest_native
    from ml.india_mandi.tabular_v2 import TabularV2
    from ml.tests.test_himachal_features import native_records

    records = native_records(cadence=3600, hours=30)
    engine = TabularV2()
    path = tmp_path / "live.sqlite"
    first = ingest_native(
        records[:25], path, engine, clock=records[24]["timestamp_utc"]
    )
    assert first["forecasts"] == 1 and first["updates"] == 0
    for row in records[25:]:
        result = ingest_native([row], path, engine, clock=row["timestamp_utc"])
    assert result["updates"] == 1 and result["forecasts"] == 7
    again = ingest_native(
        [records[-1]], path, engine, clock=records[-1]["timestamp_utc"]
    )
    assert again["updates"] == 1


def test_native_worker_explicitly_skips_nonhourly_readings(tmp_path):
    from ml.india_mandi.online import ingest_native
    from ml.india_mandi.tabular_v2 import TabularV2
    from ml.tests.test_himachal_features import native_records

    records = native_records(cadence=900, hours=7)
    result = ingest_native(
        records,
        tmp_path / "native.sqlite",
        TabularV2(),
        clock=records[-1]["timestamp_utc"],
    )
    assert result["skipped_nonhourly_rows"] == len(records) and result["updates"] == 0
    assert result["status"] == "AWAITING_HOURLY_INPUT"


def test_summary_separates_delayed_startup_from_input_hour_forecasts(tmp_path):
    l = learner(tmp_path / "timing.sqlite")
    l.observe(
        "station",
        START,
        START,
        BASE,
        np.ones(66),
        BASE,
        START + pd.Timedelta(hours=5, minutes=45),
    )
    event(l, 6)
    timing = l.summary()["timing"]
    assert timing["scored_delayed_input_forecasts"] == 1
    assert timing["scored_issued_in_input_hour"] == 0
    assert timing["scored_actual_lead_min_minutes"] == 15
    event(l, 12)
    timing = l.summary()["timing"]
    assert timing["scored_delayed_input_forecasts"] == 1
    assert timing["scored_issued_in_input_hour"] == 1
    assert timing["scored_actual_lead_max_minutes"] == 360
    assert timing["verified_full_six_hour_skill"] is False


def test_concurrent_live_writers_take_processing_time_after_lock(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    l = learner(tmp_path / "concurrent.sqlite")

    def submit(h):
        t = START + pd.Timedelta(hours=h)
        return l.observe("same-source", t, t, BASE, None, None, None)

    with ThreadPoolExecutor(max_workers=3) as pool:
        assert all(not r["duplicate"] for r in pool.map(submit, range(10)))
    with l.connect() as db:
        assert db.execute("SELECT count(*) FROM observations").fetchone()[0] == 10
    assert l.summary()["updates"] == 0

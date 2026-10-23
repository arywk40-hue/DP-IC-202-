"""Synthetic PM provenance, determinism and leakage boundaries, not weather skill."""

import numpy as np
import pandas as pd
import pytest

from ml.india_mandi.synthetic_pm import audit, draw_joint, fit_and_generate


def reference():
    t = np.arange(240)
    return pd.DataFrame(
        {
            "timestamp_utc": pd.date_range(
                "2025-01-01", periods=240, freq="h", tz="UTC"
            ),
            "location_id": "synthetic-test",
            "temperature_c": 15 + np.sin(t / 24),
            "relative_humidity_pct": 60 + np.cos(t / 12),
            "pressure_hpa": 930 + np.sin(t / 50),
            "wind_speed_mps": 2 + np.sin(t / 11),
            "pm25_ug_m3": 25 + 10 * np.sin(t / 20),
            "pm10_ug_m3": 50 + 15 * np.sin(t / 20),
        }
    )


def source():
    f = reference().iloc[:120].copy()
    f["timestamp_utc"] = pd.date_range("2024-01-01", periods=120, freq="h", tz="UTC")
    f.loc[0:119, ["pm25_ug_m3", "pm10_ug_m3"]] = np.nan
    f.loc[4, "pm25_ug_m3"] = 12.0
    f.loc[5, "pm10_ug_m3"] = 32.0
    f.loc[6, ["pm25_ug_m3", "pm10_ug_m3"]] = [17.0, 35.0]
    return f


def test_joint_draw_is_seeded_variable_bounded_and_jointly_ordered():
    mean = np.tile(np.log1p([20.0, 30.0]), (400, 1))
    innovations = np.array([[-0.2, -0.3], [0.2, 0.3], [-0.1, 0.1], [0.1, -0.1]])
    a = draw_joint(mean, innovations, [0.8, 0.7], 42)
    np.testing.assert_array_equal(a, draw_joint(mean, innovations, [0.8, 0.7], 42))
    assert not np.array_equal(a, draw_joint(mean, innovations, [0.8, 0.7], 43))
    assert np.isfinite(a).all() and (a >= 0).all() and (a <= 5000).all()
    assert (a[:, 0] <= a[:, 1]).all() and np.std(a[:, 0]) > 0
    assert np.corrcoef(a[:-1, 0], a[1:, 0])[0, 1] > 0.4


def test_missing_only_and_training_only_with_no_future_reference_leakage():
    ref = reference()
    original = source()
    cutoff = "2025-01-09T00:00:00Z"
    generated, _, details = fit_and_generate(ref, original, cutoff, rounds=4)
    ref.loc[
        ref.timestamp_utc >= pd.Timestamp(cutoff),
        ["pm25_ug_m3", "pm10_ug_m3", "temperature_c"],
    ] = 9999.0
    again, _, _ = fit_and_generate(ref, original, cutoff, rounds=4)
    pd.testing.assert_frame_equal(generated, again)
    qa = audit(original, generated)
    assert details["fit_rows"] == 192 and details["synthetic_pm25_rows"] == 118
    assert qa["existing_pm_values_preserved"] and qa["synthetic_pm_rows"] == 119
    assert all(v == 0 for v in qa["missing_after"].values())
    assert set(generated.evidence_kind) == {
        "SYNTHETIC_PM_WITH_MODELED_WEATHER",
        "MODELED_API_VALUES",
    }
    generated.loc[6, "pm25_ug_m3"] = 18.0
    with pytest.raises(ValueError, match="Existing PM"):
        audit(original, generated)


def test_refuses_fabricated_test_labels_and_discontinuous_or_invalid_sources():
    ref = reference()
    f = source()
    with pytest.raises(ValueError, match="validation/test"):
        fit_and_generate(ref, f, "2023-01-01T00:00:00Z", rounds=2)
    with pytest.raises(ValueError, match="Consecutive hourly"):
        fit_and_generate(ref, f.drop(index=12), "2025-02-01T00:00:00Z", rounds=2)
    f.loc[0, "pm10_ug_m3"] = np.inf
    with pytest.raises(ValueError, match="Existing PM"):
        fit_and_generate(ref, f, "2025-02-01T00:00:00Z", rounds=2)

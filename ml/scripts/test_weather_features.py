"""Reproduce synthetic-category metrics and verify one-point heatmap abstention."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import json

from fastapi.testclient import TestClient
from sklearn.metrics import accuracy_score, f1_score

from ml.himachal.weather_categories import (
    CATEGORIES,
    WeatherCategories,
    synthetic_episodes,
)
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from server.dashboard import assess, create_app
from server.tests.mandi_fixture import NOW, mandi_api_rows


def main():
    engine = WeatherCategories()
    _, x, y = synthetic_episodes(4000, 404)
    scores = engine.scores(x)
    pred = scores >= engine.thresholds
    report = ROOT / "ml/reports/weather_features_v1"
    report.mkdir(parents=True, exist_ok=True)
    local = ROOT / "ml/data/himachal/weather_features_v1"
    local.mkdir(parents=True, exist_ok=True)
    raw = mandi_api_rows(now=NOW, hours=73)
    nodes = assess(raw, now=NOW.isoformat())
    with TestClient(create_app(local / "verification.sqlite")) as c:
        c.app.state.store.replace(nodes)
        bundle = c.get("/api/parameter-heatmaps").json()
        assert not bundle["layers"] and bundle["status"] == "UNAVAILABLE"
        for channel in RAW_SENSOR_COLUMNS:
            response = c.get("/api/kriging/heatmap", params={"channel": channel})
            assert response.status_code == 200 and not response.json()["features"]
    result = {
        "evidence": "SYNTHETIC_SOFTWARE_AND_PROXY_LABEL_TEST_NOT_REAL_WEATHER_VALIDATION",
        "api_input": "DETERMINISTIC_TEST_FIXTURE_NOT_LIVE_OPEN_METEO",
        "fixture_only": True,
        "profile_sha256": engine.sha256,
        "test_episodes": 4000,
        "synthetic_exact_match": float(accuracy_score(y, pred)),
        "synthetic_macro_f1": float(
            f1_score(y, pred, average="macro", zero_division=0)
        ),
        "matched_categories": {
            k: int(pred[:, j].sum()) for j, k in enumerate(CATEGORIES)
        },
        "surface_status": bundle["status"],
        "surface_reason": bundle["reason"],
        "scenarios": [
            {
                "id": n["id"],
                "source": n["sourceClass"],
                "sensors": n["sensors"],
                "classification": n["weatherCategories"],
            }
            for n in nodes
        ],
        "field_validated": False,
        "real_event_probability_available": False,
    }
    (report / "integration_results_mandi_single_point.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n"
    )
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "evidence",
                    "test_episodes",
                    "synthetic_exact_match",
                    "synthetic_macro_f1",
                    "surface_status",
                ]
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

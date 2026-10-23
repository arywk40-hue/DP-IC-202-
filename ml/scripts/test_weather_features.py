"""Reproduce saved synthetic-category metrics and all six spatial API layers."""

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
from server.dashboard import assess, create_app, weather_demo_observations


def main():
    engine = WeatherCategories()
    _, x, y = synthetic_episodes(4000, 404)
    scores = engine.scores(x)
    pred = scores >= engine.thresholds
    report = ROOT / "ml/reports/weather_features_v1"
    report.mkdir(parents=True, exist_ok=True)
    local = ROOT / "ml/data/himachal/weather_features_v1"
    local.mkdir(parents=True, exist_ok=True)
    now = "2026-10-21T06:00:00Z"
    raw = weather_demo_observations(now)
    nodes = assess(raw, now=now)
    (local / "demo_observations.json").write_text(
        json.dumps(raw, indent=2, allow_nan=False) + "\n"
    )
    with TestClient(create_app(local / "verification.sqlite")) as c:
        c.app.state.store.replace(nodes)
        bundle = c.get("/api/parameter-heatmaps").json()
        assert len(bundle["layers"]) == 6 and bundle["status"] == "AREA_ESTIMATE"
        for channel in RAW_SENSOR_COLUMNS:
            response = c.get("/api/kriging/heatmap", params={"channel": channel})
            assert response.status_code == 200 and response.json()["features"]
    result = {
        "evidence": "SYNTHETIC_SOFTWARE_AND_PROXY_LABEL_TEST_NOT_REAL_WEATHER_VALIDATION",
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
        "surface_units_and_support": {
            k: {
                field: v[field]
                for field in [
                    "unit",
                    "node_count",
                    "supported_cells",
                    "minimum",
                    "maximum",
                ]
            }
            for k, v in bundle["layers"].items()
        },
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
    (report / "integration_results.json").write_text(
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

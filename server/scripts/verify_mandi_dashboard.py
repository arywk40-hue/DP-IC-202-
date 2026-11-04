"""Verify a running local dashboard against its live Mandi API receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS
from ml.india_mandi.live import atomic_json


EXPECTED_UNITS = dict(zip(RAW_SENSOR_COLUMNS, ["degC", "%", "hPa", "ug/m3", "ug/m3", "m/s"]))
EXPECTED_PROVIDER_UNITS = {
    "weather": {"temperature_2m": "°C", "relative_humidity_2m": "%", "surface_pressure": "hPa", "wind_speed_10m": "m/s"},
    "air": {"pm2_5": "µg/m³", "pm10": "µg/m³"},
}


def get_json(base_url: str, path: str) -> dict:
    """Fetch one local dashboard endpoint and decode its JSON response."""
    request = urllib.request.Request(base_url.rstrip("/") + path)
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise ValueError(f"Dashboard endpoint failed: {path} ({response.status})")
        return json.load(response)


def raw_receipt_files(source_dir: Path, receipt: dict) -> dict:
    """Find current raw API response files by their receipt hashes."""
    result = {}
    for kind, metadata in receipt["source_receipts"].items():
        expected = metadata["sha256"]
        matches = [
            path for path in (source_dir / "raw").glob(f"*/{kind}.json")
            if hashlib.sha256(path.read_bytes()).hexdigest() == expected
        ]
        if not matches:
            raise ValueError(f"Could not resolve raw {kind} response from receipt hash")
        value = json.loads(max(matches, key=lambda path: path.parent.name).read_text())
        units = {key: str(unit).replace("μ", "µ") for key, unit in value.get("hourly_units", {}).items()}
        # Open-Meteo includes the non-measurement `time: iso8601` entry and
        # uses Greek mu for particulate units. Validate requested channels only.
        if any(units.get(key) != unit for key, unit in EXPECTED_PROVIDER_UNITS[kind].items()):
            raise ValueError(f"Unexpected Open-Meteo units in {kind} response")
        result[kind] = {
            "sha256": expected,
            "returned_coordinates": [value["latitude"], value["longitude"]],
            "hourly_units": value["hourly_units"],
        }
    return result


def verify(base_url: str, source_dir: Path) -> dict:
    """Check current source, six channels, forecast, hazards and single-point maps."""
    source_dir = Path(source_dir)
    receipt = json.loads((source_dir / "latest_receipt.json").read_text())
    status = get_json(base_url, "/api/status")
    nodes = get_json(base_url, "/api/nodes")
    if len(nodes) != 1 or nodes[0]["id"] != "mandi-api-current":
        raise ValueError("Expected exactly one active Mandi API point")
    telemetry = get_json(base_url, "/api/nodes/mandi-api-current/telemetry")
    maps = get_json(base_url, "/api/parameter-heatmaps")
    feed = status["mandiApi"]
    if not feed.get("connected") or feed.get("error"):
        raise ValueError("Live Mandi feed is not connected")
    if feed.get("last_success_utc") != receipt.get("retrieved_at_utc"):
        raise ValueError("Backend retrieval receipt differs from saved API receipt")
    if status["adapter"] != "OPEN_METEO_MANDI_READ_ONLY" or status["sourceClasses"] != ["modeled_grid"]:
        raise ValueError("Unexpected active adapter or source class")
    if telemetry["sourceId"] != "OpenMeteo_current_ECMWF_IFS_CAMS_global":
        raise ValueError("Unexpected Mandi source identity")
    if telemetry["pressureReference"] != "grid_surface":
        raise ValueError("Grid surface pressure reference missing")
    if telemetry["units"] != EXPECTED_UNITS:
        raise ValueError("Canonical six-channel unit contract mismatch")
    if set(telemetry["sensors"]) != set(RAW_SENSOR_COLUMNS) or any(
        telemetry["sensors"][channel] is None for channel in RAW_SENSOR_COLUMNS
    ):
        raise ValueError("Incomplete six-channel live snapshot")
    if set(telemetry["forecast6h"]) != set(RAW_SENSOR_COLUMNS):
        raise ValueError("Six-channel forecast output contract mismatch")
    if telemetry["forecastStatus"] != "HYBRID_READY" or telemetry["forecastHistoryRows"] != 25:
        raise ValueError("Expected complete 25-point forecast history")
    observed_at = pd.to_datetime(telemetry["timestamp"], unit="ms", utc=True)
    target_at = pd.Timestamp(telemetry["forecastTimestamp"])
    if target_at.tzinfo is None or target_at.tz_convert("UTC") != observed_at + pd.Timedelta(hours=6):
        raise ValueError("Forecast timestamp is not exactly six hours after observation")
    patterns = telemetry["weatherCategories"]
    scenarios = telemetry["hazardScenarios"]
    if patterns["calibrated"] or patterns["field_validated"] or patterns["probability"] is not None:
        raise ValueError("Pattern outputs were incorrectly promoted to probabilities")
    if scenarios["calibrated"] or scenarios["field_validated"] or scenarios["probability"] is not None or scenarios["public_alerts_enabled"]:
        raise ValueError("Scenario outputs were incorrectly promoted to calibrated alerts")
    if scenarios["status"] != "SYNTHETIC_SCENARIOS_ONLY" or len(scenarios["targets"]) != 3:
        raise ValueError("Expected the three explicitly synthetic hazard scenario outputs")
    if maps["status"] != "UNAVAILABLE" or maps["layers"] or len(maps["nodes"]) != 1:
        raise ValueError("Single point must not be rendered as a fabricated area map")
    return {
        "schema_version": "indra_live_mandi_dashboard_verification_v1",
        "verified_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "evidence": "LIVE_OPEN_METEO_MODELED_GRID_NOT_PHYSICAL_SENSOR_DATA",
        "dashboard_base_url": base_url.rstrip("/"),
        "source_class": telemetry["sourceClass"],
        "source_id": telemetry["sourceId"],
        "provider_grid_receipt": receipt,
        "provider_response_details": raw_receipt_files(source_dir, receipt),
        "observation_time_utc": observed_at.isoformat(),
        "forecast_target_time_utc": target_at.tz_convert("UTC").isoformat(),
        "pressure_reference": telemetry["pressureReference"],
        "canonical_channels_present": RAW_SENSOR_COLUMNS,
        "canonical_units": telemetry["units"],
        "latest_values": telemetry["sensors"],
        "forecast_values": telemetry["forecast6h"],
        "forecast_model_id": telemetry["forecastModel"]["id"],
        "forecast_profile_sha256": telemetry["forecastModel"]["profileSha256"],
        "forecast_status": telemetry["forecastStatus"],
        "history_rows": telemetry["forecastHistoryRows"],
        "history_required": telemetry["forecastHistoryRequired"],
        "pattern_model_id": patterns["model_id"],
        "pattern_status": patterns["status"],
        "matched_patterns": patterns["matched"],
        "pattern_scores_are_calibrated_probabilities": False,
        "scenario_model_id": scenarios["model_id"],
        "scenario_config_sha256": scenarios["config_sha256"],
        "scenario_seed": scenarios["seed"],
        "scenario_targets": [
            {"id": item["id"], "central_fraction": item["scenario_fraction"], "assumption_range": item["assumption_range"]}
            for item in scenarios["targets"]
        ],
        "scenario_calibrated": False,
        "public_alerts_enabled": False,
        "spatial_map_status": maps["status"],
        "spatial_point_count": len(maps["nodes"]),
        "spatial_layers_emitted": list(maps["layers"]),
        "live_api_failure_fallback": "NO DEMO FALLBACK; backend test asserts an empty store remains empty after API failure",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8094")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.url, args.source_dir)
    atomic_json(args.output, report)
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

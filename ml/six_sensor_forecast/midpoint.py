"""Experimental midpoint estimates; coordinates alone do not predict weather."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, RAW_SENSOR_COLUMNS


def geographic_midpoint(
    a: tuple[float, float], b: tuple[float, float]
) -> tuple[float, float]:
    """Shorter great-circle midpoint on a sphere, not an ellipsoidal survey."""
    vectors = []
    for lat, lon in (a, b):
        if not (
            math.isfinite(lat)
            and math.isfinite(lon)
            and -90 <= lat <= 90
            and -180 <= lon <= 180
        ):
            raise ValueError(
                "Coordinates must be finite latitude [-90,90], longitude [-180,180]."
            )
        phi, lam = math.radians(lat), math.radians(lon)
        vectors.append(
            (
                math.cos(phi) * math.cos(lam),
                math.cos(phi) * math.sin(lam),
                math.sin(phi),
            )
        )
    x, y, z = (sum(v[i] for v in vectors) for i in range(3))
    if math.sqrt(x * x + y * y + z * z) < 1e-12:
        raise ValueError("Antipodal endpoints do not have a unique midpoint.")
    lat = math.degrees(math.atan2(z, math.hypot(x, y)))
    lon = (
        0.0
        if math.hypot(x, y) < 1e-12
        else (math.degrees(math.atan2(y, x)) + 180) % 360 - 180
    )
    return lat, lon


def prepare_midpoint(left: dict, right: dict) -> dict:
    """Require same-time, complete endpoint measurements before interpolation."""
    snapshots = []
    for endpoint in (left, right):
        timestamp = datetime.fromisoformat(
            endpoint["timestamp_utc"].replace("Z", "+00:00")
        )
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("Endpoint timestamps must include a timezone.")
        timestamp = timestamp.astimezone(timezone.utc)
        values = endpoint["measurements"]
        if set(values) != set(RAW_SENSOR_COLUMNS):
            raise ValueError(
                "Each endpoint must contain exactly the six measured inputs."
            )
        for key in RAW_SENSOR_COLUMNS:
            value = float(values[key])
            low, high = PHYSICAL_RANGES[key]
            if not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f"Invalid endpoint measurement: {key}")
        snapshots.append(timestamp)
    if snapshots[0] != snapshots[1]:
        raise ValueError(
            "Endpoint observations must have the same timestamp; no time interpolation is performed."
        )
    lat, lon = geographic_midpoint(
        (left["latitude"], left["longitude"]), (right["latitude"], right["longitude"])
    )
    return {
        "status": "EXPERIMENTAL_SPATIAL_ESTIMATE_NOT_VALIDATED",
        "latitude": lat,
        "longitude": lon,
        "timestamp_utc": snapshots[0].isoformat(),
        "estimated_inputs": {
            k: (float(left["measurements"][k]) + float(right["measurements"][k])) / 2
            for k in RAW_SENSOR_COLUMNS
        },
        "input_provenance": "Equal-weight interpolation of two endpoint measurements, not measured midpoint sensors",
        "geometry": "Shorter great-circle spherical midpoint",
        "limitations": [
            "No midpoint ground-truth accuracy has been established.",
            "No elevation, terrain, wind-direction or pollution-transport correction.",
            "Coordinates locate the estimate; they are not learned inputs to the existing model.",
            "Do not use interpolated readings as observed training labels.",
        ],
    }


def forecast_midpoint(left: dict, right: dict, model_dir: Path) -> dict:
    result = prepare_midpoint(left, right)
    import pandas as pd

    from ml.six_sensor_forecast.predict import predict

    frame = pd.DataFrame(
        [
            {
                "timestamp_utc": result["timestamp_utc"],
                "location_id": "experimental_midpoint",
                **result["estimated_inputs"],
            }
        ]
    )
    output = predict(frame, model_dir, "student").iloc[0]
    if output["status"] != "OFFLINE_RESEARCH_ONLY":
        raise ValueError("The forecast model rejected the interpolated inputs.")
    result["forecast_timestamp_utc"] = output["forecast_timestamp_utc"].isoformat()
    result["forecast_6h"] = {
        k: float(output["forecast_" + k]) for k in RAW_SENSOR_COLUMNS
    }
    result["model"] = str(model_dir)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="JSON with left and right endpoint snapshots",
    )
    parser.add_argument("--model", type=Path, default=Path("ml/models/uci_beijing_6h"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text())
    result = forecast_midpoint(payload["left"], payload["right"], args.model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

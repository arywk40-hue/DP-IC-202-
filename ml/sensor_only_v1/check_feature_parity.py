"""Compare the Python and firmware feature builders for the fixed v1 contract."""
from __future__ import annotations

import subprocess
from pathlib import Path

from feature_contract import build_feature_vector

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path("/tmp/sensor_only_v1_feature_cli")

def main() -> None:
    subprocess.run([
        "c++", "-std=c++17", "-Ifirmware/lib/IndraCore/src",
        "tests/model/sensor_only_v1_feature_cli.cpp", "firmware/lib/IndraCore/src/IndraCore.cpp",
        "-o", str(OUTPUT), "-lm",
    ], cwd=ROOT, check=True)
    c_values = [float(value) for value in subprocess.check_output([str(OUTPUT)], text=True).splitlines()]
    py_values = build_feature_vector({
        "temperature_c": 30.0, "relative_humidity_pct": 65.0, "pressure_hpa": 1009.0,
        "wind_speed_mps": 4.0, "pm25_ug_m3": 25.0, "pressure_trend_hpa_per_hour": 1.0,
        "hour": 12, "day_of_year": 236, "latitude_deg": 22.5726, "longitude_deg": 88.3639,
    })
    # Firmware uses single-precision math; the heat-index polynomial needs 1e-4 tolerance.
    if len(c_values) != len(py_values) or any(abs(left - right) > 1e-4 for left, right in zip(c_values, py_values)):
        raise SystemExit(f"feature parity failed: Python={py_values} C={c_values}")
    print("sensor_only_v1 Python/C feature parity: PASS")

if __name__ == "__main__":
    main()

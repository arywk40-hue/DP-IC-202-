"""Canonical six measured inputs and physical validity ranges."""

RAW_SENSOR_COLUMNS = [
    "temperature_c",
    "relative_humidity_pct",
    "pressure_hpa",
    "pm25_ug_m3",
    "pm10_ug_m3",
    "wind_speed_mps",
]

PHYSICAL_RANGES = {
    "temperature_c": (-60.0, 85.0),
    "relative_humidity_pct": (0.0, 100.0),
    "pressure_hpa": (300.0, 1100.0),
    "pm25_ug_m3": (0.0, 5000.0),
    "pm10_ug_m3": (0.0, 5000.0),
    "wind_speed_mps": (0.0, 100.0),
}


def sensor_profile(columns: list[str] | None = None) -> list[str]:
    """Validate a nonempty canonical ordered subset of the funded measurements."""
    selected = list(RAW_SENSOR_COLUMNS if columns is None else columns)
    if not selected or selected != [c for c in RAW_SENSOR_COLUMNS if c in selected]:
        raise ValueError(
            "Sensor profile must be a nonempty canonical ordered subset without duplicates"
        )
    return selected

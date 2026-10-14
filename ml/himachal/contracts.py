"""Strict snapshots using existing unit/QC adapters and explicit provenance."""
from __future__ import annotations

from math import isfinite

from ml.operational.contracts import UNITS, finite, observation, utc
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS

SCHEMA = "indra_himachal_snapshot_v1"
SOURCE_CLASSES = {"physical_indra", "observed_external_station", "modeled_grid", "synthetic_demo"}
PRESSURE_REFERENCES = {"station", "grid_surface", "sea_level", "unknown"}
METADATA = {
    "node_id", "physical_site_id", "registration_id", "latitude", "longitude", "elevation_m",
    "elevation_datum", "sensor_height_m", "wind_height_m", "native_interval_seconds",
    "source_class", "source_id", "source_cell_id", "pressure_reference", "timestamp_utc",
    "valid_time_utc", "available_at_utc", "sensor_model",
    "calibration_ids",
}


def _identity(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise ValueError("Nonempty bounded provenance identity required")
    return value


def snapshot(record: dict) -> dict:
    """Validate one simultaneous snapshot; never infer units, clocks or pressure.

    Missing/rejected channels stay null. Unknown/sea-level pressure is preserved
    in provenance but unavailable to the station/grid tendency feature engine.
    Source class and authentication are not a client-granted voting privilege.
    """
    required = METADATA | {"measurements", "units"}
    if not isinstance(record, dict) or not required <= set(record) or set(record) - required - {"quality_flags"}:
        raise ValueError("Missing/unexpected snapshot fields")
    if record["source_class"] not in SOURCE_CLASSES or record["pressure_reference"] not in PRESSURE_REFERENCES:
        raise ValueError("Unknown source class or pressure reference")
    for key in ("node_id", "physical_site_id", "registration_id", "source_id", "sensor_model"):
        _identity(record[key])
    if record["source_cell_id"] is not None:
        _identity(record["source_cell_id"])
    if record["source_class"] == "modeled_grid" and record["source_cell_id"] is None:
        raise ValueError("Model-grid source requires its actual cell identity")
    cadence = record["native_interval_seconds"]
    if type(cadence) is not int or not 1 <= cadence <= 3600 or 3600 % cadence:
        raise ValueError("Native cadence must divide one hour exactly")
    t, valid, available = [utc(record[k]) for k in ("timestamp_utc", "valid_time_utc", "available_at_utc")]
    if t != valid or available < t or t.value % (cadence * 1_000_000_000):
        raise ValueError("Invalid/off-grid observation, valid time or availability")
    if (not isinstance(record["measurements"], dict) or not isinstance(record["units"], dict)
            or set(record["measurements"]) != set(RAW_SENSOR_COLUMNS) or set(record["units"]) != set(RAW_SENSOR_COLUMNS)):
        raise ValueError("Exactly six named channels/units required")
    if not isinstance(record["calibration_ids"], dict) or set(record["calibration_ids"]) != set(RAW_SENSOR_COLUMNS):
        raise ValueError("Explicit per-channel calibration identities/null required")
    for identity in record["calibration_ids"].values():
        if identity is not None:
            _identity(identity)
    flags = record.get("quality_flags", {})
    if not isinstance(flags, dict) or set(flags) - set(RAW_SENSOR_COLUMNS):
        raise ValueError("Unknown quality channel")
    for value in flags.values():
        if value not in {"valid", "rejected", "missing", "uncertain"}:
            raise ValueError("Unknown provider quality flag")
    lat, lon = finite(record["latitude"]), finite(record["longitude"])
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("Invalid WGS84 coordinates")
    if record["elevation_m"] is not None:
        z = finite(record["elevation_m"])
        if not -500 <= z <= 9000 or record["elevation_datum"] not in {"EGM96", "EGM2008", "surveyed_orthometric"}:
            raise ValueError("Verified elevation datum/range required")
    elif record["elevation_datum"] != "unknown":
        raise ValueError("Missing elevation must have unknown datum")
    for key in ("sensor_height_m", "wind_height_m"):
        if record[key] is not None and not 0 <= finite(record[key]) <= 100:
            raise ValueError("Invalid sensor height")
    values, quality = {}, {}
    for channel in RAW_SENSOR_COLUMNS:
        # Reuse canonical conversion/range/QC logic. The grid adapter applies
        # the same numerical checks but retains grid_surface provenance below;
        # it never publishes a grid value as an observed station measurement.
        reference = record["pressure_reference"]
        adapted = observation(dict(node_id=record["node_id"], timestamp_utc=t.isoformat(),
            latitude=lat, longitude=lon, elevation_m=None, channel=channel,
            value=record["measurements"][channel], unit=record["units"][channel],
            source=record["source_id"], sensor_model=record["sensor_model"],
            sample_interval_seconds=cadence, pressure_reference="station" if reference == "grid_surface" else reference,
            quality_flag=flags.get(channel, "valid")), received_at=available.isoformat())
        values[channel], quality[channel] = adapted["value"], adapted["quality_flag"]
    result = {k: record[k] for k in METADATA}
    result.update(schema_version=SCHEMA, timestamp_utc=t.isoformat(), valid_time_utc=valid.isoformat(),
                  available_at_utc=available.isoformat(), latitude=lat, longitude=lon,
                  measurements=values, units=UNITS.copy(), quality_flags=quality)
    result["raw_measurements"] = {c: repr(v) if isinstance(v, float) and not isfinite(v) else v
                                  for c, v in record["measurements"].items()}
    result["raw_units"] = record["units"].copy()
    assert all(v is None or isfinite(v) for v in values.values())
    return result

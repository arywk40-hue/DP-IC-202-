"""Deduplicated provider ancestry, always outside physical warning quorum."""
import hashlib
import math

from ml.operational.contracts import canonical_bytes, utc
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS


def virtual_nodes(records):
    required = {"provider", "upstream_provider", "upstream_station_or_cell_id", "source_class", "variables",
                "native_cadence_seconds", "native_resolution", "valid_time_utc", "available_at_utc", "rights_status",
                "units", "elevation_m", "elevation_datum", "pressure_reference", "source_version",
                "provider_license", "measurement_uncertainty", "source_ancestry"}
    seen = {}
    for record in records:
        if not required <= set(record) or record["source_class"] not in {"observed_external_station", "modeled_grid"}:
            raise ValueError("Explicit virtual source ancestry/cadence/time/rights required")
        if not record["upstream_station_or_cell_id"] or not record["upstream_provider"]:
            raise ValueError("Unknown upstream identity cannot manufacture a node")
        if (type(record["native_cadence_seconds"]) is not int or record["native_cadence_seconds"] < 1
                or not isinstance(record["variables"], list) or len(set(record["variables"])) != len(record["variables"])
                or set(record["variables"]) - set(RAW_SENSOR_COLUMNS) or set(record["units"]) != set(record["variables"])
                or utc(record["available_at_utc"]) < utc(record["valid_time_utc"])):
            raise ValueError("Native cadence, named channel units and actual availability required")
        if record["elevation_m"] is not None and (not math.isfinite(record["elevation_m"]) or record["elevation_datum"] == "unknown"):
            raise ValueError("Unknown source elevation/datum must remain explicit")
        record = {**record, "valid_time_utc": utc(record["valid_time_utc"]).isoformat(),
                  "available_at_utc": utc(record["available_at_utc"]).isoformat()}
        key = (record["upstream_provider"], record["upstream_station_or_cell_id"], record["valid_time_utc"])
        identity = hashlib.sha256(canonical_bytes(key)).hexdigest()
        facts = {k: v for k, v in record.items() if k != "provider"}
        if key in seen:
            if seen[key]["facts"] != facts:
                raise ValueError("Conflicting upstream duplicates; never fuse purported observations")
            seen[key]["providers"].append(record["provider"])
            continue
        seen[key] = dict(virtual_node_id="virtual_"+identity[:24], facts=facts,
                         providers=[record["provider"]], physical_vote_eligible=False,
                         measured_station_coverage=record["source_class"]=="observed_external_station")
    return list(seen.values())

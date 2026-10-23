"""Causal, gap-aware feature packets from explicit native snapshots."""
from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path

from ml.himachal.contracts import METADATA, snapshot
from ml.himachal.meteorology import estimate, heat_index, humidity
from ml.operational.contracts import UNITS, canonical_bytes, utc
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS

CONFIG_PATH = Path(__file__).resolve().parents[2] / "ml/configs/himachal_features_v1.json"


def load_config():
    return json.loads(CONFIG_PATH.read_text())


def build_packet(records: list[dict], issue_time_utc: str, *, noise_sigma=None) -> dict:
    """One registration/site/native cadence per packet; no resampling or ffill.

    History is keyed by observation time and usable only after actual available_at.
    Late arrivals may inform later issues; they never rewrite earlier packets.
    noise_sigma, when supplied, must come from identified calibration evidence
    available by issue time and applies separately to both PM channels.
    """
    config = load_config()
    if not records or len(records) > config["max_native_records"]:
        raise ValueError("Bounded nonempty native observations required")
    rows = [snapshot(r) for r in records]
    issue = utc(issue_time_utc)
    keys = ("node_id", "physical_site_id", "registration_id", "latitude", "longitude", "elevation_m",
            "elevation_datum", "sensor_height_m", "wind_height_m", "native_interval_seconds",
            "source_class", "source_id", "source_cell_id", "pressure_reference", "sensor_model")
    if any(len({r[k] for r in rows}) != 1 for k in keys):
        raise ValueError("One fixed site/registration/source/reference required; relocation starts new history")
    if any(r["calibration_ids"] != rows[0]["calibration_ids"] for r in rows):
        raise ValueError("Calibration change requires a new feature-history segment")
    times = [utc(r["timestamp_utc"]) for r in rows]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("Duplicate or reordered observations")
    cadence = rows[0]["native_interval_seconds"]
    if issue.value % (cadence * 1_000_000_000):
        raise ValueError("Issue time off native grid")
    used = [r for r, t in zip(rows, times) if t <= issue and utc(r["available_at_utc"]) <= issue]
    lookup = {utc(r["timestamp_utc"]): r for r in used}
    import pandas as pd

    def at(seconds):
        return lookup.get(issue - pd.Timedelta(seconds=seconds))

    def window(channel, seconds, offset=0, include_current=True):
        if seconds % cadence or offset % cadence:
            return None
        ticks = range(offset, offset+seconds+1, cadence) if include_current else range(offset, offset+seconds, cadence)
        values = []
        for tick in ticks:
            row = at(tick)
            value = None if row is None else row["measurements"][channel]
            if value is None:
                return None
            values.append(value)
        return values

    features = {}

    def add(name, value, unit, status=None, **extra):
        features[name] = {"evidence_id": f"himachal_features_v1:{name}",
                          **estimate(value, unit, status or ("AVAILABLE" if value is not None else "MISSING_HISTORY_OR_CHANNEL"), **extra)}

    now = at(0)
    current = {c: None if now is None else now["measurements"][c] for c in RAW_SENSOR_COLUMNS}
    for channel, value in current.items():
        add(channel, value, UNITS[channel])
        delta_unit = "percentage_point" if channel == "relative_humidity_pct" else UNITS[channel]
        for minutes in (15, 60, 360):
            values = window(channel, minutes * 60)
            delta = None if values is None else values[0] - values[-1]
            suffix = {15: "15min", 60: "1h", 360: "6h"}[minutes]
            add(f"{channel}_delta_{suffix}", delta, delta_unit, window_seconds=minutes*60)
            add(f"{channel}_rate_per_h_{suffix}", None if delta is None else delta*60/minutes,
                delta_unit+"/h", window_seconds=minutes*60)
        values = window(channel, 21600)
        add(f"{channel}_mean_6h", None if values is None else statistics.mean(values), UNITS[channel])
        add(f"{channel}_std_6h", None if values is None else statistics.pstdev(values), UNITS[channel])
    for name, result in humidity(current["temperature_c"], current["relative_humidity_pct"]).items():
        add(name, result.pop("value"), result.pop("unit"), **result)
    predrop = window("pressure_hpa", 21600, offset=900)
    add("pressure_predrop_6h_ending_15min_ago", None if predrop is None else predrop[0]-predrop[-1],
        "hPa", window_seconds=21600, end_offset_seconds=900)
    result = heat_index(current["temperature_c"], current["relative_humidity_pct"])
    add("heat_index_nws_c", result.pop("value"), result.pop("unit"), **result)
    numerator, denominator = current["pm25_ug_m3"], current["pm10_ug_m3"]
    ratio = numerator / denominator if numerator is not None and denominator is not None and denominator > 0 else None
    add("pm25_pm10_ratio", ratio, "ratio", "ZERO_OR_MISSING_PM10" if ratio is None else "AVAILABLE",
        quality_note="PM25_EXCEEDS_PM10_REVIEW" if ratio is not None and ratio > 1 else None)

    noise = {}
    calibration_id = None
    if noise_sigma is not None:
        if set(noise_sigma) != {"calibration_id", "available_at_utc", "pm25_ug_m3", "pm10_ug_m3"}:
            raise ValueError("Noise needs both PM sigmas and calibration identity/availability")
        calibration_id = noise_sigma["calibration_id"]
        if not isinstance(calibration_id, str) or not calibration_id.strip() or utc(noise_sigma["available_at_utc"]) > issue:
            raise ValueError("Calibration must be identified and already available")
        for c in ("pm25_ug_m3", "pm10_ug_m3"):
            from ml.operational.contracts import finite
            noise[c] = finite(noise_sigma[c])
            if noise[c] < 0:
                raise ValueError("Invalid calibration noise sigma")

    def washout(native):
        settings = config["hourly_washout"]
        complete = True
        matches = []
        detail = {}
        for i, c in enumerate(("pm25_ug_m3", "pm10_ug_m3")):
            if native:
                values = window(c, 3600, offset=900+cadence) if cadence <= 900 else None
                # Exactly preceding hour [t-75min,t-15min); exclude the
                # t-15min endpoint and include t-75min. No invented samples.
                if values is not None:
                    values = values[:-1]
            elif cadence == 3600:
                values = window(c, 7200, offset=3600)
            else:
                # Hourly means of actual complete native windows, labelled at
                # their ends. All native samples must already be available.
                blocks = [window(c, 3600, offset=h*3600+cadence, include_current=False) for h in (1, 2, 3)]
                values = None if any(b is None for b in blocks) else [statistics.mean(b) for b in blocks]
            baseline = None if values is None else statistics.median(values)
            decline = None if baseline is None or current[c] is None else baseline-current[c]
            minimum = max(settings["minimum_declines_ug_m3"][i], settings["relative_decline"]*(baseline or 0),
                          settings["calibrated_noise_sigma_multiplier"]*noise.get(c, 0))
            available = baseline is not None and baseline >= settings["minimum_baselines_ug_m3"][i] and decline is not None
            complete &= available
            matches.append(available and decline >= minimum)
            detail[c] = dict(baseline=baseline, decline=decline, required_decline=minimum,
                             available=available, unit="ug/m3")
        add("washout_15min_native" if native else "washout_hourly", all(matches) if complete else None,
            "boolean", "AVAILABLE_PROXY_NOT_PRECIPITATION" if complete else "UNAVAILABLE_BASELINE_OR_CADENCE",
            profile=config["native_washout"]["profile"] if native else "three_preceding_hourly_medians_v1",
            calibration_id=calibration_id, detail=detail)

    washout(False)
    washout(True)
    rh = features["relative_humidity_pct_delta_1h"]["value"]
    add("sharp_rh_change_1h", None if rh is None else abs(rh) >= config["sharp_rh_change_1h_pp"], "boolean")
    change = features["wind_speed_mps_delta_15min"]["value"]
    wind_calibrated = rows[0]["calibration_ids"]["wind_speed_mps"] is not None
    add("wind_increase_15min", None if change is None or not wind_calibrated else change >= config["wind_increase_15min_mps"]
        and current["wind_speed_mps"] >= config["wind_current_minimum_mps"], "boolean",
        "UNVERIFIED_WIND_CALIBRATION" if not wind_calibrated else None)
    hourly_change = features["wind_speed_mps_delta_1h"]["value"]
    add("wind_increase_1h_companion", None if hourly_change is None or not wind_calibrated else hourly_change >= config["wind_increase_15min_mps"]
        and current["wind_speed_mps"] >= config["wind_current_minimum_mps"], "boolean",
        "UNVERIFIED_WIND_CALIBRATION" if not wind_calibrated else None)
    add("calendar_jjas_proxy", issue.tz_convert("Asia/Kolkata").month in (6, 7, 8, 9), "boolean", "CONTEXT_NOT_EVENT_EVIDENCE")
    availability = {}
    for name, seconds in (("event_hourly_seven_snapshots", 21600), ("teacher_24h", 86400)):
        availability[name] = all(window(c, seconds) is not None for c in RAW_SENSOR_COLUMNS)
    # Metadata describes the fixed site, not any future sensor reading.
    metadata = {k: rows[0][k] for k in METADATA if k not in {"timestamp_utc", "valid_time_utc", "available_at_utc"}}
    provenance = hashlib.sha256(canonical_bytes(used)).hexdigest()
    return dict(schema_version=config["schema_version"], issue_time_utc=issue.isoformat(),
                metadata=metadata, features=features, history_availability=availability,
                observation_time_utc=None if now is None else now["timestamp_utc"],
                input_provenance_sha256=provenance, feature_config_sha256=hashlib.sha256(canonical_bytes(config)).hexdigest(),
                feature_role="CAUSAL_DERIVED_INPUTS_NOT_INDEPENDENT_LABELS", training_label_admissible=False)

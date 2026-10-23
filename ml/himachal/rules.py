"""Explicit current-condition rule baselines; never observed event labels."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from ml.operational.contracts import canonical_bytes, utc

CONFIG = Path(__file__).resolve().parents[2] / "ml/configs/himachal_rules_v1.json"
TARGETS = ("rain", "snowstorm", "cloudburst_risk")
OPERATORS = {">=": lambda x, y: x >= y, "<=": lambda x, y: x <= y,
             ">": lambda x, y: x > y, "==": lambda x, y: x == y}


def evaluate(packet: dict, *, profile="native_15min", terrain=None) -> dict:
    """No learned likelihood, event confirmation, lead time or dispatch here.

    Corroboration/human confirmation are later policy stages, never inferred from
    a high local score. A non-match does not establish absence of weather.
    """
    config = json.loads(CONFIG.read_text())
    if packet.get("schema_version") != config["feature_version"] or profile not in {"native_15min", "hourly_companion"}:
        raise ValueError("Unknown rule/feature profile")
    if packet.get("training_label_admissible") is not False:
        raise ValueError("Feature packets must not claim independent label status")
    features = dict(packet["features"])
    for name, feature in features.items():
        v = feature["value"]
        if v is not None and (not isinstance(v, (int, float, bool)) or not math.isfinite(v)):
            raise ValueError("Finite numerical/boolean features or null required")
        if feature.get("evidence_id") != "himachal_features_v1:" + name:
            raise ValueError("Feature evidence identity mismatch")
    meta = packet["metadata"]
    trusted_source = meta["source_class"] in {"physical_indra", "observed_external_station", "synthetic_demo"}
    compatible = trusted_source and meta["pressure_reference"] == "station"
    terrain_value, terrain_id = None, None
    if terrain is not None:
        if (set(terrain) != {"reviewed", "exposed", "source_id", "available_at_utc"}
                or terrain["reviewed"] is not True or type(terrain["exposed"]) is not bool
                or not isinstance(terrain["source_id"], str) or not terrain["source_id"].strip()
                or utc(terrain["available_at_utc"]) > utc(packet["issue_time_utc"])):
            raise ValueError("Terrain prior requires reviewed, identified, issue-time evidence")
        terrain_value, terrain_id = terrain["exposed"], terrain["source_id"]
    features["reviewed_terrain_exposure"] = dict(value=terrain_value, unit="boolean",
        status="REVIEWED_CONTEXT" if terrain_value is not None else "MISSING_REVIEWED_TERRAIN",
        evidence_id="himachal_context_v1:reviewed_terrain_exposure", source_id=terrain_id)

    def condition(name, op, threshold, weight=1., dynamic=True):
        f = features.get(name, dict(value=None, unit="unknown", evidence_id="missing:"+name, status="MISSING_FEATURE"))
        v = f["value"]
        available = v is not None and compatible
        matched = bool(OPERATORS[op](v, threshold)) if available else None
        return dict(evidence_id=f["evidence_id"], feature=name, value=v, unit=f["unit"],
                    operator=op, threshold=threshold, matched=matched, available=available,
                    feature_status=f["status"], weight=weight, dynamic=dynamic)

    def conjunction(items):
        # Conservative complete conjunction; even known false + unknown remains
        # explicitly unknown rather than claiming a complete negative assessment.
        return None if any(x["matched"] is None for x in items) else all(x["matched"] for x in items)

    rain, snow, storm = config["rain"], config["snowstorm"], config["rainstorm_sequence"]
    rain_evidence = [condition("relative_humidity_pct", ">=", rain["rh_min_pct"]),
                     condition("pressure_hpa_delta_6h", "<=", rain["pressure_delta_6h_max_hpa"]),
                     condition("temperature_c", ">", rain["temperature_min_exclusive_c"]),
                     condition(rain["washout_feature"], "==", True)]
    snow_evidence = [condition("temperature_c", "<=", snow["temperature_max_c"]),
                     condition("relative_humidity_pct", ">=", snow["rh_min_pct"]),
                     condition("wind_speed_mps", ">=", snow["wind_min_mps"]),
                     condition("pressure_hpa_delta_6h", "<=", snow["pressure_delta_6h_max_hpa"]),
                     condition(snow["washout_feature"], "==", True)]
    storm_evidence = [condition("pressure_predrop_6h_ending_15min_ago", "<=", storm["pre_drop_max_hpa"]),
                      condition("pressure_hpa_delta_15min", ">=", storm["subsequent_pressure_rebound_min_hpa"]),
                      condition("temperature_c_delta_15min", "<=", storm["subsequent_temperature_delta_max_c"]),
                      condition("temperature_c", ">", storm["temperature_min_exclusive_c"]),
                      condition("wind_speed_mps", ">=", storm["wind_min_mps"]),
                      condition(storm["washout_feature"], "==", True)]
    cloud = config["cloudburst_native" if profile == "native_15min" else "cloudburst_hourly"]
    cloud_evidence = [condition(x["feature"], x["operator"], x["threshold"], x["weight"], x["dynamic"]) for x in cloud["criteria"]]

    def output(name, evidence, match, rule_profile, weighted=False):
        available = round(sum(e["weight"] for e in evidence if e["available"]), 12)
        total = round(sum(e["weight"] for e in evidence), 12)
        coverage = available / total
        observed = round(sum(e["weight"] for e in evidence if e["matched"] is True), 12)
        score = observed if weighted and available else float(match) if match is not None else None
        dynamic_matches = sum(e["dynamic"] and e["matched"] is True for e in evidence)
        dynamic_available = sum(e["dynamic"] and e["available"] for e in evidence)
        abstain = match is None if not weighted else not compatible or dynamic_available < 3 or coverage < config["minimum_warning_available_weight"]
        local_candidate = (not abstain and score is not None and score >= config["warning_candidate_threshold"]
                           and dynamic_matches >= config["minimum_warning_dynamic_matches"])
        if abstain:
            level = "unknown"
        elif local_candidate:
            level = "local_warning_candidate"
        elif score is not None and score >= config["watch_threshold"]:
            level = "watch"
        else:
            level = "not_matched"
        return dict(target=name, display_name="Snowstorm risk" if name == "snowstorm" else "Cloudburst risk" if name == "cloudburst_risk" else "Rain condition risk",
            level=level, score=score, probability=None, lead_time_h=None, risk_only=True, abstain=abstain,
            confidence_kind="UNCALIBRATED_RULE_MATCH", task="current_condition_heuristic",
            profile=rule_profile, version=config["schema_version"], feature_version=packet["schema_version"],
            feature_availability={e["feature"]: e["available"] for e in evidence}, available_weight=available,
            coverage=coverage, dynamic_matches=dynamic_matches,
            score_interpretation="OBSERVED_WEIGHT_SUM_NOT_RENORMALIZED" if weighted else "COMPLETE_CONJUNCTION_MATCH_NOT_PROBABILITY",
            triggered_evidence=[e for e in evidence if e["matched"] is True], evidence=evidence,
            assessment_state="LOCAL_ONLY" if compatible else "SOURCE_REFERENCE_UNSUPPORTED",
            warning_candidate=False, corroboration="NOT_ASSESSED", human_confirmation_required=True,
            dispatch_state="DISABLED", training_label_admissible=False,
            non_match_means="RULE_NOT_MATCHED_OR_UNAVAILABLE_NOT_PROOF_OF_SAFETY")

    outputs = {
        "rain": output("rain", rain_evidence, conjunction(rain_evidence), "rain_hourly_washout_condition_v1"),
        "snowstorm": output("snowstorm", snow_evidence, conjunction(snow_evidence), "snowstorm_hourly_washout_risk_v1"),
        "cloudburst_risk": output("cloudburst_risk", cloud_evidence, None, cloud["profile"], weighted=True),
    }
    return dict(schema_version=config["schema_version"], issue_time_utc=packet["issue_time_utc"],
                feature_input_sha256=hashlib.sha256(canonical_bytes(packet)).hexdigest(),
                rule_config_sha256=hashlib.sha256(canonical_bytes(config)).hexdigest(),
                source_class=meta["source_class"], pressure_reference=meta["pressure_reference"],
                synthetic_demo=meta["source_class"] == "synthetic_demo", outputs=outputs,
                rainstorm_sequence=dict(matched=conjunction(storm_evidence), evidence=storm_evidence,
                    role=storm["role"], profile="disjoint_predrop_6h_then_rebound_15min_v1", risk_only=True),
                empirical_validation="NOT_EVALUATED", training_labels_allowed=False,
                public_notifications_enabled=False)

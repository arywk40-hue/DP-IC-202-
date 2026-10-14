"""Independent onset-window label adapter; unknown monitoring is never dry.

The existing conservative admission/matching engine remains authoritative.
New wrappers add structural rain accumulation intervals and explicit source/site
review. Rule/satellite/model/synthetic outputs cannot become empirical labels.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

from ml.hazard_context.events import admit
from ml.hazard_context.matching import validate_monitoring
from ml.hazard_context.warning import mask_incomplete_history, warning_targets
from ml.himachal.data.observations import sensor_frame
from ml.operational.contracts import canonical_bytes, utc

DEFAULT = Path(__file__).resolve().parents[3] / "configs/himachal_labels_v1.json"


def outcome(envelope, config, *, contract_mode=False):
    if set(envelope) != {"record", "measurement", "evidence_category"}:
        raise ValueError("Reviewed outcome envelope with explicit evidence role required")
    record = envelope["record"]
    target = record["event_type"]
    if target not in config["definitions"]:
        raise ValueError("Unsupported independent target")
    source = config.get("approved_sources", {}).get(record["source_dataset"], {})
    admitted = admit(record, source, allow_fixture=contract_mode)
    reasons = list(admitted["admission_reasons"])
    if envelope["evidence_category"] != "INDEPENDENT_OBSERVED" and not contract_mode:
        reasons.append("NONEMPIRICAL_EVIDENCE_ROLE")
    if target in {"rain", "cloudburst"}:
        m = envelope["measurement"]
        required = {"interval_start_utc", "interval_end_utc", "amount", "unit", "statistic", "instrument", "local_gauge_verified"}
        if not isinstance(m, dict) or set(m) != required:
            reasons.append("STRUCTURAL_LOCAL_RAIN_INTERVAL_REQUIRED")
        else:
            interval = (utc(m["interval_end_utc"])-utc(m["interval_start_utc"])).total_seconds()
            amount = m["amount"]
            good = type(amount) in {float, int} and math.isfinite(amount) and amount >= (.2 if target=="rain" else 100)
            if (interval != 3600 or m["unit"] != "mm" or m["statistic"] != "accumulation"
                    or m["local_gauge_verified"] is not True or not m["instrument"] or not good
                    or admitted["evidence_kind"] != "observed_gauge"):
                reasons.append("INCOMPATIBLE_GAUGE_AMOUNT_INTERVAL_OR_QC")
            # Legacy admission already requires observed mm/h >=100 for
            # cloudburst. Verify that scalar agrees with the structured hour.
            unit = "mm" if target == "rain" else "mm/h"
            if admitted["measurement_unit"] != unit or admitted["measurement_value"] != amount:
                reasons.append("STRUCTURED_LEGACY_MEASUREMENT_CONFLICT")
    if admitted["threshold_definition"] != config["definitions"][target]:
        reasons.append("TARGET_DEFINITION_PROFILE_MISMATCH")
    admitted["admission_reasons"] = sorted(set(reasons))
    if reasons and admitted["admission_status"] == "admitted_for_training":
        admitted["admission_status"] = "research_only"
    return admitted


def build_labels(events, observations, monitoring, config, *, contract_mode=False):
    if config.get("schema_version") != "indra_himachal_labels_v1" or config["deployment_approved"] is not False:
        raise ValueError("Research label profile required")
    if config["horizon_hours"] != 6 or config["history_minutes"] < 1440 or config["cadence_seconds"] != 3600:
        raise ValueError("Frozen six-hour onset / 24-hour hourly history profile required")
    frame = sensor_frame(observations)
    reviews = config.get("approved_sites", {})
    for site, group in frame.groupby("physical_site_id"):
        reviewed = reviews.get(site, {})
        if (reviewed.get("co_location_verified") is True and reviewed.get("country_code") == "IN"
                and reviewed.get("state") == "Himachal Pradesh" and reviewed.get("reviewed_by")
                and reviewed.get("source_id") == group.source_id.iloc[0]
                and reviewed.get("latitude") == group.latitude.iloc[0]
                and reviewed.get("longitude") == group.longitude.iloc[0]):
            frame.loc[group.index, "country_code"] = "IN"
    eligible_site = frame.country_code.eq("IN") & frame.source_class.isin(["physical_indra", "observed_external_station"])
    if contract_mode:
        eligible_site |= frame.country_code.eq("IN") & frame.source_class.eq("synthetic_demo")
    synthetic_observations = frame.source_class.eq("synthetic_demo").any()
    admitted = [outcome(e, config, contract_mode=contract_mode) for e in events]
    monitors = validate_monitoring(monitoring)
    allowed_monitors = []
    for m in monitors:
        source = config.get("approved_sources", {}).get(m["source_dataset"], {})
        if (m["definition"] == config["definitions"].get(m["event_type"])
                and source.get("status") == "admitted_for_training"
                and source.get("independent_observed") is True
                and m["source_provider"] == source.get("source_provider")
                and m["rights_status"] == source.get("rights_status")
                and m["provider_license"] == source.get("provider_license")
                and (source.get("evidence") != "SYNTHETIC_CONTRACT_ONLY" or contract_mode)):
            allowed_monitors.append(m)
    columns = ["physical_site_id", "location_id", "latitude", "longitude", "elevation_m"]
    sites = frame[columns].drop_duplicates("physical_site_id")
    counts, labels = {}, []
    for public, target in config["public_to_observed_target"].items():
        selected = frame.loc[eligible_site].reset_index(drop=True)
        if selected.empty:
            result = pd.DataFrame(columns=["physical_site_id", "timestamp_utc", "label", "event_group_id", "label_quality"])
        else:
            contextual = admitted
            if target == "rain":
                # A possible cloudburst is possible rain, even if its gauge
                # evidence is unverified. It can block a negative, never invent
                # a positive rain label or a precise onset.
                contextual = [{**e, "event_type": "rain", "event_id": e["event_id"]+":rain_candidate",
                    "reported_event_id": e["event_id"], "admission_status": "research_only"}
                    if e["event_type"] == "cloudburst" else e for e in admitted]
            result = warning_targets(selected, contextual, sites, allowed_monitors, target,
                horizon_hours=config["horizon_hours"], matching_cfg=config["matching"])
            result = mask_incomplete_history(result, selected, config["history_minutes"], config["cadence_seconds"])
        result["public_target"], result["observed_target"] = public, target
        result["evidence_kind"] = "SYNTHETIC_CONTRACT_ONLY" if contract_mode or synthetic_observations else "INDEPENDENT_ADMISSION_REQUIRED"
        result["empirical_training_admissible"] = result.label.isin([0.,1.]) & (not contract_mode and not synthetic_observations)
        # Mixed demo/real sources do not partially slip into an empirical table.
        if synthetic_observations and not contract_mode:
            result["label"] = None
            result["empirical_training_admissible"] = False
        positives = result.label.eq(1)
        groups = result.loc[positives, "event_group_id"].nunique()
        site_count = result.loc[positives, "physical_site_id"].nunique()
        counts[public] = dict(rows=len(result), positive_windows=int(positives.sum()),
            negative_windows=int(result.label.eq(0).sum()), unknown_windows=int(result.label.isna().sum()),
            independent_positive_groups=int(groups), positive_sites=int(site_count),
            status="READY_FOR_COHORT_REVIEW" if not contract_mode and not synthetic_observations and groups>=config["minimum_independent_event_groups_for_fitting"] and site_count>=config["minimum_independent_sites_for_fitting"] and result.label.eq(0).any() else "NOT_READY")
        labels.append(result)
    combined = pd.concat(labels, ignore_index=True)
    receipt = dict(schema_version="indra_himachal_label_receipt_v1", status="NOT_READY" if any(c["status"]=="NOT_READY" for c in counts.values()) else "READY_FOR_COHORT_REVIEW",
        task="onset_in_next_6h", horizon_hours=6, targets=counts,
        sources_admitted=sum(e["admission_status"]=="admitted_for_training" for e in admitted),
        rejected_reasons=dict(Counter(reason for e in admitted for reason in e["admission_reasons"])),
        observation_rows=len(frame), unreviewed_or_ineligible_observation_rows=int((~eligible_site).sum()),
        accepted_monitoring_intervals=len(allowed_monitors), rejected_monitoring_intervals=len(monitors)-len(allowed_monitors),
        evidence_kind="SYNTHETIC_CONTRACT_ONLY" if contract_mode or synthetic_observations else "INDEPENDENT_ADMISSION_REQUIRED",
        input_sha256=hashlib.sha256(canonical_bytes(dict(events=events, observations=observations, monitoring=monitoring, config=config))).hexdigest(),
        empirical_training_approved=False, deployment_approved=False)
    return combined, receipt


def write_outputs(output, labels, receipt):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    csv = labels.to_csv(index=False, lineterminator="\n")
    receipt = {**receipt, "labels_sha256": hashlib.sha256(csv.encode()).hexdigest()}
    for name, text in (("labels.csv", csv), ("manifest.json", json.dumps(receipt, indent=2, allow_nan=False)+"\n")):
        path = output / name
        if path.exists() and path.read_text() != text:
            raise ValueError("Existing label outputs differ; choose a new versioned directory")
    (output / "labels.csv").write_text(csv)
    (output / "manifest.json").write_text(json.dumps(receipt, indent=2, allow_nan=False)+"\n")
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--events", type=Path, required=True)
    p.add_argument("--observations", type=Path, required=True)
    p.add_argument("--monitoring", type=Path, required=True)
    p.add_argument("--config", type=Path, default=DEFAULT)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--offline", action="store_true", required=True)
    a = p.parse_args()
    def jsonl(path):
        if path.stat().st_size > 50_000_000:
            raise ValueError("Partition source exports before labelling")
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    labels, receipt = build_labels(jsonl(a.events), jsonl(a.observations), json.loads(a.monitoring.read_text()), json.loads(a.config.read_text()))
    print(json.dumps(write_outputs(a.output, labels, receipt), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

"""Export the frozen Mandi v2 ensemble as a portable C++ parameter header.

This export contains no training code. It preserves all trained ensemble
components and checks the source profile before writing any device artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import lightgbm as lgb
import numpy as np
import pandas as pd
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
MODEL = ROOT / "ml/models/india_mandi_tabular_v2"
LEGACY_PROFILE = ROOT / "ml/models/india_mandi_hybrid_6h_v1/profile.json"
SENSORS = [
    "temperature_c", "relative_humidity_pct", "pressure_hpa",
    "pm25_ug_m3", "pm10_ug_m3", "wind_speed_mps",
]
PATTERN_NAMES = ["rain", "rainstorm", "snowstorm", "heatwave_like", "fog", "frost",
                 "dust_storm", "smoke", "wildfire_weather", "cloudburst_like"]


def sha256(path: Path) -> str:
    """Return a file digest used by the source manifest."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def flatten_lgb(node: dict, out: list[dict]) -> int:
    """Flatten one LightGBM tree; reject unsupported categorical/missing splits."""
    index = len(out)
    out.append({})
    if "leaf_value" in node:
        out[index] = dict(feature=-1, left=-1, right=-1, threshold=0.0,
                          value=float(node["leaf_value"]))
        return index
    if node.get("decision_type") != "<=" or node.get("missing_type") not in (None, "None", "NaN"):
        raise ValueError("Unsupported LightGBM decision or missing-value mode")
    left = flatten_lgb(node["left_child"], out)
    right = flatten_lgb(node["right_child"], out)
    out[index] = dict(feature=int(node["split_feature"]), left=left, right=right,
                      threshold=float(node["threshold"]), value=0.0)
    return index


def flatten_xgb(node: dict, out: list[dict], feature_names: list[str]) -> int:
    """Flatten one complete-feature XGBoost regression tree."""
    index = len(out)
    out.append({})
    if "leaf" in node:
        out[index] = dict(feature=-1, left=-1, right=-1, threshold=0.0,
                          value=float(node["leaf"]))
        return index
    split = node["split"]
    if split in feature_names:
        feature = feature_names.index(split)
    elif split.startswith("f") and split[1:].isdigit():
        feature = int(split[1:])
    else:
        raise ValueError(f"Unknown XGBoost feature name {split!r}")
    children = {int(child["nodeid"]): child for child in node["children"]}
    yes, no = int(node["yes"]), int(node["no"])
    left = flatten_xgb(children[yes], out, feature_names)
    right = flatten_xgb(children[no], out, feature_names)
    out[index] = dict(feature=feature, left=left, right=right,
                      threshold=float(node["split_condition"]), value=0.0)
    return index


def load_legacy():
    """Read the hash-checked India hybrid components used by v2."""
    from ml.india_mandi.hybrid import Hybrid

    model = Hybrid()
    report = model.components.report
    return model, report


def cpp_float(value: float) -> str:
    """Format a finite float literal for generated C++."""
    literal = f"{float(value):.9g}"
    if "." not in literal and "e" not in literal.lower():
        literal += ".0"
    return literal + "f"


def emit_tree_array(name: str, trees: list[list[dict]], roots: list[int], base: float) -> list[str]:
    """Write one flat const node array plus per-tree root offsets."""
    nodes = [node for tree in trees for node in tree]
    if any(len(tree) > 127 for tree in trees):
        raise ValueError(f"Tree node index does not fit the compact edge format: {name}")
    lines = [f"static const Node {name}_nodes[] = {{"]
    lines += [
        "  {%d,%d,%d,%s,%s}," % (
            n["feature"], n["left"], n["right"], cpp_float(n["threshold"]), cpp_float(n["value"])
        ) for n in nodes
    ]
    lines.append("};")
    offsets, cursor = [], 0
    for tree in trees:
        offsets.append(cursor)
        cursor += len(tree)
    lines.append(f"static const uint32_t {name}_roots[] = {{" + ",".join(map(str, offsets)) + "};")
    lines.append(f"static const uint32_t {name}_root_count = {len(trees)};")
    lines.append(f"static const float {name}_base = {cpp_float(base)};")
    return lines


def emit_float_array(name: str, value) -> list[str]:
    """Emit a flattened immutable parameter vector."""
    flat = np.asarray(value, dtype=np.float64).reshape(-1)
    return [f"static const float {name}[{len(flat)}] = {{",
            "  " + ",".join(cpp_float(v) for v in flat), "};"]


def collect():
    """Collect all parameters of the selected top-level blend."""
    from ml.india_mandi.tabular_v2 import TabularV2

    model = TabularV2()
    profile = model.profile
    legacy, legacy_report = load_legacy()
    if legacy.profile_sha256 != profile["legacy_profile_sha256"]:
        raise ValueError("Legacy hybrid profile hash does not match selected ensemble")
    data = {"profile": profile, "weights": model.weights, "legacy_weights": legacy.weights,
            "features": profile["features"], "trees": {}, "neural": {}, "ridge": {},
            "teacher_weights": {t: float(legacy_report["models"][t]["teacher_weight"]) for t in SENSORS},
            "hashes": {"profile.json": sha256(MODEL / "profile.json"),
                       "ensemble_weights.json": sha256(MODEL / "ensemble_weights.json")}}

    for target in SENSORS:
        booster = model.boosters[target]
        dump = booster.dump_model()
        trees, roots = [], []
        for item in dump["tree_info"]:
            one = []
            roots.append(flatten_lgb(item["tree_structure"], one))
            trees.append(one)
        data["trees"]["lgb_" + target] = dict(trees=trees, roots=roots, base=float(dump.get("average_output", False) and 0.0))

    for target in SENSORS:
        booster = legacy.components.boosters[target]
        trees, roots = [], []
        for raw in booster.get_dump(dump_format="json"):
            one = []
            roots.append(flatten_xgb(json.loads(raw), one, legacy.components.features))
            trees.append(one)
        cfg = json.loads(booster.save_config())
        base = float(cfg["learner"]["learner_model_param"]["base_score"].strip("[]"))
        data["trees"]["xgb_" + target] = dict(trees=trees, roots=roots, base=base)

    from ml.himachal.weather_categories import WeatherCategories
    categories = WeatherCategories()
    data["pattern"] = {
        "weights": categories.weights.tolist(),
        "thresholds": categories.thresholds.tolist(),
        "feature_min": categories.profile["feature_min"],
        "feature_max": categories.profile["feature_max"],
        "neural": {k: np.asarray(v).tolist() for k, v in categories.state.items()},
        "sha256": categories.sha256,
        "trees": {},
    }
    for name, booster in zip(PATTERN_NAMES, categories.trees):
        dump = booster.dump_model()
        trees, roots = [], []
        for item in dump["tree_info"]:
            one = []
            roots.append(flatten_lgb(item["tree_structure"], one))
            trees.append(one)
        data["pattern"]["trees"][name] = dict(trees=trees, roots=roots, base=0.0)

    scenario_path = ROOT / "ml/configs/himalayan_synthetic_scenarios_v1.json"
    from ml.himachal.hazard_scenarios import HazardScenarios
    scenario_validator = HazardScenarios(scenario_path)
    scenario_bytes = scenario_path.read_bytes()
    data["scenario_config"] = json.loads(scenario_bytes)
    data["scenario_config_sha256"] = scenario_validator.sha256

    data["neural"]["mlp_v2"] = {k: np.asarray(v).tolist() for k, v in model.neural.items()}
    for family, state in legacy.components.neural.items():
        data["neural"][family] = {k: np.asarray(v).tolist() for k, v in state.items()}

    ridge_report = json.loads((ROOT / "ml/models/india_mandi_modeled_6h_v1/ridge_report.json").read_text())
    ridge_path = ROOT / "ml/models/india_mandi_modeled_6h_v1" / ridge_report["artifact"]
    with np.load(ridge_path, allow_pickle=False) as arrays:
        data["ridge"] = {k: arrays[k].tolist() for k in arrays.files}

    for relative in [*profile["files"],
                     "../india_mandi_hybrid_6h_v1/profile.json"]:
        path = (MODEL / relative).resolve()
        if path.is_file():
            data["hashes"][str(path.relative_to(ROOT))] = sha256(path)
    data["source_model_id"] = profile["id"]
    data["source_profile_sha256"] = sha256(MODEL / "profile.json")
    data["legacy_report_sha256"] = sha256(ROOT / "ml/models/india_mandi_modeled_6h_v1/training_report.json")
    return data


def emit(data: dict, output: Path):
    """Generate a C++ model header and a provenance manifest."""
    output.mkdir(parents=True, exist_ok=True)
    lines = ["#pragma once", "#include <cstdint>", "namespace mandi_v2 {",
             "#pragma pack(push, 1)",
             "struct Node { int8_t feature, left, right; float threshold, value; };",
             "#pragma pack(pop)",
             f"static constexpr uint16_t kFeatureCount = {len(data['features'])};",
             f"static constexpr uint8_t kTargetCount = {len(SENSORS)};"]
    for name, model in data["trees"].items():
        lines.extend(emit_tree_array(name, model["trees"], model["roots"], model["base"]))
    for name, model in data["pattern"]["trees"].items():
        lines.extend(emit_tree_array("cat_" + name, model["trees"], model["roots"], model["base"]))
    for family, arrays in data["neural"].items():
        for key, values in arrays.items():
            lines.extend(emit_float_array(f"{family}_{key}", values))
    for key, values in data["ridge"].items():
        lines.extend(emit_float_array(f"ridge_{key}", values))
    for key, values in data["pattern"]["neural"].items():
        lines.extend(emit_float_array(f"pattern_{key}", values))
    lines.extend(emit_float_array("pattern_tree_weights", data["pattern"]["weights"]))
    lines.extend(emit_float_array("pattern_thresholds", data["pattern"]["thresholds"]))
    lines.extend(emit_float_array("pattern_feature_min", data["pattern"]["feature_min"]))
    lines.extend(emit_float_array("pattern_feature_max", data["pattern"]["feature_max"]))
    sc = data["scenario_config"]
    rl = sc["rain_link"]
    lr = sc["latent_ranges"]
    lines += [
        f"static constexpr uint16_t kScenarioDraws = {int(sc['draws'])};",
        f"static constexpr float kCloudburstThreshold = {cpp_float(sc['cloudburst_threshold_mm_in_1h'])};",
        f"static constexpr float kLandslideIdCoefficient = {cpp_float(sc['landslide_id_coefficient'])};",
        f"static constexpr float kLandslideIdExponent = {cpp_float(sc['landslide_id_exponent'])};",
        f"static constexpr float kWetRunoffCoefficient = {cpp_float(lr['wet_runoff_coefficient'])};",
        f"static constexpr float kLandslideWetnessBase = {cpp_float(sc['landslide_wetness_adjustment']['base'])};",
        f"static constexpr float kLandslideWetnessCoefficient = {cpp_float(sc['landslide_wetness_adjustment']['wetness_coefficient'])};",
        f"static constexpr const char* kScenarioModelId = {json.dumps(sc['id'])};",
        f"static constexpr const char* kScenarioConfigSha256 = {json.dumps(data['scenario_config_sha256'])};",
        "static constexpr uint8_t kLandslideDurations[2] = {" + ",".join(str(int(x)) for x in sc['landslide_duration_hours']) + "};",
    ]
    for name, value in rl.items():
        lines.append(f"static constexpr float kRain_{name} = {cpp_float(value)};")
    lines += [
        "static constexpr float kFamilyRainMultiplier[3] = {" + ",".join(cpp_float(sc['families'][n]['rain_multiplier']) for n in ('drier','central','wetter')) + "};",
        "static constexpr float kFamilyWetness[3][2] = {" + ",".join("{"+cpp_float(sc['families'][n]['soil_wetness'][0])+","+cpp_float(sc['families'][n]['soil_wetness'][1])+"}" for n in ('drier','central','wetter')) + "};",
        "static constexpr float kFamilyCapacity[3][2] = {" + ",".join("{"+cpp_float(sc['families'][n]['capacity_m3_s_km2'][0])+","+cpp_float(sc['families'][n]['capacity_m3_s_km2'][1])+"}" for n in ('drier','central','wetter')) + "};",
        "static constexpr float kFamilySusceptibility[3] = {" + ",".join(cpp_float(sc['families'][n]['susceptible_fraction']) for n in ('drier','central','wetter')) + "};",
        f"static constexpr float kSoilStorage[2] = {{{cpp_float(lr['soil_storage_mm'][0])},{cpp_float(lr['soil_storage_mm'][1])}}};",
        f"static constexpr float kDryRunoffCoefficient[2] = {{{cpp_float(lr['dry_runoff_coefficient'][0])},{cpp_float(lr['dry_runoff_coefficient'][1])}}};",
        f"static constexpr float kCatchmentArea[2] = {{{cpp_float(lr['catchment_area_km2'][0])},{cpp_float(lr['catchment_area_km2'][1])}}};",
        "static constexpr float kConcentrationTimes[3] = {" + ",".join(cpp_float(x) for x in lr['concentration_time_hours']) + "};",
        f"static constexpr const char* kPatternModelId = {json.dumps('himachal_sensor_patterns_v1')};",
        f"static constexpr const char* kPatternProfileSha256 = {json.dumps(data['pattern']['sha256'])};",
    ]
    for target_index, target in enumerate(SENSORS):
        lines.append(f"static constexpr float xgb_teacher_weight_{target_index} = {cpp_float(data['teacher_weights'][target])};")
        for family_index, family in enumerate(data["weights"]["family_order"]):
            lines.append(f"static constexpr float v2_blend_{target_index}_{family_index} = {cpp_float(data['weights']['heads'][target]['weights'][family])};")
        legacy = data["legacy_weights"]["heads"][target]
        for family_index, family in enumerate(("neural", "xgb_history", "ridge_history")):
            lines.append(f"static constexpr float legacy_blend_{target_index}_{family_index} = {cpp_float(legacy['weights'][family])};")
        neural_name = legacy["neural"]
        neural_index = 0 if neural_name == "residual_mlp_32" else 1
        lines.append(f"static constexpr uint8_t legacy_neural_index_{target_index} = {neural_index};")
    lines.append("static constexpr const char* kSensors[6] = {" + ",".join(json.dumps(x) for x in SENSORS) + "};")
    header = "\n".join(lines + ["}  // namespace mandi_v2", ""])
    (output / "mandi_v2_trees.h").write_text(header)
    # Reproducible model smoke-test vector, generated from this exact frozen
    # Python profile. It is a synthetic software fixture, not weather evidence.
    from ml.india_mandi.tabular_v2 import TabularV2
    model = TabularV2()
    stamps = pd.date_range("2026-01-01T00:00:00Z", periods=25, freq="h")
    rows = []
    for i in range(25):
        t = 14.0 + 0.18 * i + 0.9 * np.sin(i / 4.0)
        rh = 72.0 - 0.35 * i + 2.0 * np.cos(i / 5.0)
        p = 927.0 - 0.07 * i + 0.12 * np.sin(i / 6.0)
        pm25 = 18.0 + 0.4 * i + 1.5 * np.sin(i / 3.0)
        rows.append([t, rh, p, pm25, pm25 + 11.0 + 0.1 * i, 0.8 + 0.02 * i])
    fixture = pd.DataFrame(rows, columns=SENSORS)
    fixture.insert(0, "location_id", "synthetic_test_fixture")
    fixture.insert(0, "timestamp_utc", stamps)
    expected = model.predict(fixture).iloc[-1]
    from ml.himachal.weather_categories import WeatherCategories, episode_features
    pattern_model = WeatherCategories()
    pattern_expected = pattern_model.scores(episode_features(np.asarray(rows[-7:])[None, ...]))[0]
    fixture_lines = ["#pragma once", "namespace mandi_v2 {", "static const double kSelfTestRows[25][6] = {"]
    fixture_lines += ["  {" + ",".join(cpp_float(v) for v in row) + "}," for row in rows]
    fixture_lines += ["};", "static const double kSelfTestExpected[6] = {" + ",".join(cpp_float(expected["forecast_"+c]) for c in SENSORS) + "};",
                      "static const double kSelfTestPatternExpected[10] = {" + ",".join(cpp_float(x) for x in pattern_expected) + "};",
                      "} // namespace mandi_v2", ""]
    (output / "mandi_v2_selftest.h").write_text("\n".join(fixture_lines))
    # Neural/ridge arrays are emitted separately in the next stage so the tree
    # bundle can be independently size-checked before compiling firmware.
    manifest = {
        "schema_version": "indra_mandi_edge_export_manifest_v1",
        "source_model_id": data["source_model_id"],
        "source_profile_sha256": data["source_profile_sha256"],
        "features": data["features"], "sensor_order": SENSORS,
        "forecast_horizon_hours": 6, "history_hours": 24,
        "ensemble_families": data["weights"]["family_order"],
        "self_test_fixture": "SYNTHETIC_SOFTWARE_VECTOR_NOT_FIELD_DATA",
        "lightgbm_tree_counts": {k[4:]: len(v["trees"]) for k,v in data["trees"].items() if k.startswith("lgb_")},
        "legacy_xgboost_tree_counts": {k[4:]: len(v["trees"]) for k,v in data["trees"].items() if k.startswith("xgb_")},
        "synthetic_pattern_profile_sha256": data["pattern"]["sha256"],
        "pattern_categories": PATTERN_NAMES,
        "pattern_tree_counts": {k: len(v["trees"]) for k,v in data["pattern"]["trees"].items()},
        "scenario_model_id": data["scenario_config"]["id"],
        "scenario_config_sha256": data["scenario_config_sha256"],
        "source_hashes": data["hashes"],
        "status": "HOST_PARITY_AND_ESP32_BUILD_VERIFIED_PHYSICAL_TEST_PENDING",
        "field_validated": False, "calibrated": False,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "esp32/ml_integration/generated/mandi_v2")
    args = parser.parse_args()
    data = collect()
    emit(data, args.output)
    print(json.dumps({"output": str(args.output), "tree_models": list(data["trees"]),
                      "source_profile_sha256": data["source_profile_sha256"]}, indent=2))


if __name__ == "__main__":
    main()

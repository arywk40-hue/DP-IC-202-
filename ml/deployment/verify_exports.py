"""Offline verification of committed C exports against frozen model weights.

Compiles the shipping bytes, then regenerates into a temporary directory. No
training, provider calls or source datasets are involved. Synthetic inputs test
software contracts only; this is not a weather-accuracy evaluation.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from ml.six_sensor_forecast.c_codegen import _parse_tree, _tree_depth
from ml.six_sensor_forecast.contract import PHYSICAL_RANGES, sensor_profile
from ml.six_sensor_forecast.data import sha256

SCHEMA = "indra_committed_exports_v1"


def checked(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"Missing or unsafe artifact path: {relative}")
    return path


def verify_identities(root: Path, manifest: dict) -> None:
    """Never repair checksums from changed artifacts during verification."""
    if manifest.get("schema_version") != SCHEMA:
        raise ValueError("Unknown committed-export manifest schema")
    for relative, expected in manifest["files"].items():
        if sha256(checked(root, relative)) != expected:
            raise ValueError(f"Committed artifact checksum mismatch: {relative}")


def load_head(path: Path, names: list[str], digest: str, objective: str,
              max_trees: int, max_depth: int, allow_unnamed: bool = False) -> xgb.Booster:
    if sha256(path) != digest:
        raise ValueError(f"Model checksum mismatch: {path.name}")
    model = xgb.Booster(params={"nthread": 1})
    model.load_model(path)
    config = json.loads(model.save_config())["learner"]
    names_match = model.feature_names == names or (allow_unnamed and model.feature_names is None)
    if not names_match or model.num_features() != len(names) or config["objective"]["name"] != objective:
        raise ValueError("Model feature order/objective mismatch")
    trees = [json.loads(t) for t in model.get_dump(dump_format="json")]
    if not 0 < len(trees) <= max_trees or any(_tree_depth(t) > max_depth for t in trees):
        raise ValueError("Model exceeds the documented export budget")
    return model


def split_rows(models: list, names: list[str], anchor: np.ndarray,
               missing: bool = False) -> tuple[np.ndarray, int]:
    """Threshold and adjacent float32 cases with feasible ancestor paths.

    Ancestor bounds make each tested split reachable. Infeasible adjacent cases
    (a repeated threshold can constrain an ancestor) are still tested as ordinary
    inputs. A separate leaf-path fixture exercises each reachable leaf.
    """
    rows = [anchor.copy()]
    splits = 0
    for model, local_names, depth in models:
        for tree in model.get_dump(dump_format="json"):
            nodes = _parse_tree(json.loads(tree), local_names, max_depth=depth)

            def visit(index, lo, hi):
                nonlocal splits
                node = nodes[index]
                row = np.maximum(lo, np.minimum(hi, anchor)).astype(np.float32)
                if (lo > hi).any():
                    return
                if node["feature_index"] < 0:
                    rows.append(row)
                    return
                splits += 1
                i = names.index(local_names[node["feature_index"]])
                threshold = np.float32(node["threshold"])
                for value in (np.nextafter(threshold, np.float32(-np.inf)), threshold,
                              np.nextafter(threshold, np.float32(np.inf))):
                    candidate = row.copy()
                    candidate[i] = value
                    rows.append(candidate)
                if missing:
                    candidate = row.copy()
                    candidate[i] = np.nan
                    rows.append(candidate)
                left_hi = hi.copy()
                left_hi[i] = min(hi[i], np.nextafter(threshold, np.float32(-np.inf)))
                visit(node["left_child"], lo.copy(), left_hi)
                right_lo = lo.copy()
                right_lo[i] = max(lo[i], threshold)
                visit(node["right_child"], right_lo, hi.copy())

            visit(0, np.full(len(names), -np.inf, dtype=np.float32),
                  np.full(len(names), np.inf, dtype=np.float32))
    return np.array(rows, dtype=np.float32), splits


def compile_run(header: Path, inputs: np.ndarray, outputs: int, code: str,
                setup: str = "", extra_flags: tuple = ()) -> np.ndarray:
    compiler = shutil.which("cc")
    if not compiler:
        raise RuntimeError("A C99 compiler is required; no checks are skipped")
    with tempfile.TemporaryDirectory(prefix="indra-committed-c-") as tmp:
        folder = Path(tmp)
        source = folder / "runner.c"
        source.write_text(
            '#include <stdio.h>\n#include <string.h>\n#include "' + header.name + '"\n'
            + 'int main(void) {\n' + setup + '\n'
            + f'float x[{inputs.shape[1]}], y[{outputs}];\nwhile(1) {{\n'
            + f'for(int i=0;i<{inputs.shape[1]};++i) if(scanf(" %f",x+i)!=1) return 0;\n'
            + code + '\n}\n}\n')
        binary = folder / "runner"
        build = subprocess.run([compiler, "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror",
                                *extra_flags, str(source), "-I" + str(header.parent),
                                "-lm", "-o", str(binary)], capture_output=True, text=True)
        if build.returncode:
            raise RuntimeError("Committed C compilation failed: " + build.stderr)
        data = "\n".join(" ".join(f"{float(v):.9g}" for v in r) for r in inputs) + "\n"
        run = subprocess.run([str(binary)], input=data, text=True, capture_output=True)
        if run.returncode:
            raise RuntimeError(f"Committed C safety/contract test failed ({run.returncode})")
        result = np.array([[float(v) for v in row.split()] for row in run.stdout.splitlines()])
        if len(result) != len(inputs):
            raise ValueError("Committed C returned incomplete results")
        return result


def compare(actual, expected, tolerance):
    if actual.shape != expected.shape or not np.array_equal(np.isnan(actual), np.isnan(expected)):
        raise ValueError("Committed C output shape/missing-state mismatch")
    finite = np.isfinite(expected)
    if not np.isfinite(actual[finite]).all():
        raise ValueError("Committed C produced nonfinite predictions")
    error = np.max(np.abs(actual[finite] - expected[finite]), initial=0.)
    if error > tolerance:
        raise ValueError(f"Committed C prediction parity failed: {error} > {tolerance}")
    return float(error)


def verify_forecast(root, profile, fixture, temporary):
    from ml.six_sensor_forecast.export import export
    folder = checked(root, profile["report"]).parent
    report = json.loads((folder / "training_report.json").read_text())
    names = sensor_profile(report.get("sensor_profile"))
    if report["architecture"]["student_features"] != names or report["horizon_hours"] != 6:
        raise ValueError("Forecast target/feature/horizon mismatch")
    models = [load_head(folder / report["models"][n]["student_file"], names,
                        report["models"][n]["student_sha256"], "reg:squarederror", 16, 3)
              for n in names]
    raw = pd.read_csv(fixture)[names].to_numpy("float32")
    boundary, splits = split_rows([(m, names, 3) for m in models], names, raw[0])
    lower = np.array([PHYSICAL_RANGES[n][0] for n in names], dtype="float32")
    upper = np.array([PHYSICAL_RANGES[n][1] for n in names], dtype="float32")
    rows = np.vstack([raw, boundary, lower, upper])
    invalid = []
    for i in range(len(names)):
        for value in (np.nan, np.inf, -np.inf, np.nextafter(lower[i], np.float32(-np.inf)),
                      np.nextafter(upper[i], np.float32(np.inf))):
            r = raw[0].copy()
            r[i] = value
            invalid.append(r)
    rows = np.vstack([rows, invalid]).astype("float32")
    valid = np.isfinite(rows).all(axis=1) & (rows >= lower).all(axis=1) & (rows <= upper).all(axis=1)
    expected = np.full((len(rows), len(names)), np.nan)
    matrix = xgb.DMatrix(rows[valid], feature_names=names)
    for i, (name, model) in enumerate(zip(names, models)):
        expected[valid, i] = np.clip(rows[valid, i] + np.float32(report["models"][name]["student_weight"])
                                   * model.predict(matrix), lower[i], upper[i])
    header = checked(root, profile["header"])
    output_count = len(names)
    code = f'''int ok=indra_forecast_predict(x,y);
printf("%d",ok); for(int i=0;i<{output_count};++i) printf(" %.9g",y[i]); puts("");
float alias[{output_count}]; memcpy(alias,x,sizeof(alias));
if(indra_forecast_predict(alias,alias)!=ok) return 41;
for(int i=0;i<{output_count};++i) if(!(alias[i]==y[i] || (isnan(alias[i])&&isnan(y[i]))))return 42;
if(indra_forecast_predict(NULL,y) || indra_forecast_predict(x,NULL)) return 43;'''
    result = compile_run(header, rows, output_count, code)
    if not np.array_equal(result[:, 0], valid.astype(int)):
        raise ValueError("Forecast invalid-input rejection differs")
    error = compare(result[:, 1:], expected, 2e-4)
    export(folder, fixture, temporary)
    generated = (temporary / header.name).read_text()
    if profile["compatibility"] == "legacy_without_country_evidence_macros_v1":
        # Exact, enumerated legacy difference; never normalize numerical C code.
        generated = "\n".join(line for line in generated.split("\n")
                              if not line.startswith(("#define INDRA_FORECAST_COUNTRY ",
                                                      "#define INDRA_FORECAST_EVIDENCE ")))
    elif profile["compatibility"] != "current_v1":
        raise ValueError("Unknown forecast export compatibility identity")
    if generated.encode() != header.read_bytes():
        raise ValueError("Forecast committed bytes do not reproduce")
    metadata = json.loads(checked(root, profile["export_report"]).read_text())
    if metadata["header_sha256"] != sha256(header) or metadata["model_report_sha256"] != sha256(folder / "training_report.json"):
        raise ValueError("Forecast export report identity mismatch")
    return dict(rows=len(rows), valid_rows=int(valid.sum()), invalid_rows=int((~valid).sum()),
                split_thresholds=splits, max_absolute_error=error, alias="SUPPORTED_TESTED",
                regeneration="BYTE_IDENTICAL_WITH_EXPLICIT_PROFILE", input_order=names)


def verify_events(root, profile, fixture, temporary):
    from ml.event_classifier.export import export
    from ml.event_classifier.features import ALL_EVENT_FEATURE_COLS, EVENT_NAMES, build_features
    report_path = checked(root, profile["report"])
    report = json.loads(report_path.read_text())
    names = ALL_EVENT_FEATURE_COLS
    if report["input_features"] != names or report["event_names"] != EVENT_NAMES:
        raise ValueError("Event feature/target order mismatch")
    models = [None if report["models"][n].get("skipped") else load_head(
        report_path.parent / report["models"][n]["student_file"], names,
        report["models"][n]["student_sha256"], "binary:logistic", 16, 4) for n in EVENT_NAMES]
    _, features = build_features(pd.read_csv(fixture))
    raw = features[names].dropna().to_numpy("float32")
    boundary, splits = split_rows([(m, names, 4) for m in models if m is not None], names, raw[0])
    valid = np.vstack([raw, boundary])
    invalid = []
    for i in range(len(names)):
        for value in (np.nan, np.inf, -np.inf):
            row = raw[0].copy()
            row[i] = value
            invalid.append(row)
    rows = np.vstack([valid, invalid])
    expected = np.full((len(rows), len(EVENT_NAMES)), np.nan)
    matrix = xgb.DMatrix(valid, feature_names=names)
    for i, model in enumerate(models):
        expected[:len(valid), i] = 0 if model is None else model.predict(matrix)
    header = checked(root, profile["header"])
    count = len(EVENT_NAMES)
    code = f'''int ok=indra_event_predict(x,y); printf("%d",ok);
for(int i=0;i<{count};++i)printf(" %.9g",y[i]);puts("");
if(indra_event_predict(NULL,y) || indra_event_predict(x,NULL))return 51;
float alias[{len(names)}];memcpy(alias,x,sizeof(alias));
if(indra_event_predict(alias,alias)!=0)return 52;
for(int i=0;i<{count};++i)if(!isnan(alias[i]))return 53;'''
    result = compile_run(header, rows, count, code)
    if not np.array_equal(result[:, 0], np.r_[np.ones(len(valid)), np.zeros(len(invalid))]):
        raise ValueError("Event invalid-input rejection differs")
    error = compare(result[:, 1:], expected, 5e-4)
    export(report_path.parent, fixture, temporary)
    if (temporary / header.name).read_bytes() != header.read_bytes():
        raise ValueError("Event committed header does not reproduce")
    metadata = json.loads(checked(root, profile["export_report"]).read_text())
    if metadata["header_sha256"] != sha256(header) or metadata["model_report_sha256"] != sha256(report_path):
        raise ValueError("Event export report identity mismatch")
    return dict(rows=len(rows), valid_rows=len(valid), invalid_rows=len(invalid), split_thresholds=splits,
                max_absolute_error=error, alias="UNSUPPORTED_REJECTED_LEGACY",
                unavailable_heads=[n for n, m in zip(EVENT_NAMES, models) if m is None],
                low_level_untrained_value=0, deployment_untrained_value=None,
                regeneration="BYTE_IDENTICAL", input_order=names)


def verify_india(root, profile, fixture, temporary):
    from ml.india_sensor.export import export
    metadata_path = checked(root, profile["report"])
    metadata = json.loads(metadata_path.read_text())
    manifest = json.loads(checked(root, profile["export_report"]).read_text())
    names = manifest["feature_order"]
    heads = [metadata["artifacts"]["national/" + n]["B"] for n in metadata["labels"]]
    if manifest["targets"] != list(metadata["labels"]) or list(dict.fromkeys(n for h in heads for n in h["features"])) != names:
        raise ValueError("India target/feature order mismatch")
    models = [load_head(metadata_path.parent / h["artifact"], h["features"], h["sha256"],
                        "binary:logistic", 40, 3, allow_unnamed=True) for h in heads]
    anchor = np.array([np.mean(heads[0]["training_bounds"].get(n, [0., 1.])) for n in names], dtype="float32")
    rows, splits = split_rows([(m, h["features"], 3) for m, h in zip(models, heads)], names, anchor, missing=True)
    # Every optional missing feature; all-missing/core cases and both infinities.
    extra = [np.full(len(names), np.nan, dtype="float32")]
    for i in range(len(names)):
        for v in (np.nan, np.inf, -np.inf):
            row = anchor.copy()
            row[i] = v
            extra.append(row)
    serving = np.vstack([rows, extra])
    expected = np.full((len(serving), 13), np.nan)
    core = [names.index(n) for n in ("temperature_c", "relative_humidity_pct", "wind_speed_mps")]
    accepted = ~np.isinf(serving).any(axis=1) & np.isfinite(serving[:, core]).all(axis=1)
    expected[:, 0] = accepted
    for j, (m, h) in enumerate(zip(models, heads)):
        local = serving[:, [names.index(n) for n in h["features"]]]
        bounds = np.array([h["training_bounds"][n] for n in h["features"]])
        ood = ((local < bounds[:, 0]) | (local > bounds[:, 1])).any(axis=1)
        good = accepted & ~ood
        raw = m.predict(xgb.DMatrix(local[good], feature_names=h["features"]))
        expected[good, 1+j] = raw
        calibration = h.get("calibration")
        if calibration:
            p = np.clip(raw, 1e-6, 1-1e-6)
            expected[good, 4+j] = 1 / (1 + np.exp(-(np.float32(calibration["coefficient"]) * np.log(p/(1-p)) + np.float32(calibration["intercept"]))))
        expected[:, 7+j] = 0
        expected[~np.isinf(serving).any(axis=1) & ~np.isfinite(serving[:, core]).all(axis=1), 7+j] = 4
        expected[accepted & ood, 7+j] = 3
        expected[good, 7+j] = 2 if calibration else 1
        expected[:, 10+j] = -1
        cutoff = (h.get("threshold_selection") or {}).get("raw_threshold")
        if cutoff is not None:
            expected[good, 10+j] = raw >= np.float32(cutoff)
    header = checked(root, profile["header"])
    # Compare raw trees separately, including reachable out-of-domain branches.
    finite_or_missing = ~np.isinf(rows).any(axis=1)
    raw_rows = rows[finite_or_missing]
    raw_actual = compile_run(header, raw_rows, 3,
        'y[0]=indra_raw_0(x);y[1]=indra_raw_1(x);y[2]=indra_raw_2(x);'
        'printf("%.9g %.9g %.9g\\n",y[0],y[1],y[2]);')
    raw_expected = np.column_stack([m.predict(xgb.DMatrix(raw_rows[:, [names.index(n) for n in h["features"]]], feature_names=h["features"])) for m, h in zip(models, heads)])
    raw_error = compare(raw_actual, raw_expected, 5e-5)
    code = '''float p[3];int flags[3];uint8_t status[3];
int ok=indra_india_predict(x,y,p,flags,status);printf("%d",ok);
for(int i=0;i<3;++i)printf(" %.9g",y[i]);for(int i=0;i<3;++i)printf(" %.9g",p[i]);
for(int i=0;i<3;++i)printf(" %u",status[i]);
for(int i=0;i<3;++i)printf(" %d",flags[i]);puts("");
if(indra_india_predict(NULL,y,p,flags,status)||indra_india_predict(x,NULL,p,flags,status)||
indra_india_predict(x,y,NULL,flags,status)||indra_india_predict(x,y,p,NULL,status)||
indra_india_predict(x,y,p,flags,NULL))return 61;'''
    actual = compile_run(header, serving, 3, code)
    serving_error = compare(actual, expected, 5e-5)
    # The generator needs samples, not a source archive: explicitly synthetic
    # bounded fixtures feed a temporary preparation receipt, never training.
    model_copy = temporary / "models"
    model_copy.mkdir(parents=True)
    copied = json.loads(metadata_path.read_text())
    for h in copied["artifacts"].values():
        for entry in h.values():
            if isinstance(entry, dict) and entry.get("artifact"):
                entry["artifact"] = str((metadata_path.parent / entry["artifact"]).resolve())
    (model_copy / "metadata.json").write_text(json.dumps(copied))
    sample = temporary / "contract.parquet"
    pd.DataFrame(np.tile(anchor, (4, 1)), columns=names).to_parquet(sample)
    (temporary / "preparation.json").write_text(json.dumps({"files": [{"features": str(sample)}]}))
    out = temporary / "export"
    export({"models": str(model_copy), "reports": str(temporary)}, out)
    for field in ("header", "preprocessing_header"):
        original = checked(root, profile[field])
        if (out / original.name).read_bytes() != original.read_bytes():
            raise ValueError(f"India committed bytes do not reproduce: {original.name}")
    identity = profile["metadata_compatibility"]
    # The historical receipt and bundled metadata disagree. Freeze both exact
    # identities instead of silently rewriting either research artifact. Only
    # the bundled metadata/weights verified above drive this fresh check.
    if (manifest["metadata_sha256"] != identity["legacy_receipt_metadata_sha256"]
            or sha256(metadata_path) != identity["bundled_metadata_sha256"]
            or manifest["header_sha256"] != sha256(header)
            or manifest["preprocessing_header_sha256"] != sha256(checked(root, profile["preprocessing_header"]))):
        raise ValueError("India export manifest identity mismatch")
    return dict(rows=len(serving), split_thresholds=splits, max_absolute_error=raw_error,
                serving_max_absolute_error=serving_error, regeneration="BYTE_IDENTICAL",
                alias="DISTINCT_ARRAYS_REQUIRED", input_order=names,
                metadata_compatibility=identity)


def verify(catalog: Path, output: Path | None = None, root: Path | None = None) -> dict:
    root = (root or Path(__file__).resolve().parents[2]).resolve()
    catalog_path = checked(root, str(catalog))
    catalog_data = json.loads(catalog_path.read_text())
    manifest_path = checked(root, catalog_data["committed_export_verification"])
    manifest = json.loads(manifest_path.read_text())
    verify_identities(root, manifest)
    fixture = checked(root, manifest["fixture"])
    if xgb.__version__ != manifest["runtime"]["xgboost"]:
        raise ValueError("Use the pinned requirements-himachal.txt XGBoost version")
    checks = {"forecast": verify_forecast, "event_rules": verify_events, "india_measurements": verify_india}
    results = {}
    with tempfile.TemporaryDirectory(prefix="indra-export-verify-") as tmp:
        for name, profile in manifest["profiles"].items():
            if profile["catalog_profile"] not in catalog_data["profiles"]:
                raise ValueError("Shipping profile is missing from the model catalog")
            directory = Path(tmp) / name
            directory.mkdir()
            result = checks[profile["kind"]](root, profile, fixture, directory)
            results[name] = {"status": "PASSED", "header_sha256": sha256(checked(root, profile["header"])),
                             "compatibility": profile["compatibility"], **result}
    receipt = dict(schema_version=SCHEMA, status="HOST_VERIFIED_NOT_HARDWARE_VALIDATED",
                   evidence_kind="SYNTHETIC_SOFTWARE_CONTRACT_ONLY", offline=True,
                   fixture_sha256=sha256(fixture), manifest_sha256=sha256(manifest_path),
                   runtime={"python": platform.python_version(), "xgboost": xgb.__version__, "numpy": np.__version__},
                   hardware_execution_verified=False, weather_accuracy_evaluated=False, profiles=results)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("configs/model_catalog.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offline", action="store_true", required=True)
    args = parser.parse_args()
    result = verify(args.catalog, args.output)
    print(json.dumps({"status": result["status"], "profiles": list(result["profiles"]), "output": str(args.output)}))


if __name__ == "__main__":
    main()

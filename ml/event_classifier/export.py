"""Export rule classifiers to a separate C99 header with Python/C parity."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from ml.six_sensor_forecast.c_codegen import _c_float, _parse_tree, _tree_depth
from ml.six_sensor_forecast.data import sha256
from ml.event_classifier.features import ALL_EVENT_FEATURE_COLS, EVENT_NAMES
from ml.event_classifier.train import EVENT_SCHEMA


def export(
    model_dir: Path, observations: Path, output: Path, tolerance: float = 5e-4
) -> dict:
    if not np.isfinite(tolerance) or not 0 < tolerance <= 5e-4:
        raise ValueError("Parity tolerance must be in (0, 5e-4]")
    compiler = shutil.which("cc")
    if compiler is None:
        raise RuntimeError("A C compiler is required to verify exported predictions")
    report = json.loads((model_dir / "event_training_report.json").read_text())

    count_features = len(ALL_EVENT_FEATURE_COLS)
    count_events = len(EVENT_NAMES)

    if (
        report["schema_version"] != EVENT_SCHEMA
        or report["event_names"] != EVENT_NAMES
        or report["input_features"] != ALL_EVENT_FEATURE_COLS
        or set(report["models"]) != set(EVENT_NAMES)
    ):
        raise ValueError("Incomplete or incompatible event model")

    from ml.event_classifier.features import build_features
    _, features_df = build_features(pd.read_csv(observations))
    sample = features_df[ALL_EVENT_FEATURE_COLS].dropna()
    sample = sample[np.isfinite(sample).all(axis=1)]
    if sample.empty:
        raise ValueError("No complete observations for parity")
    sample = sample.sample(n=min(2048, len(sample)), random_state=42).to_numpy(
        dtype=np.float32
    )

    models = []

    lines = [
        "/* Sensor-rule classifier. No independently observed hazard labels. */",
        "#ifndef INDRA_EVENT_CLASSIFIER_H",
        "#define INDRA_EVENT_CLASSIFIER_H",
        "#include <math.h>",
        "#include <stddef.h>",
        f"#define INDRA_EVENT_INPUTS {count_features}",
        f"#define INDRA_EVENT_OUTPUTS {count_events}",
        '#define INDRA_EVENT_STATUS "OFFLINE_RESEARCH_ONLY"',
        "/* Input feature order: " + ", ".join(ALL_EVENT_FEATURE_COLS) + " */",
        "/* Output probability order: " + ", ".join(EVENT_NAMES) + " */",
    ]
    total_nodes = 0

    for ev_idx, target in enumerate(EVENT_NAMES):
        entry = report["models"].get(target)
        if not entry or entry.get("skipped"):
            lines.append(
                f"static inline float indra_ev_head_{ev_idx}(const float *x) "
                f"{{ (void)x; return 0.0f; }}"
            )
            models.append(None)
            continue

        path = model_dir / entry["student_file"]
        if sha256(path) != entry["student_sha256"]:
            raise ValueError(f"Student checksum mismatch: {target}")

        model = xgb.Booster()
        model.load_model(path)
        if model.feature_names != ALL_EVENT_FEATURE_COLS:
            raise ValueError(f"Event model feature order mismatch: {target}")

        config = json.loads(model.save_config())["learner"]
        if config["objective"]["name"] != "binary:logistic":
            raise ValueError(f"Event model objective mismatch: {target}")
        base = float(str(config["learner_model_param"]["base_score"]).strip("[]"))
        if not 0 < base < 1:
            raise ValueError(f"Invalid logistic base score: {target}")
        trees = [json.loads(t) for t in model.get_dump(dump_format="json")]
        if len(trees) > report["architecture"]["max_trees"] or any(_tree_depth(tree) > 4 for tree in trees):
            raise ValueError(f"Event model exceeds tree budget: {target}")

        models.append(model)

        for tree_index, tree in enumerate(trees):
            nodes = _parse_tree(tree, ALL_EVENT_FEATURE_COLS, max_depth=4)
            total_nodes += len(nodes)
            lines.append(
                f"static inline float indra_ev_{ev_idx}_{tree_index}(const float *x) {{"
            )

            def emit(index: int, indent: str, tree_nodes: list[dict]) -> None:
                node = tree_nodes[index]
                if node["feature_index"] == -1:
                    lines.append(f"{indent}return {_c_float(node['leaf_value'])};")
                    return
                feature = node["feature_index"]
                threshold = np.float32(node["threshold"])
                lines.append(f"{indent}if (x[{feature}] < {_c_float(threshold)}) {{")
                emit(node["left_child"], indent + "  ", tree_nodes)
                lines.append(f"{indent}}} else {{")
                emit(node["right_child"], indent + "  ", tree_nodes)
                lines.append(f"{indent}}}")

            emit(0, "  ", nodes)
            lines.append("}")

        lines.append(
            f"static inline float indra_ev_head_{ev_idx}(const float *x) {{"
        )
        lines.append(f"  float raw = {_c_float(np.log(base / (1.0 - base)))};")
        for tree_index in range(len(trees)):
            lines.append(f"  raw += indra_ev_{ev_idx}_{tree_index}(x);")
        lines.append("  return 1.0f / (1.0f + expf(-raw));")
        lines.append("}")

    lines.extend(
        [
            "/* Returns 1 on success, 0 for null pointers or non-finite features.",
            " * Outputs are NAN on invalid sensor data. No heap allocation. */",
            "static inline int indra_event_predict(const float *input, float *output) {",
            "  if (!input || !output) return 0;",
            f"  for (int i = 0; i < {count_events}; ++i) output[i] = NAN;",
            f"  float x[{count_features}];",
            f"  for (int i = 0; i < {count_features}; ++i) {{",
            "    if (!isfinite(input[i])) return 0;",
            "    x[i] = input[i];",
            "  }",
        ]
    )
    for index in range(count_events):
        lines.append(f"  output[{index}] = indra_ev_head_{index}(x);")
    lines.extend(["  return 1;", "}", "#endif", ""])

    samples = sample.astype(np.float32)

    expected = np.zeros((len(samples), count_events), dtype=np.float64)
    for ev_idx, model in enumerate(models):
        if model is None:
            continue
        dm = xgb.DMatrix(samples, feature_names=ALL_EVENT_FEATURE_COLS)
        expected[:, ev_idx] = model.predict(dm)

    invalid_samples = np.tile(sample[0], (3, 1))
    invalid_samples[0, 0] = np.nan
    invalid_samples[1, 0] = np.inf
    invalid_samples[2, 0] = -np.inf
    all_samples = np.vstack([samples, invalid_samples])

    runner = """#include <stdio.h>
#include "indra_event_classifier.h"
int main(void) {
  float x[INDRA_EVENT_INPUTS], y[INDRA_EVENT_OUTPUTS];
  while (1) {
    int got = 0;
    for (int i=0; i<INDRA_EVENT_INPUTS; ++i) {
      if (scanf(" %f", &x[i]) != 1) { got = -1; break; }
      got++;
    }
    if (got != INDRA_EVENT_INPUTS) break;
    int ok = indra_event_predict(x, y);
    printf("%d", ok);
    for (int i=0; i<INDRA_EVENT_OUTPUTS; ++i) printf(" %.9g", y[i]);
    puts("");
  }
  return 0;
}
"""
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        header = temporary / "indra_event_classifier.h"
        header.write_text("\n".join(lines))
        (temporary / "runner.c").write_text(runner)
        binary = temporary / "runner"
        subprocess.run(
            [
                compiler,
                "-std=c99",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(temporary / "runner.c"),
                "-lm",
                "-o",
                str(binary),
            ],
            check=True,
            capture_output=True,
        )
        stdin = (
            "\n".join(" ".join(f"{float(v):.9g}" for v in row) for row in all_samples)
            + "\n"
        )
        process = subprocess.run(
            [str(binary)], input=stdin, text=True, capture_output=True, check=True
        )
        actual = np.array(
            [[float(v) for v in line.split()] for line in process.stdout.splitlines()]
        )

        if (
            actual.shape != (len(all_samples), count_events + 1)
            or not (actual[: len(samples), 0] == 1).all()
        ):
            raise RuntimeError(
                "C runner rejected valid input or returned incomplete predictions"
            )
        if (
            not (actual[len(samples) :, 0] == 0).all()
            or not np.isnan(actual[len(samples) :, 1:]).all()
        ):
            raise RuntimeError("C runner failed invalid-input rejection")

        error = np.max(np.abs(expected - actual[: len(samples), 1:]), axis=0)
        if not np.isfinite(error).all() or error.max() > tolerance:
            raise RuntimeError(f"Python/C parity failed: {error.tolist()}")

        output.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(header, output / header.name)

    metadata = {
        "schema_version": EVENT_SCHEMA,
        "status": "OFFLINE_RESEARCH_ONLY",
        "input_features": ALL_EVENT_FEATURE_COLS,
        "heads": count_events,
        "trees_per_head": report["architecture"]["max_trees"],
        "max_depth": 4,
        "total_nodes": total_nodes,
        "header_bytes": (output / header.name).stat().st_size,
        "header_sha256": sha256(output / header.name),
        "model_report_sha256": sha256(model_dir / "event_training_report.json"),
        "parity": {
            "valid_rows": len(samples),
            "invalid_rows": len(invalid_samples),
            "absolute_tolerance": tolerance,
            "passed": True,
        },
    }
    (output / "event_c_export_report.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=Path("ml/models/uci_beijing_event_rules_6sensor"))
    parser.add_argument(
        "--observations",
        type=Path,
        default=Path("data/uci_beijing_air_quality/observations.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("ml/models/uci_beijing_event_rules_6sensor/esp32_student/export"),
    )
    args = parser.parse_args()
    print(json.dumps(export(args.model, args.observations, args.output), indent=2))


if __name__ == "__main__":
    main()

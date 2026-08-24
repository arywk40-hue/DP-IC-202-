"""Validate Python XGBoost probabilities against a generated C header."""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb


CLASSES = ["wildfire", "flood", "storm", "air_quality"]


def python_outputs(model_dir, raw):
    with open(os.path.join(model_dir, "normalization.json")) as f:
        stats = json.load(f)
    X = (raw - np.asarray(stats["mean"], dtype=np.float32)) / np.asarray(stats["std"], dtype=np.float32)
    outputs = []
    for name in CLASSES:
        model = xgb.Booster()
        model.load_model(os.path.join(model_dir, f"xgboost_{name}.json"))
        outputs.append(model.predict(xgb.DMatrix(X)))
    return np.column_stack(outputs)


def c_source(header_name, vectors):
    rows = []
    for vector in vectors:
        literals = []
        for value in vector:
            literal = f"{float(value):.9g}"
            if "." not in literal and "e" not in literal.lower():
                literal += ".0"
            literals.append(literal + "f")
        rows.append("{" + ", ".join(literals) + "}")
    return f'''#include <stdio.h>
#include "{header_name}"

int main(void) {{
    const float vectors[{len(vectors)}][NUM_FEATURES] = {{
        {', '.join(rows)}
    }};
    for (int i = 0; i < {len(vectors)}; i++) {{
        float wf, fl, st, aq;
        xgb_model_inference(vectors[i], &wf, &fl, &st, &aq);
        printf("%.9g %.9g %.9g %.9g\\n", wf, fl, st, aq);
    }}
    return 0;
}}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--header", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--data", required=True, help="Prepared features.csv containing raw feature vectors")
    parser.add_argument("--tolerance", type=float, default=3e-5)
    args = parser.parse_args()

    header = Path(args.header).resolve()
    raw_all = pd.read_csv(args.data).to_numpy(dtype=np.float32)
    if raw_all.shape[1] != 14:
        raise ValueError(f"Expected 14 raw features, got {raw_all.shape[1]}")
    indices = np.linspace(0, len(raw_all) - 1, num=min(8, len(raw_all)), dtype=int)
    raw = raw_all[indices]
    expected = python_outputs(args.model, raw)

    with tempfile.TemporaryDirectory(prefix="c_parity_") as tmp:
        source = Path(tmp) / "parity.c"
        binary = Path(tmp) / "parity"
        source.write_text(c_source(header.name, raw))
        compile_result = subprocess.run([
            "clang", "-std=c99", "-I", str(header.parent), str(source),
            "-lm", "-o", str(binary),
        ], capture_output=True, text=True)
        if compile_result.returncode:
            raise RuntimeError(compile_result.stderr)
        run_result = subprocess.run([str(binary)], capture_output=True, text=True, check=True)

    actual = np.asarray([[float(v) for v in line.split()] for line in run_result.stdout.splitlines()])
    errors = np.abs(expected - actual)
    max_error = float(errors.max())
    print(f"vectors={len(raw)} max_abs_error={max_error:.9g} tolerance={args.tolerance}")
    if max_error > args.tolerance:
        print("expected:")
        print(expected)
        print("actual:")
        print(actual)
        raise SystemExit(1)
    print("Python/C parity: PASS")


if __name__ == "__main__":
    main()

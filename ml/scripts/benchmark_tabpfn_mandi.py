"""Optional isolated local TabPFN v2 benchmark on bounded, comparable rows.

Run with .venv/tabpfn/bin/python after installing tabpfn==2.2.1 there.
No hosted inference, telemetry, production promotion or test-set selection.
"""

import os

os.environ["TABPFN_DISABLE_TELEMETRY"] = "1"
os.environ["TABPFN_MODEL_CACHE_DIR"] = os.path.abspath("ml/data/himachal/tabpfn_cache")
import argparse
import json
from pathlib import Path
import time

import numpy as np
import torch
from tabpfn import TabPFNRegressor


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--input", type=Path, default=Path("ml/data/himachal/tabpfn_benchmark_inputs.npz")
    )
    p.add_argument(
        "--output", type=Path, default=Path("ml/reports/mandi_pipeline_v2/tabpfn.json")
    )
    a = p.parse_args()
    torch.set_num_threads(2)
    with np.load(a.input, allow_pickle=False) as data:
        d = {k: data[k] for k in data.files}
    results = []
    predictions = []
    for j in range(6):
        started = time.monotonic()
        model = TabPFNRegressor(
            device="cpu",
            n_estimators=1,
            n_jobs=2,
            random_state=42,
            fit_mode="low_memory",
            model_path="auto",
        )
        model.fit(d["train_x"], d["train_y"][:, j])
        pred = np.clip(
            model.predict(d["test_x"]) + d["test_current"][:, j],
            d["low"][j],
            d["high"][j],
        )
        predictions.append(pred)
        results.append(
            dict(
                target_index=j,
                rows=len(pred),
                mae=float(np.abs(pred - d["test_truth"][:, j]).mean()),
                seconds=time.monotonic() - started,
            )
        )
        print(results[-1], flush=True)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(
        json.dumps(
            dict(
                model="TabPFN v2 local regression",
                train_context_rows=len(d["train_x"]),
                test_rows=len(d["test_x"]),
                purpose="BOUNDED_REUSED_TEST_SUBSET_DIAGNOSTIC_NOT_PRODUCTION_SELECTION",
                telemetry=False,
                hosted_inference=False,
                metrics=results,
                predictions=np.column_stack(predictions).tolist(),
                baseline_mae={k: d[k].tolist() for k in d if k.endswith("_mae")},
                license="Prior Labs v2 model weights; separate attribution/license, no checkpoint redistributed",
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()

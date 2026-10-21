"""Generate explicitly flagged PM simulations where old Mandi API PM is missing."""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd

from ml.india_mandi.data import (
    AIR,
    WEATHER,
    fetch,
    month_windows,
    prepare,
)
from ml.india_mandi.synthetic_pm import audit, fit_and_generate
from ml.six_sensor_forecast.data import sha256


def verify(out, c, config_path, reproduce=False):
    """Audit the saved dataset without overwriting it; optionally repeat its draw."""
    manifest = json.loads((out / "manifest.json").read_text())
    source_manifest = json.loads((out / "source/dataset_manifest.json").read_text())
    if sha256(config_path) != source_manifest["experiment_config_sha256"]:
        raise ValueError(
            "Synthetic configuration differs from the saved source version"
        )
    ref_root = ROOT / c["reference_data"]
    for path, expected in [
        (out / "dataset.csv", manifest["dataset_sha256"]),
        (out / "source/observations.csv", manifest["source_original_sha256"]),
        (ref_root / "observations.csv", manifest["reference_sha256"]),
    ]:
        if sha256(path) != expected:
            raise ValueError("Synthetic/source checksum changed: " + str(path))
    original = pd.read_csv(out / "source/observations.csv")
    saved = pd.read_csv(out / "dataset.csv")
    quality = audit(original, saved)
    if reproduce:
        repeated, models, _ = fit_and_generate(
            pd.read_csv(ref_root / "observations.csv"),
            original,
            c["fit_before"],
            c["seed"],
            c["lightgbm_rounds"],
        )
        np.testing.assert_allclose(
            saved[["pm25_ug_m3", "pm10_ug_m3"]],
            repeated[["pm25_ug_m3", "pm10_ug_m3"]],
            rtol=1e-12,
            atol=1e-12,
        )
        for name, model in zip(["fine_pm", "coarse_pm"], models):
            if model.booster_.model_to_string() != (out / (name + ".txt")).read_text():
                raise ValueError("Saved generator weights differ from the seeded fit")
    receipt = {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": manifest["dataset_sha256"],
        "configuration_sha256": sha256(config_path),
        "generator_code_sha256": sha256(ROOT / "ml/india_mandi/synthetic_pm.py"),
        "generator_files": {
            p.name: sha256(p) for p in [out / "fine_pm.txt", out / "coarse_pm.txt"]
        },
        "seeded_draw_reproduced": reproduce,
        "source_hashes_verified": True,
        "coverage_start_utc": pd.to_datetime(saved.timestamp_utc, utc=True)
        .min()
        .isoformat(),
        "coverage_end_utc": pd.to_datetime(saved.timestamp_utc, utc=True)
        .max()
        .isoformat(),
        "quality": quality,
        "attribution": json.loads((out / "source/dataset_manifest.json").read_text())[
            "attribution"
        ],
    }
    report = ROOT / "reports" / ("mandi_" + out.name)
    report.mkdir(parents=True, exist_ok=True)
    for name, value in [("quality.json", quality), ("verification.json", receipt)]:
        (report / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    print(json.dumps(receipt, indent=2))
    print("Verified dataset:", out / "dataset.csv")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--config", type=Path, default=ROOT / "configs/mandi_synthetic_pm_v1.json"
    )
    p.add_argument("--offline", action="store_true")
    p.add_argument(
        "--verify",
        action="store_true",
        help="Verify existing dataset without overwriting",
    )
    p.add_argument(
        "--reproduce",
        action="store_true",
        help="With --verify, repeat the seeded draw in memory",
    )
    a = p.parse_args()
    c = json.loads(a.config.read_text())
    out = (ROOT / c["output"]).resolve()
    source = out / "source"
    raw = source / "raw"
    if (
        not out.is_relative_to(ROOT / "data/himachal")
        or not out.name.startswith("synthetic_pm_")
        or c["schema_version"] != "indra_synthetic_pm_v1"
    ):
        raise ValueError("Separate ignored synthetic output required")
    if a.verify:
        verify(out, c, a.config, a.reproduce)
        return
    if a.reproduce:
        raise ValueError("--reproduce requires --verify")
    if (out / "dataset.csv").exists():
        raise ValueError(
            "Synthetic version exists; preserve it and choose another output"
        )
    raw.mkdir(parents=True, exist_ok=True)
    jobs = []
    for start, end in month_windows(c["start_date"], c["end_date"]):
        common = {
            "latitude": 31.71,
            "longitude": 76.93,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "timezone": "UTC",
        }
        jobs.extend(
            [
                (
                    "weather",
                    {
                        **common,
                        "models": "ecmwf_ifs",
                        "wind_speed_unit": "ms",
                        "hourly": ",".join(
                            [
                                *WEATHER.values(),
                                "precipitation",
                                "snowfall",
                                "wind_gusts_10m",
                            ]
                        ),
                    },
                ),
                (
                    "air",
                    {
                        **common,
                        "domains": "cams_global",
                        "hourly": ",".join(AIR.values()),
                    },
                ),
            ]
        )

    def get(job):
        return fetch(job[0], job[1], raw, a.offline)

    with ThreadPoolExecutor(max_workers=3) as pool:
        for i, _ in enumerate(pool.map(get, jobs), 1):
            if i % 24 == 0:
                print("Historical API responses", i, "/", len(jobs), flush=True)
    cfg = {
        "data": str(source),
        "start_date": c["start_date"],
        "end_date": c["end_date"],
        "latitude": 31.71,
        "longitude": 76.93,
        "weather_model": "ecmwf_ifs",
        "air_domain": "cams_global",
        "_config_sha256": sha256(a.config),
    }
    original = prepare(cfg, offline=True)
    ref_root = ROOT / c["reference_data"]
    reference = pd.read_csv(ref_root / "observations.csv")
    ref_manifest = json.loads((ref_root / "dataset_manifest.json").read_text())
    if sha256(ref_root / "observations.csv") != ref_manifest["observations_sha256"]:
        raise ValueError("Reference source changed")
    source_frame = pd.read_csv(source / "observations.csv")
    generated, models, details = fit_and_generate(
        reference, source_frame, c["fit_before"], c["seed"], c["lightgbm_rounds"]
    )
    quality = audit(source_frame, generated)
    generated.to_csv(out / "dataset.csv", index=False)
    for name, model in zip(["fine_pm", "coarse_pm"], models):
        model.booster_.save_model(str(out / (name + ".txt")))
    manifest = {
        "schema_version": "indra_synthetic_pm_dataset_v1",
        "evidence_kind": "SYNTHETIC_AUGMENTATION_NOT_MEASURED_OR_API_PM_TRUTH",
        "rows": len(generated),
        "source_original_sha256": original["observations_sha256"],
        "reference_sha256": ref_manifest["observations_sha256"],
        "dataset_sha256": sha256(out / "dataset.csv"),
        "generator": details,
        "validation_or_test_labels_generated": False,
        "active_model_retrained": False,
        "field_accuracy_established": False,
        "coverage_start_utc": generated.timestamp_utc.min().isoformat(),
        "coverage_end_utc": generated.timestamp_utc.max().isoformat(),
        "configuration_sha256": sha256(a.config),
        "source_manifest": "source/dataset_manifest.json",
        "generator_files": {
            name + ".txt": sha256(out / (name + ".txt"))
            for name in ["fine_pm", "coarse_pm"]
        },
        "attribution": original["attribution"],
        "license": original["license"],
        "quality": quality,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n"
    )
    report = ROOT / "reports" / ("mandi_" + out.name)
    report.mkdir(parents=True, exist_ok=True)
    (report / "manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n"
    )
    (report / "quality.json").write_text(
        json.dumps(quality, indent=2, allow_nan=False) + "\n"
    )
    print(json.dumps(manifest, indent=2))
    print("Dataset:", out / "dataset.csv")


if __name__ == "__main__":
    main()

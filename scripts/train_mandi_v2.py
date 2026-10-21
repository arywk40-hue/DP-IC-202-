"""Fit the versioned expanded Mandi tabular pipeline, preserving all v1 weights."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.india_mandi.tabular_v2 import train, evaluate  # noqa: E402


def prepare_data(path):
    """Acquire the configured source, reusing immutable raw snapshots when present."""
    from concurrent.futures import ThreadPoolExecutor
    import json, shutil
    from ml.india_mandi.data import month_windows, fetch, prepare, WEATHER, AIR
    from ml.six_sensor_forecast.data import sha256

    c = json.loads(Path(path).read_text())
    out = (ROOT / c["data"]).resolve()
    raw = out / "raw"
    if not out.is_relative_to(ROOT / "data/himachal"):
        raise ValueError("Expanded raw source must stay ignored under data/himachal")
    raw.mkdir(parents=True, exist_ok=True)
    sources = [
        ROOT / "data/india_mandi_modeled/raw",
        *ROOT.glob("data/himachal/mandi_api/*/raw"),
    ]
    for old in sources:
        for file in old.glob("*.json"):
            if not (raw / file.name).exists():
                shutil.copy2(file, raw / file.name)
    jobs = []
    for start, end in month_windows(c["start_date"], c["end_date"]):
        common = dict(
            latitude=31.71,
            longitude=76.93,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            timezone="UTC",
        )
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
        return fetch(job[0], job[1], raw)

    with ThreadPoolExecutor(max_workers=3) as pool:
        for _ in pool.map(get, jobs):
            pass
    result = prepare(
        dict(
            data=str(out),
            start_date=c["start_date"],
            end_date=c["end_date"],
            latitude=31.71,
            longitude=76.93,
            weather_model="ecmwf_ifs",
            air_domain="cams_global",
            _config_sha256=sha256(Path(path)),
        ),
        offline=True,
    )
    print(
        "Expanded Mandi source:",
        result["rows"],
        "positions;",
        result["complete_six_channel_rows"],
        "complete",
    )
    live_input = ROOT / "data/himachal/live_hourly.json"
    if not live_input.exists():
        import pandas as pd
        from ml.india_mandi.submission import replay_records

        frame = pd.read_csv(out / "observations.csv")
        frame["timestamp_utc"] = pd.to_datetime(frame.timestamp_utc, utc=True)
        live_input.write_text(
            json.dumps(replay_records(frame, result), indent=2, allow_nan=False) + "\n"
        )
        print("Historical model-grid input initialized:", live_input)


def prepare_tabpfn_inputs(path):
    """Build the fixed bounded comparison matrices in the main model environment."""
    import json
    import numpy as np
    from ml.india_mandi.tabular_v2 import dataset, TabularV2, combine
    from ml.six_sensor_forecast.contract import PHYSICAL_RANGES

    c = json.loads(Path(path).read_text())
    f, x, y, m, manifest = dataset(c)
    engine = TabularV2()
    if manifest["observations_sha256"] != engine.profile["source_sha256"]:
        raise ValueError("Frozen source mismatch")
    a = np.flatnonzero(m["train"])
    a = a[np.linspace(0, len(a) - 1, 512, dtype=int)]
    b = np.flatnonzero(m["future_test"])
    b = b[np.linspace(0, len(b) - 1, 96, dtype=int)]
    columns = engine.profile["sensors"]
    candidates = engine.candidates(x.iloc[b], f.iloc[b][columns])
    candidates["selected_v2"] = combine(candidates, engine.weights)
    payload = dict(
        train_x=x.iloc[a].to_numpy(float),
        train_y=y.iloc[a].to_numpy(float) - f.iloc[a][columns].to_numpy(float),
        test_x=x.iloc[b].to_numpy(float),
        test_truth=y.iloc[b].to_numpy(float),
        test_current=f.iloc[b][columns].to_numpy(float),
    )
    payload.update(
        {
            k + "_mae": np.abs(v - payload["test_truth"]).mean(axis=0)
            for k, v in candidates.items()
        }
    )
    payload["low"], payload["high"] = np.array([PHYSICAL_RANGES[c] for c in columns]).T
    target = ROOT / "data/himachal/tabpfn_benchmark_inputs.npz"
    if target.exists():
        with np.load(target, allow_pickle=False) as saved:
            if set(saved.files) != set(payload) or any(
                not np.allclose(saved[k], v, rtol=0, atol=1e-10)
                for k, v in payload.items()
            ):
                raise ValueError(
                    "Existing TabPFN benchmark context differs; preserve it rather than overwrite"
                )
    else:
        np.savez_compressed(target, **payload)
    print("Frozen TabPFN input:", target)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--config", type=Path, default=ROOT / "configs/mandi_pipeline_v2.json"
    )
    p.add_argument("--prepare", action="store_true")
    p.add_argument("--train", action="store_true")
    p.add_argument("--evaluate", action="store_true")
    p.add_argument("--tabpfn-inputs", action="store_true")
    a = p.parse_args()
    if not (a.prepare or a.train or a.evaluate or a.tabpfn_inputs):
        p.error(
            "Choose --prepare, --train or --evaluate; existing versions are never overwritten"
        )
    if a.prepare:
        prepare_data(a.config)
    if a.train:
        r = train(a.config)
        print(r["profile_id"], r["data_rows"], r["rows_by_role"])
    if a.tabpfn_inputs:
        prepare_tabpfn_inputs(a.config)
    if a.evaluate:
        r = evaluate(a.config)
        for c, score in r["metrics"]["future_test"]["selected_v2"].items():
            print(
                c,
                "v2 MAE",
                round(score["mae"], 4),
                "v1 MAE",
                round(r["metrics"]["future_test"]["legacy_hybrid"][c]["mae"], 4),
            )

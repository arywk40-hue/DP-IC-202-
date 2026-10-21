"""Persistent delayed-label six-sensor shadow worker, or explicit simulated replay."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd  # noqa: E402
from ml.india_mandi.online import for_model, ingest_native  # noqa: E402
from ml.india_mandi.tabular_v2 import TabularV2, dataset  # noqa: E402
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS  # noqa: E402
from server.dashboard import read_observations  # noqa: E402


def replay(config, state_path):
    """Prequential research simulation; original API timely availability is unknown."""
    cfg = json.loads(Path(config).read_text())
    engine = TabularV2()
    learner = for_model(state_path, engine)
    frame, features, _, _, manifest = dataset(cfg)
    start = pd.Timestamp(cfg["test_start"])
    take = frame.timestamp_utc >= start - pd.Timedelta(hours=24)
    frame = frame.loc[take].reset_index(drop=True)
    # Compute frozen predictions causally once; SGD never sees future features/labels.
    predictions = engine.predict(frame)
    from ml.six_sensor_forecast.features import build_features

    frame, features = build_features(frame)
    namespace = "simulated:" + manifest["observations_sha256"][:24]
    for i, row in frame.iterrows():
        ready = (
            row.timestamp_utc >= start
            and predictions.iloc[i]["status"] == "HYBRID_READY"
        )
        learner.observe(
            namespace,
            row.timestamp_utc,
            row.timestamp_utc,
            row[RAW_SENSOR_COLUMNS].tolist(),
            features.iloc[i].to_numpy() if ready else None,
            predictions.iloc[i][["forecast_" + c for c in RAW_SENSOR_COLUMNS]].to_numpy(
                float
            )
            if ready
            else None,
            row.timestamp_utc,
            mode="SIMULATED_TIMELY_MODEL_GRID_REPLAY_NOT_LIVE",
        )
    summary = learner.summary()
    summary["evidence"] = "RETROSPECTIVE_PREQUENTIAL_SIMULATION_ASSUMES_TIMELY_ARRIVAL"
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    modes = p.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--input",
        type=Path,
        help="Canonical hourly native snapshot file; actual availability retained",
    )
    modes.add_argument(
        "--replay",
        action="store_true",
        help="Explicit research simulation, never live accuracy",
    )
    p.add_argument("--state", type=Path, required=True)
    p.add_argument(
        "--config", type=Path, default=ROOT / "configs/mandi_pipeline_v2.json"
    )
    p.add_argument("--watch-seconds", type=float, default=0)
    p.add_argument("--summary", type=Path)
    a = p.parse_args()
    if a.watch_seconds and (a.replay or a.watch_seconds < 2):
        p.error("Watch supports native input only, at least two seconds")
    engine = None if a.replay else TabularV2()
    digest = None
    while True:
        try:
            new = None if a.replay else hashlib.sha256(a.input.read_bytes()).hexdigest()
            if a.replay or new != digest:
                result = (
                    replay(a.config, a.state)
                    if a.replay
                    else ingest_native(read_observations(a.input), a.state, engine)
                )
                if a.summary:
                    a.summary.parent.mkdir(parents=True, exist_ok=True)
                    a.summary.write_text(
                        json.dumps(result, indent=2, allow_nan=False) + "\n"
                    )
                print(json.dumps(result, allow_nan=False), flush=True)
                digest = new
        except (OSError, ValueError) as error:
            if not a.watch_seconds:
                raise
            # A file may be momentarily incomplete during replacement. Do not
            # mark it processed; retry and expose the error instead of stopping.
            print(
                json.dumps(dict(status="WAITING_FOR_VALID_INPUT", error=str(error))),
                flush=True,
            )
        if not a.watch_seconds:
            break
        time.sleep(a.watch_seconds)


if __name__ == "__main__":
    main()

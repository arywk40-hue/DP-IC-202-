"""Fetch current Mandi model grids, publish locally and save delayed shadow tests.

These are ECMWF/CAMS modeled values, not live station/sensor measurements.
"""

import argparse
import fcntl
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.india_mandi.live import atomic_json, collect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "data/himachal/mandi_current_api_v1"
    )
    parser.add_argument(
        "--db", type=Path, help="Optional dashboard SQLite store to refresh"
    )
    parser.add_argument(
        "--online-state", type=Path, help="Optional delayed-label shadow store"
    )
    parser.add_argument(
        "--watch-seconds",
        type=int,
        default=0,
        help="0 fetches once; otherwise >=900 seconds",
    )
    args = parser.parse_args()
    directory = args.output.resolve()
    if not directory.is_relative_to(ROOT / "data/himachal"):
        parser.error("Keep raw current snapshots under ignored data/himachal")
    if args.watch_seconds and args.watch_seconds < 900:
        parser.error("Poll no more often than every 900 seconds")
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "collector.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while True:
            try:
                rows, result = collect(directory)
                if args.db:
                    from server.dashboard import Store, assess

                    nodes = assess(rows)
                    Store(args.db).replace(nodes)
                    result["dashboard_nodes"] = len(nodes)
                    result["latest_forecast"] = {
                        k: nodes[-1][k]
                        for k in [
                            "timestamp",
                            "forecastTimestamp",
                            "forecastStatus",
                            "sensors",
                            "forecast6h",
                            "sourceClass",
                        ]
                    }
                if args.online_state:
                    from ml.india_mandi.online import ingest_native
                    from ml.india_mandi.registry import load_forecaster

                    result["online"] = ingest_native(
                        rows, args.online_state, load_forecaster()
                    )
                atomic_json(directory / "status.json", result)
                print(json.dumps(result, allow_nan=False), flush=True)
            except (OSError, ValueError) as error:
                if not args.watch_seconds:
                    raise
                print(
                    json.dumps(
                        {
                            "status": "FETCH_FAILED_PREVIOUS_DATA_RETAINED",
                            "error": str(error),
                        }
                    ),
                    flush=True,
                )
            if not args.watch_seconds:
                break
            time.sleep(args.watch_seconds)


if __name__ == "__main__":
    main()

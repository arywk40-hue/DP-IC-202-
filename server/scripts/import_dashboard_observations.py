"""Atomically publish operator-reviewed native snapshots to the local dashboard."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from server.dashboard import Store, assess, read_observations  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--db", type=Path, default=ROOT/"ml/data/himachal/dashboard.sqlite")
    p.add_argument('--online-state',type=Path,help='Process actual hourly arrivals with the persistent shadow learner')
    args = p.parse_args()
    # Finish validation and inference before replacing the previous snapshot.
    raw=read_observations(args.input)
    prepared = assess(raw)
    Store(args.db).replace(prepared)
    if args.online_state is not None:
        from ml.india_mandi.online import ingest_native
        from ml.india_mandi.registry import load_forecaster
        ingest_native(raw,args.online_state,load_forecaster())
    print(json.dumps(dict(nodes=len(prepared), source_classes=sorted({n["sourceClass"] for n in prepared}),
        public_alerts=False, accuracy="NOT_EVALUATED", refresh="Dashboard polls every eight seconds")))


if __name__ == "__main__":
    main()

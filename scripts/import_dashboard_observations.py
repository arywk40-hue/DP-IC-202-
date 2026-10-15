"""Atomically publish operator-reviewed native snapshots to the local dashboard."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.dashboard import Store, assess, read_observations  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--db", type=Path, default=ROOT/"data/himachal/dashboard.sqlite")
    args = p.parse_args()
    # Finish validation and inference before replacing the previous snapshot.
    prepared = assess(read_observations(args.input))
    Store(args.db).replace(prepared)
    print(json.dumps(dict(nodes=len(prepared), source_classes=sorted({n["sourceClass"] for n in prepared}),
        public_alerts=False, accuracy="NOT_EVALUATED", refresh="Dashboard polls every eight seconds")))


if __name__ == "__main__":
    main()

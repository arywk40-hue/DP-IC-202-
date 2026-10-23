#!/usr/bin/env python3
"""Evaluate all saved Mandi candidates without fitting; create a local API replay."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ml.india_mandi.submission import run  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'ml/configs/mandi_modeled_forecast_v1.json')
    parser.add_argument('--output', type=Path, default=ROOT/'ml/reports/submission/2026-10-21')
    parser.add_argument('--replay', type=Path, default=ROOT/'ml/data/himachal/mandi_replay.json')
    args = parser.parse_args()
    result = run(args.config, args.output, args.replay)
    print('MANDI MODELED-DATA TEST — no fitting, no field/hazard accuracy claim')
    for channel, metrics in result['metrics']['active_hybrid'].items():
        print(f'{channel}: MAE={metrics["mae"]:.4f}, RMSE={metrics["rmse"]:.4f}, R2={metrics["r2"]:.4f}; n={metrics["rows"]}')
    print('Dashboard replay:', args.replay)
    print('Report:', args.output/'REPORT.md')


if __name__ == '__main__':
    main()

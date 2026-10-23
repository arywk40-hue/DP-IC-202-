"""Local experimental storm-risk pipeline; no restricted portal downloads."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ml.storm_risk.demo import create_fixture
from ml.storm_risk.pipeline import run_pipeline
from ml.storm_risk.settings import load_config


def main() -> int:
    """Run owner-supplied files or an explicitly synthetic engineering fixture."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['run', 'demo'])
    parser.add_argument('--config', type=Path, default=Path('ml/storm_risk/config/default.yaml'))
    parser.add_argument('--base', type=Path, default=Path.cwd())
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--fixture-dir', type=Path)
    parser.add_argument('--online', action='store_true')
    args = parser.parse_args()
    cfg = load_config(args.config, base=args.base)
    if args.online:
        cfg['online']['enabled'] = True
    if args.stage == 'demo':
        if args.fixture_dir is None:
            parser.error('Demo requires an explicit --fixture-dir in private/ignored storage')
        cfg = create_fixture(cfg, args.fixture_dir)
    directory, report = run_pipeline(cfg, args.run_id)
    print(json.dumps(dict(output=str(directory), status=report['status'], evidence_kind=report['evidence_kind'],
        calibrated=report['calibrated'], gate_failures=report['gate_failures'], warnings=report['warnings'])))
    return 0 if report['status'] == 'COMPLETED_EXPERIMENTAL' else 2


if __name__ == '__main__':
    raise SystemExit(main())

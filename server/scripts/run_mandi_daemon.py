#!/usr/bin/env python3
"""INDRA Autonomous Multi-Day Ingestion Daemon.

Maintains rolling observations without stalling. Automatically fetches latest
hourly ECMWF IFS and CAMS global model-grid observations from Open-Meteo,
appends first-seen entries, updates provenance receipts, and releases locks cleanly.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ml.india_mandi.live import collect as collect_mandi

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s UTC] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("indra.daemon")

SYSTEMD_UNIT_TEMPLATE = """[Unit]
Description=INDRA Continuous Ingestion Daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=indra
Group=indra
WorkingDirectory={working_dir}
ExecStart={python_bin} server/scripts/run_mandi_daemon.py --interval-seconds 3600
Restart=always
RestartSec=30
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""


class IngestionDaemon:
    def __init__(self, data_dir: Path, interval_seconds: int = 3600):
        self.data_dir = data_dir
        self.interval_seconds = max(60, interval_seconds)
        self.running = True

        # Signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        sig_name = signal.Signals(signum).name
        log.info(f"Received signal {sig_name}; shutting down cleanly...")
        self.running = False

    def run_once(self) -> bool:
        log.info(f"Initiating ingestion pass for directory: {self.data_dir}")
        start = time.monotonic()
        try:
            rows, manifest = collect_mandi(self.data_dir)
            elapsed = time.monotonic() - start
            log.info(
                f"Ingestion successful in {elapsed:.2f}s: "
                f"{manifest['rows']} total hours stored, "
                f"+{manifest['new_hours']} new hours added, "
                f"latest_valid_utc={manifest['latest_valid_utc']}"
            )
            return True
        except Exception as exc:
            elapsed = time.monotonic() - start
            log.warning(f"Ingestion pass deferred ({elapsed:.2f}s): {exc}")
            return False

    def run_loop(self):
        log.info(f"Starting INDRA ingestion loop (cadence: {self.interval_seconds}s)")
        consecutive_failures = 0

        while self.running:
            success = self.run_once()
            if success:
                consecutive_failures = 0
                sleep_duration = self.interval_seconds
            else:
                consecutive_failures += 1
                # Exponential backoff capped at 15 minutes
                sleep_duration = min(900, 30 * (2 ** min(consecutive_failures, 5)))
                log.info(f"Backing off for {sleep_duration}s after {consecutive_failures} failure(s)...")

            # Sleep in 1-second chunks to respond quickly to termination signals
            wake_time = time.monotonic() + sleep_duration
            while self.running and time.monotonic() < wake_time:
                time.sleep(1.0)

        log.info("INDRA ingestion daemon terminated cleanly.")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=ROOT / "ml/data/himachal/mandi_current_api_v1",
        help="Target observation cache directory",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=3600,
        help="Cadence between collection cycles in seconds (min: 60)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Execute single ingestion pass and exit immediately (ideal for cron jobs)",
    )
    parser.add_argument(
        "--systemd-unit",
        action="store_true",
        help="Print systemd service unit template to stdout and exit",
    )

    args = parser.parse_args(argv)

    if args.systemd_unit:
        unit = SYSTEMD_UNIT_TEMPLATE.format(
            working_dir=ROOT,
            python_bin=sys.executable,
        )
        print(unit)
        return 0

    daemon = IngestionDaemon(data_dir=args.data_dir, interval_seconds=args.interval_seconds)

    if args.once:
        success = daemon.run_once()
        return 0 if success else 1

    daemon.run_loop()
    return 0


if __name__ == "__main__":
    sys.exit(main())


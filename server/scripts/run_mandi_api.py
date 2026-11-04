"""Build and launch the dashboard using only the live Mandi Open-Meteo feed."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "ui"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--refresh-seconds", type=int, default=900)
    parser.add_argument("--db", type=Path, default=ROOT / "ml/data/himachal/mandi_api.sqlite")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "ml/data/himachal/mandi_current_api_v1")
    parser.add_argument("--forecast-model", type=Path, help="Versioned Mandi six-channel model directory")
    args = parser.parse_args()
    if not (UI / "node_modules/.bin/vite").exists():
        parser.error("Install dependencies first: pip install -r server/requirements.txt; cd ui && npm ci")
    subprocess.run(["npm", "run", "build"], cwd=UI, check=True)
    command = [
        sys.executable, "-m", "server.dashboard",
        "--ui", str(UI / "dist"), "--db", str(args.db),
        "--mandi-data-dir", str(args.data_dir), "--refresh-seconds", str(args.refresh_seconds),
        "--port", str(args.port),
    ]
    if args.forecast_model:
        command += ["--forecast-model", str(args.forecast_model)]
    print(f"Mandi Open-Meteo API → http://127.0.0.1:{args.port}", flush=True)
    try:
        subprocess.run(command, cwd=ROOT, check=True)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

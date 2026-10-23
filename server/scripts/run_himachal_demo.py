"""Start the connected local UI and saved-model backend; no weather API needed."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT/"ui"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--offline", action="store_true", help="No downloads; dependencies must already be installed")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--observations", type=Path, help="Use reviewed native snapshots instead of synthetic demo")
    p.add_argument('--weather-demo',action='store_true',help='Twelve-location synthetic parameter-map and category showcase')
    p.add_argument("--db", type=Path, default=ROOT/"ml/data/himachal/dashboard.sqlite")
    p.add_argument('--online-state',type=Path,help='Persistent delayed-label shadow state')
    p.add_argument('--forecast-model',type=Path,help='Explicit versioned model directory; default is active v2')
    args = p.parse_args()
    if args.weather_demo and args.observations:p.error('Choose imported observations or the synthetic weather demo')
    if not (APP/"node_modules/.bin/vite").exists():
        p.error("Install once: pip install -r server/requirements.txt; cd ui && npm ci")
    subprocess.run(["npm", "run", "build"], cwd=APP, check=True)
    print(f"Open http://127.0.0.1:{args.port} — " + ("IMPORTED OBSERVATIONS" if args.observations else "SYNTHETIC DEMO"), flush=True)
    command = [sys.executable, "-m", "server.dashboard", "--ui", str(APP/"dist"), "--db", str(args.db), "--port", str(args.port)]
    command += ["--observations", str(args.observations)] if args.observations else ['--weather-demo'] if args.weather_demo else ["--demo"]
    if args.online_state: command += ['--online-state',str(args.online_state)]
    if args.forecast_model: command += ['--forecast-model',str(args.forecast_model)]
    try:
        subprocess.run(command, cwd=ROOT, check=True)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

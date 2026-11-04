#!/usr/bin/env python3
"""Unified Production Deployment Script for INDRA Weather Platform.

Builds the optimized frontend, validates the trained ML forecaster,
and launches the FastAPI service serving both API endpoints and UI static assets.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
UI_DIR = ROOT / "ui"
DEFAULT_DB = ROOT / "ml/data/himachal/mandi_api.sqlite"


def build_frontend():
    print("▶ [1/3] Building production frontend with Vite...", flush=True)
    if not (UI_DIR / "node_modules").is_dir():
        print("  Installing UI dependencies (npm ci)...", flush=True)
        subprocess.run(["npm", "ci"], cwd=UI_DIR, check=True)

    result = subprocess.run(["npm", "run", "build"], cwd=UI_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Frontend build failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    dist_dir = UI_DIR / "dist"
    if not (dist_dir / "index.html").is_file():
        print("❌ Error: dist/index.html was not generated.", file=sys.stderr)
        sys.exit(1)
    print("✓ Frontend successfully built into ui/dist", flush=True)


def verify_models(model_dir: Path):
    print("▶ [2/3] Verifying active machine learning models...", flush=True)
    from ml.india_mandi.registry import load_forecaster
    try:
        engine = load_forecaster(model_dir)
        print(f"✓ Loaded forecaster: {engine.profile.get('display_name')} (ID: {engine.profile['id']})", flush=True)
        print(f"  Profile SHA256: {engine.profile_sha256[:16]}...", flush=True)
        print(f"  Active channels: {list(engine.weights.get('heads', {}).keys())}", flush=True)
    except Exception as exc:
        print(f"❌ Failed to load ML model from {model_dir}: {exc}", file=sys.stderr)
        sys.exit(1)


def launch_server(host: str, port: int, db_path: Path, model_dir: Path,
                  data_dir: Path, refresh_seconds: int, enable_demo_auth: bool = False):
    print(f"▶ [3/3] Launching INDRA production gateway on http://{host}:{port}...", flush=True)
    cmd = [
        sys.executable,
        "-m", "server.dashboard",
        "--ui", str(UI_DIR / "dist"),
        "--db", str(db_path),
        "--host", host,
        "--port", str(port),
        "--forecast-model", str(model_dir),
        "--mandi-data-dir", str(data_dir),
        "--refresh-seconds", str(refresh_seconds),
    ]
    if enable_demo_auth:
        cmd.append("--enable-demo-auth")

    print("\n" + "=" * 60)
    print("  🚀 INDRA FORECASTING & OBSERVATION SYSTEM ONLINE")
    print(f"  • Web Dashboard & APIs: http://{host}:{port}")
    print(f"  • API Explorer:         http://{host}:{port}/#apis")
    print(f"  • Google OAuth Config:  http://{host}:{port}/api/auth/config")
    print(f"  • System Status:        http://{host}:{port}/api/status")
    print("=" * 60 + "\n", flush=True)

    try:
        subprocess.run(cmd, cwd=ROOT, check=True)
    except KeyboardInterrupt:
        print("\nGateway stopped by operator.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="Bind locally by default; put hosted deployments behind TLS and an authenticated proxy")
    parser.add_argument("--port", type=int, default=8080, help="Listening port (default: 8080)")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite database path")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "ml/data/himachal/mandi_current_api_v1", help="Rolling Open-Meteo response cache")
    parser.add_argument("--refresh-seconds", type=int, default=900, help="API refresh interval (minimum 60 seconds)")
    parser.add_argument("--model-dir", type=Path, default=ROOT / "ml/models/india_mandi_tabular_v2", help="Model catalog directory")
    parser.add_argument("--enable-demo-auth", action="store_true", help="Enable 1-click demo login for local operator testing (loopback only)")
    parser.add_argument("--skip-build", action="store_true", help="Skip npm run build if dist already exists")
    args = parser.parse_args()

    if args.enable_demo_auth and args.host not in ("127.0.0.1", "::1", "localhost"):
        parser.error("--enable-demo-auth is restricted to loopback addresses (127.0.0.1, ::1)")

    if not args.skip_build or not (UI_DIR / "dist/index.html").exists():
        build_frontend()

    verify_models(args.model_dir)
    if args.refresh_seconds < 60:
        parser.error("Use a refresh interval of at least 60 seconds")
    launch_server(args.host, args.port, args.db, args.model_dir,
                  args.data_dir, args.refresh_seconds, enable_demo_auth=args.enable_demo_auth)


if __name__ == "__main__":
    main()

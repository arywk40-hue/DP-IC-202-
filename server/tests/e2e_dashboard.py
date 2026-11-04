"""Serve Mandi API-shaped test responses; production has no fixture mode."""
import argparse
from pathlib import Path

import uvicorn

from server.dashboard import assess, create_app
from server.tests.mandi_fixture import NOW, mandi_api_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument("--db", type=Path, default=Path("ml/data/himachal/dashboard_e2e.sqlite"))
    args = parser.parse_args()
    app = create_app(args.db, ui_dir=Path("ui/dist"), demo_auth_enabled=True)
    app.state.store.replace(assess(mandi_api_rows(), now=NOW.isoformat()))
    app.state.mandi_feed.update(enabled=True, connected=True, last_success_utc=NOW.isoformat(), latest_valid_utc=NOW.isoformat())
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()

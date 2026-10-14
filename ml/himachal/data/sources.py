"""Reviewed source roles; discovery/access is never a grant of training rights."""
import json
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT = Path(__file__).resolve().parents[3] / "configs/himachal_sources_v1.json"


def load(path=DEFAULT):
    config = json.loads(Path(path).read_text())
    if config.get("schema_version") != "indra_himachal_sources_v1":
        raise ValueError("Unknown source registry")
    if not 1 <= config["limits"]["attempts"] <= 3 or not 1 <= config["limits"]["maximum_bytes"] <= 67108864:
        raise ValueError("Source acquisition resource budget invalid")
    for entry in config["sources"].values():
        if entry["mode"] not in {"http_json", "manual_import"} or not entry["documentation"].startswith("https://"):
            raise ValueError("Unsupported source mode/documentation")
        if entry["mode"] == "http_json":
            endpoint = urlsplit(entry["endpoint"])
            if endpoint.scheme != "https" or endpoint.username or endpoint.password or endpoint.query:
                raise ValueError("Public source endpoint must not contain credentials/query secrets")
    return config

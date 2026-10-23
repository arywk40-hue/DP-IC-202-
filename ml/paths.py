"""Resolve historical config paths without changing checksum-bound settings."""

import json
from pathlib import Path


def relocate(value):
    """Translate old root-relative paths; preserve absolute and external paths."""
    if isinstance(value, dict):
        return {key: relocate(item) for key, item in value.items()}
    if isinstance(value, list):
        return [relocate(item) for item in value]
    if isinstance(value, str):
        prefix = value.split("/", 1)[0]
        if prefix in {"configs", "data", "reports", "outputs", "results", "storm_risk"}:
            return "ml/" + value
    return value


def read_config(path):
    """Load relocated path values while leaving the original file bytes intact."""
    return relocate(json.loads(Path(path).read_text()))

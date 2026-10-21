"""Active gateway selection with explicit, retained legacy loading."""

import json
from pathlib import Path

from ml.india_mandi.hybrid import Hybrid
from ml.india_mandi.tabular_v2 import DEFAULT_MODEL, MODEL_ID, TabularV2

ACTIVE_MODEL = DEFAULT_MODEL
ACTIVE_ID = MODEL_ID


def load_forecaster(directory=ACTIVE_MODEL):
    directory = Path(directory)
    profile = json.loads((directory / "profile.json").read_text())
    if profile.get("schema_version") == "indra_mandi_tabular_profile_v2":
        return TabularV2(directory)
    return Hybrid(directory)

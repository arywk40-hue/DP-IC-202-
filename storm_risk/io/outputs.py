"""JSON-safe reports and owner-generated joblib artifacts."""
from __future__ import annotations

import json
from pathlib import Path
import platform

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost

from storm_risk.settings import digest, snapshot


def clean(value: object) -> object:
    """Replace nonfinite diagnostics with JSON null and serialize UTC clocks."""
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.integer, np.bool_)):
        return value.item()
    if isinstance(value, (pd.Timestamp, Path)):
        return str(value)
    return value


def write_json(path: Path, value: dict) -> None:
    """Write strict JSON with no executable deserialization requirement."""
    path.write_text(json.dumps(clean(value), indent=2, allow_nan=False) + '\n')


def save_bundle(directory: Path, bundle: dict, cfg: dict) -> dict:
    """Save local model/scaler/weights/calibrator/config together with a digest."""
    name = 'ensemble_' + pd.Timestamp(cfg['time']['train_end']).strftime('%Y-%m-%d') + '.joblib'
    artifact = {**bundle, 'config_snapshot': snapshot(cfg), 'software': dict(python=platform.python_version(),
        sklearn=sklearn.__version__, numpy=np.__version__, pandas=pd.__version__, xgboost=xgboost.__version__)}
    joblib.dump(artifact, directory / name, compress=3)
    return dict(file=name, sha256=digest(directory / name), loading='ONLY_TRUST_OWNER_GENERATED_LOCAL_JOBLIB')

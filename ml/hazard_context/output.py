"""Additive research writes: do not overwrite baseline namespaces or prior fits."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PROTECTED=['ml/india_sensor','ml/models','esp32','data/india_sensor','docs/archive']

def protected(p):
    if p.is_relative_to(ROOT/'reports') and not p.is_relative_to(ROOT/'reports/hazard_context_phase'):return True
    return any(p.is_relative_to(ROOT/folder) for folder in PROTECTED) or p in [ROOT/'configs/india_sensor_offline.json',ROOT/'configs/india_sensor_risk.json',ROOT/'data/registry/cds_physics_requests.json']

def new_file(path):
    p=Path(path).resolve()
    if protected(p) or p.exists():raise ValueError('Protected/existing file; choose a new research output path')
    p.parent.mkdir(parents=True,exist_ok=True)
    return p


def fresh_directory(path):
    p=Path(path).resolve()
    if protected(p):raise ValueError('Protected baseline namespace; choose a new research output directory')
    if p.exists() and (not p.is_dir() or any(p.iterdir())):raise ValueError('Existing research output; use a fresh versioned directory')
    p.mkdir(parents=True,exist_ok=True)
    return p

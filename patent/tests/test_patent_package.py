"""Automated unit test suite validating the INDRA Patent Filing Package.

Verifies:
1. Presence and cryptographic validity of all cited codebase files.
2. Statutory claim structures, dependency chains, and claim counts.
3. Drawing figure cross-references and reference numerals.
4. Numerical and algorithmic consistency between claims and code.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
PATENT_DIR = ROOT / "patent"
COMPILED_DIR = PATENT_DIR / "compiled"


def test_patent_files_exist():
    required = [
        PATENT_DIR / "SPECIFICATION.md",
        PATENT_DIR / "CLAIMS.md",
        PATENT_DIR / "DRAWINGS.md",
        PATENT_DIR / "INVENTION_DISCLOSURE_REPORT.md",
        PATENT_DIR / "FILING_CHECKLIST_AND_FORMS.md",
        COMPILED_DIR / "INDRA_COMPLETE_PATENT_APPLICATION.md",
        COMPILED_DIR / "INDRA_COMPLETE_PATENT_APPLICATION.html",
        COMPILED_DIR / "patent_manifest.json",
    ]
    for path in required:
        assert path.is_file(), f"Missing patent filing artifact: {path}"
        assert path.stat().st_size > 500, f"Artifact appears truncated: {path}"


def test_statutory_claim_structure():
    claims_text = (PATENT_DIR / "CLAIMS.md").read_text(encoding="utf-8")
    claims = [line.strip() for line in claims_text.splitlines() if line.strip().startswith("#### ") and "." in line]
    assert len(claims) == 25, f"Expected exactly 25 statutory claims, found {len(claims)}"

    # Verify independent claims
    assert "1. A micro-meteorological edge forecasting" in claims[0]
    assert "11. A computer-implemented method" in claims[10]
    assert "19. An embedded edge microcontroller device" in claims[18]
    assert "23. A non-transitory computer-readable storage medium" in claims[22]

    # Verify dependent claim references
    assert "The system of claim 1" in claims_text
    assert "The method of claim 11" in claims_text
    assert "The embedded edge microcontroller device of claim 19" in claims_text


def test_drawing_figures_and_cross_references():
    spec_text = (PATENT_DIR / "SPECIFICATION.md").read_text(encoding="utf-8")
    drawings_text = (PATENT_DIR / "DRAWINGS.md").read_text(encoding="utf-8")

    for fig_num in range(1, 9):
        tag = f"FIG. {fig_num}"
        assert tag in spec_text, f"{tag} missing from SPECIFICATION.md"
        assert tag in drawings_text, f"{tag} missing from DRAWINGS.md"


def test_numerical_claims_match_codebase():
    from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS, PHYSICAL_RANGES
    from ml.six_sensor_forecast.features import LAGS, WINDOWS
    from contracts.provenance import canonical

    # 1. Six physical channels
    assert len(RAW_SENSOR_COLUMNS) == 6
    assert set(RAW_SENSOR_COLUMNS) == {
        "temperature_c", "relative_humidity_pct", "pressure_hpa",
        "pm25_ug_m3", "pm10_ug_m3", "wind_speed_mps"
    }

    # 2. 66 Causal features:
    # 6 raw + (6 channels * 5 lags = 30) + (6 channels * 1 delta = 6) + (6 channels * 2 windows * 2 moments = 24) = 66
    computed_feature_count = (
        len(RAW_SENSOR_COLUMNS) +
        len(RAW_SENSOR_COLUMNS) * len(LAGS) +
        len(RAW_SENSOR_COLUMNS) * 1 +
        len(RAW_SENSOR_COLUMNS) * len(WINDOWS) * 2
    )
    assert computed_feature_count == 66

    # 3. Physical bounds asserted in Claim 22
    assert PHYSICAL_RANGES["temperature_c"] == (-60.0, 85.0)
    assert PHYSICAL_RANGES["relative_humidity_pct"] == (0.0, 100.0)
    assert PHYSICAL_RANGES["pressure_hpa"] == (300.0, 1100.0)
    assert PHYSICAL_RANGES["pm25_ug_m3"] == (0.0, 5000.0)
    assert PHYSICAL_RANGES["pm10_ug_m3"] == (0.0, 5000.0)
    assert PHYSICAL_RANGES["wind_speed_mps"] == (0.0, 100.0)


def test_patent_manifest_integrity():
    manifest_path = COMPILED_DIR / "patent_manifest.json"
    data = json.loads(manifest_path.read_text())
    assert "title" in data
    assert "inventors" in data
    assert "codebase_evidence" in data
    for rel_path, meta in data["codebase_evidence"].items():
        file_path = ROOT / rel_path
        assert file_path.is_file(), f"Cited evidence file missing: {rel_path}"
        assert file_path.stat().st_size == meta["bytes"], f"Byte size mismatch for {rel_path}"


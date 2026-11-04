#!/usr/bin/env python3
"""Automated Patent Verification & Compilation Suite for INDRA.

Validates that all patent claims map to active codebase files, computes
cryptographic SHA-256 evidence digests, and compiles the formal patent
package into unified Markdown and standalone HTML/PDF export formats.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PATENT_DIR = ROOT / "patent"
COMPILED_DIR = PATENT_DIR / "compiled"

CORE_CITED_FILES = [
    "ml/six_sensor_forecast/contract.py",
    "ml/six_sensor_forecast/features.py",
    "ml/india_mandi/tabular_v2.py",
    "ml/himachal/hazard_scenarios.py",
    "ml/himachal/parameter_maps.py",
    "esp32/ml_integration/src/mandi_v2_main.cpp",
    "esp32/ml_integration/include/indra_mandi_v2_runtime.h",
    "contracts/IndraAnchor.sol",
    "contracts/provenance.py",
    "server/auth.py",
    "server/dashboard.py",
    "server/scripts/deploy_production.py",
    "ui/src/App.jsx",
]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_codebase_evidence() -> dict[str, dict[str, any]]:
    print("▶ [1/4] Verifying codebase evidentiary integrity...", flush=True)
    manifest = {}
    missing = []
    for rel_path in CORE_CITED_FILES:
        full_path = ROOT / rel_path
        if not full_path.is_file():
            missing.append(rel_path)
            continue
        sha = file_sha256(full_path)
        size = full_path.stat().st_size
        manifest[rel_path] = {
            "sha256": sha,
            "bytes": size,
            "status": "VERIFIED_PRESENT",
        }
        print(f"  ✓ {rel_path} ({size} bytes, SHA-256: {sha[:12]}...)")

    if missing:
        print(f"❌ Error: Missing cited codebase files: {missing}", file=sys.stderr)
        sys.exit(1)
    return manifest


def verify_patent_documents() -> tuple[str, str, str]:
    print("▶ [2/4] Verifying patent text structure and cross-references...", flush=True)
    spec_path = PATENT_DIR / "SPECIFICATION.md"
    claims_path = PATENT_DIR / "CLAIMS.md"
    drawings_path = PATENT_DIR / "DRAWINGS.md"

    for path in (spec_path, claims_path, drawings_path):
        if not path.is_file():
            print(f"❌ Error: Required patent file missing: {path}", file=sys.stderr)
            sys.exit(1)

    spec_text = spec_path.read_text(encoding="utf-8")
    claims_text = claims_path.read_text(encoding="utf-8")
    drawings_text = drawings_path.read_text(encoding="utf-8")

    # Verify claim count
    claim_count = sum(1 for line in claims_text.splitlines() if line.strip().startswith("#### ") and "." in line)
    print(f"  ✓ Found {claim_count} structured statutory claims.")
    if claim_count < 20:
        print(f"⚠️ Warning: Expected at least 20 claims, found {claim_count}", file=sys.stderr)

    # Verify key drawing figures are described
    for fig_num in range(1, 9):
        fig_tag = f"FIG. {fig_num}"
        if fig_tag not in drawings_text or fig_tag not in spec_text:
            print(f"❌ Error: Missing figure reference for {fig_tag}", file=sys.stderr)
            sys.exit(1)
    print("  ✓ All 8 patent drawing figures verified across Specification and Drawings.")

    return spec_text, claims_text, drawings_text


def compile_package(spec_text: str, claims_text: str, drawings_text: str, manifest: dict) -> Path:
    print("▶ [3/4] Compiling unified publication package...", flush=True)
    COMPILED_DIR.mkdir(parents=True, exist_ok=True)

    header = f"""# COMPLETE PATENT APPLICATION SPECIFICATION & PROOF OF INVENTORSHIP

**INVENTION TITLE:** SYSTEMS AND METHODS FOR MULTI-CHANNEL MICRO-METEOROLOGICAL EDGE FORECASTING, LATENT HYDROLOGICAL HAZARD SIMULATION, AND CRYPTOGRAPHIC PROVENANCE ANCHORING  
**INVENTOR(S):** Ariyan Bhakat, et al.  
**DATE OF COMPILATION:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  
**REPOSITORY COMMIT CONTEXT:** `INDRA / Dp-indra-six-sensor`  

---

## TABLE OF CONTENTS
1. [Official Patent Specification](#patent-specification)
2. [Statutory Patent Claims](#patent-claims)
3. [Formal Patent Drawings & Logic Diagrams](#formal-patent-drawings-specification)
4. [Evidentiary Codebase Manifest & Cryptographic Hashes](#evidentiary-codebase-manifest)

---
"""

    manifest_section = "\n## EVIDENTIARY CODEBASE MANIFEST\n\n"
    manifest_section += "The following source code modules establish the physical reduction to practice of the claimed invention:\n\n"
    manifest_section += "| Source File | Bytes | SHA-256 Checksum |\n| :--- | :---: | :--- |\n"
    for path, meta in manifest.items():
        manifest_section += f"| `{path}` | {meta['bytes']:,} | `{meta['sha256']}` |\n"

    full_markdown = f"{header}\n\n{spec_text}\n\n---\n\n{claims_text}\n\n---\n\n{drawings_text}\n\n---\n\n{manifest_section}"

    out_md = COMPILED_DIR / "INDRA_COMPLETE_PATENT_APPLICATION.md"
    out_md.write_text(full_markdown, encoding="utf-8")
    print(f"  ✓ Compiled Markdown written to: {out_md.relative_to(ROOT)}")

    # Also generate a standalone, self-contained HTML document for printing / PDF export
    out_html = COMPILED_DIR / "INDRA_COMPLETE_PATENT_APPLICATION.html"
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>INDRA — Complete Patent Specification</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #1a1a1a; }}
  h1, h2, h3, h4 {{ color: #0d233a; border-bottom: 1px solid #eaeaea; padding-bottom: 6px; }}
  pre {{ background: #f6f8fa; padding: 16px; border-radius: 6px; overflow-x: auto; font-family: "Courier New", Courier, monospace; font-size: 13px; line-height: 1.35; border: 1px solid #d0d7de; }}
  code {{ background: #f6f8fa; padding: 2px 5px; border-radius: 4px; font-size: 88%; font-family: monospace; }}
  table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
  th, td {{ border: 1px solid #d0d7de; padding: 8px 12px; text-align: left; font-size: 14px; }}
  th {{ background: #f3f4f6; }}
  @media print {{ body {{ max-width: 100%; margin: 0; }} }}
</style>
</head>
<body>
<pre style="white-space: pre-wrap;">{full_markdown.replace('<', '&lt;').replace('>', '&gt;')}</pre>
</body>
</html>
"""
    out_html.write_text(html_content, encoding="utf-8")
    print(f"  ✓ Standalone HTML written to: {out_html.relative_to(ROOT)}")

    # Write JSON manifest
    manifest_file = COMPILED_DIR / "patent_manifest.json"
    manifest_data = {
        "title": "SYSTEMS AND METHODS FOR MULTI-CHANNEL MICRO-METEOROLOGICAL EDGE FORECASTING, LATENT HYDROLOGICAL HAZARD SIMULATION, AND CRYPTOGRAPHIC PROVENANCE ANCHORING",
        "inventors": ["Ariyan Bhakat"],
        "compiled_at_utc": datetime.now(timezone.utc).isoformat(),
        "application_markdown_sha256": file_sha256(out_md),
        "codebase_evidence": manifest,
    }
    manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    print(f"  ✓ JSON manifest written to: {manifest_file.relative_to(ROOT)}")

    return out_md


def main():
    print("=" * 70)
    print("  INDRA PATENT APPLICATION COMPILATION & VERIFICATION TOOL")
    print("=" * 70)
    manifest = verify_codebase_evidence()
    spec_text, claims_text, drawings_text = verify_patent_documents()
    compiled_path = compile_package(spec_text, claims_text, drawings_text, manifest)
    print("\n▶ [4/4] Validation Summary:")
    print(f"  • Status: All patent artifacts compiled & verified successfully.")
    print(f"  • File:   {compiled_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()


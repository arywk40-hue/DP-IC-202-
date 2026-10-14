"""Committed model/header verification; synthetic inputs, never field skill."""
import json
import tempfile
import unittest
from pathlib import Path

from ml.deployment.verify_exports import verify, verify_identities

ROOT = Path(__file__).resolve().parents[1]


class CommittedExportTests(unittest.TestCase):
    def test_all_committed_headers_compile_reproduce_and_match_frozen_weights(self):
        receipt = verify(Path("configs/model_catalog.json"))
        self.assertEqual(len(receipt["profiles"]), 6)
        self.assertFalse(receipt["hardware_execution_verified"])
        self.assertFalse(receipt["weather_accuracy_evaluated"])
        for profile in receipt["profiles"].values():
            self.assertEqual(profile["status"], "PASSED")
            self.assertGreater(profile["split_thresholds"], 0)
        self.assertIn("mandi_modeled_6h_v1", receipt["profiles"])

    def test_each_header_weight_and_report_tamper_is_rejected_before_compilation(self):
        original = json.loads((ROOT / "configs/committed_exports_v1.json").read_text())
        # Exercise every protected file independently in a miniature root; do
        # not change the real model artifacts even temporarily.
        for relative, expected in original["files"].items():
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                path = root / relative
                path.parent.mkdir(parents=True)
                path.write_bytes((ROOT / relative).read_bytes() + b"TAMPER")
                manifest = {**original, "files": {relative: expected}}
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    verify_identities(root, manifest)

    def test_unknown_schema_missing_and_escaping_paths_fail(self):
        manifest = {"schema_version": "wrong", "files": {}}
        with self.assertRaisesRegex(ValueError, "schema"):
            verify_identities(ROOT, manifest)
        manifest["schema_version"] = "indra_committed_exports_v1"
        for path in ("does_not_exist.h", "../../escape.h"):
            with self.subTest(path=path):
                manifest["files"] = {path: "0" * 64}
                with self.assertRaisesRegex(ValueError, "Missing or unsafe"):
                    verify_identities(ROOT, manifest)

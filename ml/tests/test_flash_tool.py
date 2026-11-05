"""Unit tests for the INDRA ESP32-S3 Hardware Flasher Tool."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from esp32.tools.flash_esp32 import detect_serial_ports, main, ENV_DIRECTORY_MAP


def test_environment_directory_mapping_exists():
    root = Path(__file__).resolve().parents[2]
    for env_name, (sub_dir, target_env) in ENV_DIRECTORY_MAP.items():
        project_dir = root / sub_dir
        assert project_dir.exists(), f"Project dir {project_dir} for {env_name} must exist."
        assert (project_dir / "platformio.ini").exists(), f"platformio.ini in {project_dir} must exist."


def test_flash_tool_dry_run_generates_json_receipt(tmp_path):
    report_file = tmp_path / "receipt.json"
    ret = main(["--dry-run", "--env", "esp32-s3-mandi-v2", "--output", str(report_file)])
    assert ret == 0
    assert report_file.exists()
    data = json.loads(report_file.read_text())
    assert data["status"] == "DRY_RUN_PASSED"
    assert data["environment"] == "esp32-s3-mandi-v2"
    assert "detected_ports" in data


def test_detect_serial_ports_fallback():
    with patch("shutil.which", return_value=None):
        ports = detect_serial_ports()
        assert isinstance(ports, list)


def test_invalid_environment_rejected():
    with pytest.raises(SystemExit):
        main(["--env", "non_existent_env"])

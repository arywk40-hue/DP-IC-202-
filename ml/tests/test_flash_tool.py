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


def test_flash_tool_role_resolution(tmp_path):
    report_master = tmp_path / "master.json"
    ret = main(["--dry-run", "--role", "master", "--node-id", "0", "--output", str(report_master)])
    assert ret == 0
    data = json.loads(report_master.read_text())
    assert data["environment"] == "mesh-master"
    assert data["role"] == "master"
    assert data["node_id"] == 0

    report_slave = tmp_path / "slave.json"
    ret = main(["--dry-run", "--role", "slave", "--node-id", "2", "--output", str(report_slave)])
    assert ret == 0
    data = json.loads(report_slave.read_text())
    assert data["environment"] == "mesh-slave"
    assert data["role"] == "slave"
    assert data["node_id"] == 2


def test_invalid_environment_rejected():
    with pytest.raises(SystemExit):
        main(["--env", "non_existent_env"])



def test_every_mapped_environment_is_defined_in_its_platformio_ini():
    """Regression: slave/mesh roles used to point at env names that did not exist."""
    import configparser
    root = Path(__file__).resolve().parents[2]
    for env_name, (sub_dir, target_env) in ENV_DIRECTORY_MAP.items():
        ini = configparser.ConfigParser(interpolation=None)
        ini.read(root / sub_dir / "platformio.ini")
        assert f"env:{target_env}" in ini.sections(), f"{env_name}: env:{target_env} missing in {sub_dir}"


def test_node_id_is_baked_into_build_flags():
    from types import SimpleNamespace
    from esp32.tools.flash_esp32 import build_environment, node_name_for
    assert node_name_for(SimpleNamespace(node_id=2, node_name=None)) == "indra-node-02"
    assert node_name_for(SimpleNamespace(node_id=2, node_name="ridge-01")) == "ridge-01"
    env = build_environment("ridge-01")
    assert '-DINDRA_NODE_ID=\\"ridge-01\\"' in env["PLATFORMIO_BUILD_FLAGS"]

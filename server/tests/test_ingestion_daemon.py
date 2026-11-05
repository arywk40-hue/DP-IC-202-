"""Unit tests for the autonomous ingestion daemon."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from server.scripts.run_mandi_daemon import IngestionDaemon, main


def test_daemon_systemd_unit_output(capsys):
    ret = main(["--systemd-unit"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Description=INDRA Continuous Ingestion Daemon" in captured.out
    assert "Restart=always" in captured.out


def test_daemon_run_once_success(tmp_path):
    mock_manifest = {
        "rows": 188,
        "new_hours": 1,
        "latest_valid_utc": "2026-11-05T01:00:00Z",
    }
    with patch("server.scripts.run_mandi_daemon.collect_mandi", return_value=([], mock_manifest)):
        daemon = IngestionDaemon(data_dir=tmp_path)
        success = daemon.run_once()
        assert success is True


def test_daemon_run_once_failure(tmp_path):
    with patch("server.scripts.run_mandi_daemon.collect_mandi", side_effect=RuntimeError("Network timeout")):
        daemon = IngestionDaemon(data_dir=tmp_path)
        success = daemon.run_once()
        assert success is False


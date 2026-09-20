import os
import pytest
from unittest.mock import patch
from engine import MonitorEngine

def test_persistent_logging_directory_and_file_created(tmp_path, mock_registry):
    custom_log_dir = str(tmp_path / "test_logs_folder")
    assert not os.path.exists(custom_log_dir)

    engine = MonitorEngine(channel_registry=mock_registry, log_dir=custom_log_dir)
    try:
        # Directory must be automatically created
        assert os.path.exists(custom_log_dir)
        log_file = os.path.join(custom_log_dir, "sentinel.log")
        assert os.path.exists(log_file)

        # Log several messages across levels
        engine.log("System startup initiated", level="info")
        engine.log("Drive space running low", level="warning")
        engine.log("Connection failure detected", level="error")

        # Flush / verify file content
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()

        assert "[INFO] System startup initiated" in content
        assert "[WARNING] Drive space running low" in content
        assert "[ERROR] Connection failure detected" in content

        # Verify in-memory buffer also contains all 3 entries
        assert len(engine.logs) == 3
        assert engine.logs[0]["message"] == "System startup initiated"
        assert engine.logs[1]["message"] == "Drive space running low"
        assert engine.logs[2]["message"] == "Connection failure detected"
    finally:
        engine.close()


def test_default_logging_relative_to_app_directory(tmp_path, mock_registry):
    with patch("engine.get_app_directory", return_value=str(tmp_path)):
        engine = MonitorEngine(channel_registry=mock_registry)
        try:
            expected_log_dir = tmp_path / "logs"
            expected_log_file = expected_log_dir / "sentinel.log"

            assert expected_log_dir.exists()
            assert expected_log_file.exists()

            engine.log("Testing app directory relative logging", level="info")

            with open(str(expected_log_file), "r", encoding="utf-8") as f:
                content = f.read()

            assert "Testing app directory relative logging" in content
        finally:
            engine.close()

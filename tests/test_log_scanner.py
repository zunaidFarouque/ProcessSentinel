import os
import pytest
from unittest.mock import MagicMock, patch
from monitors.log_scanner import LogScannerMonitor

def test_log_scanner_new_appended_lines(tmp_path, mock_registry):
    log_file = tmp_path / "service.log"
    log_file.write_text("2026-09-20 10:00:00 [INFO] Service started successfully\n")

    mon = LogScannerMonitor(
        name="Service Watcher",
        file_path=str(log_file),
        patterns=["ERROR", "FATAL"]
    )

    # First check: establish baseline at EOF
    mon.check(None, mock_registry)
    assert mon.status_level == "ok"
    assert len(mock_registry.sent_alerts) == 0

    # Append non-matching line
    with open(log_file, "a") as f:
        f.write("2026-09-20 10:01:00 [INFO] Health check passed\n")

    mon.check(None, mock_registry)
    assert mon.status_level == "ok"
    assert len(mock_registry.sent_alerts) == 0

    # Append matching line
    with open(log_file, "a") as f:
        f.write("2026-09-20 10:02:00 [ERROR] Failed to establish DB connection\n")

    mon.check(None, mock_registry)
    assert mon.status_level == "warning"
    assert len(mock_registry.sent_alerts) == 1
    alert = mock_registry.sent_alerts[0]
    assert "Failed to establish DB connection" in alert["message"]
    assert "ERROR" in alert["message"] or "service.log" in alert["message"]

def test_log_scanner_regex_and_case_sensitivity(tmp_path, mock_registry):
    log_file = tmp_path / "app.log"
    log_file.write_text("initial\n")

    # 1. Regex test
    mon_regex = LogScannerMonitor(
        name="Regex Scanner",
        file_path=str(log_file),
        patterns=[r"HTTP/\d\.\d\s+5\d{2}"],
        is_regex=True
    )
    mon_regex.check(None, mock_registry)

    with open(log_file, "a") as f:
        f.write("GET /api 200 OK\n")
    mon_regex.check(None, mock_registry)
    assert len(mock_registry.sent_alerts) == 0

    with open(log_file, "a") as f:
        f.write("POST /checkout HTTP/1.1 503 Service Unavailable\n")
    mon_regex.check(None, mock_registry)
    assert len(mock_registry.sent_alerts) == 1
    assert "503" in mock_registry.sent_alerts[0]["message"]

    # 2. Case sensitivity test
    mock_registry.sent_alerts.clear()
    mon_case = LogScannerMonitor(
        name="Case Scanner",
        file_path=str(log_file),
        patterns=["CRITICAL"],
        case_sensitive=True
    )
    mon_case.check(None, mock_registry)

    with open(log_file, "a") as f:
        f.write("a lowercase critical message\n")
    mon_case.check(None, mock_registry)
    assert len(mock_registry.sent_alerts) == 0

    with open(log_file, "a") as f:
        f.write("an uppercase CRITICAL message\n")
    mon_case.check(None, mock_registry)
    assert len(mock_registry.sent_alerts) == 1

def test_log_scanner_log_rotation_detection(tmp_path, mock_registry):
    log_file = tmp_path / "rotated.log"
    # Write initial large log
    log_file.write_text("A" * 5000 + "\n")

    mon = LogScannerMonitor(
        name="Rotation Scanner",
        file_path=str(log_file),
        patterns=["PANIC"]
    )
    mon.check(None, mock_registry)
    assert mon.last_file_pos > 5000

    # Simulate log rotation (file truncated / replaced with fresh small file)
    log_file.write_text("PANIC: Kernel module missing\n")

    mon.check(None, mock_registry)
    # File shrunk, rotation detected, scanned from beginning
    assert len(mock_registry.sent_alerts) == 1
    assert "PANIC" in mock_registry.sent_alerts[0]["message"]

def test_log_scanner_file_missing(mock_registry):
    mon = LogScannerMonitor(
        name="Missing File",
        file_path="C:\\nonexistent_log_dir\\missing.log",
        patterns=["ERROR"]
    )
    mon.check(None, mock_registry)
    assert mon.status_level == "warning"
    assert "File not found" in mon.status_text
    assert len(mock_registry.sent_alerts) == 0

def test_log_scanner_trigger_action(tmp_path, mock_registry):
    log_file = tmp_path / "action.log"
    log_file.write_text("init\n")

    mon = LogScannerMonitor(
        name="Action Scanner",
        file_path=str(log_file),
        patterns=["EMERGENCY"],
        action_command="pager.bat"
    )
    mon.check(None, mock_registry)

    engine = MagicMock()
    with patch.object(mon, "execute_trigger_action") as mock_action:
        with open(log_file, "a") as f:
            f.write("EMERGENCY system shutdown requested\n")
        mon.check(engine, mock_registry)
        mock_action.assert_called_once_with(engine)

def test_log_scanner_reset_state(tmp_path):
    log_file = tmp_path / "state.log"
    log_file.write_text("line 1\nline 2\n")

    mon = LogScannerMonitor(
        name="State Scanner",
        file_path=str(log_file),
        patterns=["WARN"]
    )
    mon.check(None, None)
    mon.alerted = True

    mon.reset_state()
    assert mon.alerted is False
    assert mon.status_level == "idle"
    assert mon.status_text == "State Reset"

def test_log_scanner_serialization(tmp_path):
    log_file = str(tmp_path / "ser.log")
    mon = LogScannerMonitor(
        name="SerLog",
        file_path=log_file,
        patterns=["ERR", "FATAL"],
        is_regex=True,
        case_sensitive=True,
        action_command="cleanup.bat",
        action_timeout=40
    )

    d = mon.to_dict()
    assert d["type"] == "LogScanner"
    assert d["file_path"] == log_file
    assert d["patterns"] == ["ERR", "FATAL"]
    assert d["is_regex"] is True
    assert d["case_sensitive"] is True
    assert d["action_command"] == "cleanup.bat"
    assert d["action_timeout"] == 40

    loaded = LogScannerMonitor.from_dict(d)
    assert loaded.name == "SerLog"
    assert loaded.file_path == log_file
    assert loaded.patterns == ["ERR", "FATAL"]
    assert loaded.is_regex is True
    assert loaded.case_sensitive is True
    assert loaded.action_command == "cleanup.bat"
    assert loaded.action_timeout == 40

import pytest
from unittest.mock import patch, MagicMock
from monitors.network import HTTPEndpointMonitor, LocalPortMonitor
from monitors.process import ProcessInstanceMonitor
from monitors.resource import ResourceMonitor
from monitors.base import BaseMonitor

def test_http_endpoint_recovery_alert(mock_registry):
    mon = HTTPEndpointMonitor(
        name="API Monitor",
        url="http://localhost:8080/health",
        expected_status=200,
        recovery_notification=True,
        recovery_message="API service is fully operational again!"
    )

    # 1. First check: Server returns 500 -> Triggers alert
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 500
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 1
        assert mon.alerted is True
        assert mock_registry.sent_alerts[0]["priority"] == 4

    # 2. Second check: Server still 500 -> Debounced, no new alert
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 500
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 1

    # 3. Third check: Server recovers to 200 -> Recovery alert fires!
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 2
        recovery_alert = mock_registry.sent_alerts[-1]
        assert recovery_alert["priority"] == 3
        assert "white_check_mark,recycle" in recovery_alert["tags"]
        assert "API service is fully operational again!" in recovery_alert["message"]
        assert mon.alerted is False

    # 4. Fourth check: Server still 200 -> No duplicate recovery alert
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 2

    # 5. Verify recovery_notification=False sends no recovery alert
    mon_no_rec = HTTPEndpointMonitor(
        name="Silent API",
        url="http://localhost:8080/health",
        expected_status=200,
        recovery_notification=False
    )
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 500
        mon_no_rec.check(None, mock_registry)
        assert mon_no_rec.alerted is True
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mon_no_rec.check(None, mock_registry)
        assert mon_no_rec.alerted is False
        # Alert count should not have increased beyond the 1 initial failure alert
        assert len(mock_registry.sent_alerts) == 3


def test_local_port_recovery_alert(mock_registry):
    mon = LocalPortMonitor(
        name="Postgres DB",
        port=5432,
        host="127.0.0.1",
        recovery_notification=True
    )

    # 1. Port down -> Alerts
    with patch("socket.socket.connect", side_effect=ConnectionRefusedError("Connection refused")):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 1
        assert mon.alerted is True

    # 2. Port recovers -> Recovery alert sent exactly once
    with patch("socket.socket.connect", return_value=None):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 2
        recovery_alert = mock_registry.sent_alerts[-1]
        assert recovery_alert["priority"] == 3
        assert "white_check_mark,recycle" in recovery_alert["tags"]
        assert "5432" in recovery_alert["message"]
        assert mon.alerted is False

    # 3. Subsequent OK checks do not duplicate alert
    with patch("socket.socket.connect", return_value=None):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 2


def test_process_instance_recovery_alert(mock_registry):
    mon = ProcessInstanceMonitor(
        name="Worker Daemon",
        target="worker.exe",
        condition="below",
        threshold=2,
        recovery_notification=True
    )

    # 1. Count drops to 0 (< 2) -> Triggers alert
    with patch.object(mon, "_get_current_count", return_value=0):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 1
        assert mon.alerted is True

    # 2. Count recovers to 3 (>= 2) -> Recovery alert fires exactly once
    with patch.object(mon, "_get_current_count", return_value=3):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 2
        recovery_alert = mock_registry.sent_alerts[-1]
        assert recovery_alert["priority"] == 3
        assert "white_check_mark,recycle" in recovery_alert["tags"]
        assert "worker.exe" in recovery_alert["message"]
        assert mon.alerted is False

    # 3. Subsequent check at 3 -> No duplicate
    with patch.object(mon, "_get_current_count", return_value=3):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 2


def test_resource_monitor_recovery_alert(mock_registry):
    mon = ResourceMonitor(
        name="RAM Sentinel",
        target="heavy_task.exe",
        metric="ram_mb",
        condition="above",
        threshold=1000.0,
        recovery_notification=True
    )

    fake_proc = MagicMock()
    fake_proc.info = {"name": "heavy_task.exe"}
    fake_proc.cpu_percent.return_value = 10.0
    mem_info = MagicMock()
    fake_proc.memory_info.return_value = mem_info

    # 1. High RAM (1500 MB) -> Alerts
    mem_info.rss = int(1500 * 1024 * 1024)
    with patch("psutil.process_iter", return_value=[fake_proc]):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 1
        assert mon.alerted is True

    # 2. RAM drops to normal (400 MB) -> Recovery alert fires exactly once
    mem_info.rss = int(400 * 1024 * 1024)
    with patch("psutil.process_iter", return_value=[fake_proc]):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 2
        recovery_alert = mock_registry.sent_alerts[-1]
        assert recovery_alert["priority"] == 3
        assert "white_check_mark,recycle" in recovery_alert["tags"]
        assert "heavy_task.exe" in recovery_alert["message"]
        assert mon.alerted is False

    # 3. Subsequent check with normal RAM -> No duplicate alert
    with patch("psutil.process_iter", return_value=[fake_proc]):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 2


def test_base_monitor_recovery_serialization():
    mon = HTTPEndpointMonitor(
        name="SerTest",
        url="http://localhost:5000",
        recovery_notification=True,
        recovery_message="Resolved automatically"
    )
    d = mon.to_dict()
    assert d["recovery_notification"] is True
    assert d["recovery_message"] == "Resolved automatically"

    loaded = HTTPEndpointMonitor.from_dict(d)
    assert loaded.recovery_notification is True
    assert loaded.recovery_message == "Resolved automatically"

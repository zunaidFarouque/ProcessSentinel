import pytest
from unittest.mock import patch, MagicMock

from channels import NotificationChannel, ChannelRegistry
from monitors import create_monitor_from_dict
from monitors.process import ProcessStepDownMonitor, ProcessInstanceMonitor
from monitors.storage import StorageMultiTierMonitor, DirectorySizeMonitor
from monitors.io_heartbeat import IOMonitor
from monitors.resource import ResourceMonitor
from monitors.network import HTTPEndpointMonitor, LocalPortMonitor

def test_channel_send_headers_with_auth_and_customization():
    channel = NotificationChannel(
        name="Private Lab",
        url="https://ntfy.internal.net/alerts",
        auth_token="tk_secret_token_123"
    )

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        ok = channel.send(
            message="Test message",
            title="Custom Title",
            tags="rotating_light,skull",
            priority=5,
            click_url="https://grafana.internal.net",
            markdown=True,
            actions="action=view, Open Dashboard, https://grafana.internal.net"
        )

        assert ok is True
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        headers = kwargs.get("headers", {})

        assert headers.get("Title") == "Custom Title"
        assert headers.get("Priority") == "5"
        assert headers.get("Tags") == "rotating_light,skull"
        assert headers.get("Click") == "https://grafana.internal.net"
        assert headers.get("Markdown") == "yes"
        assert headers.get("Authorization") == "Bearer tk_secret_token_123"
        assert headers.get("Actions") == "action=view, Open Dashboard, https://grafana.internal.net"


def test_channel_send_without_auth_header():
    channel = NotificationChannel(name="Public Phone", url="https://ntfy.sh/my_topic")

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        channel.send(message="Simple message")
        _, kwargs = mock_post.call_args
        headers = kwargs.get("headers", {})
        assert "Authorization" not in headers


def test_channel_registry_token_roundtrip():
    reg = ChannelRegistry()
    ch = reg.add_channel(name="IT Secured", url="https://ntfy.sh/private_it", auth_token="tk_999")
    assert ch.auth_token == "tk_999"

    data = reg.to_dict()
    loaded_reg = ChannelRegistry.from_dict(data)
    loaded_ch = loaded_reg.get_channel(ch.id)
    assert loaded_ch.auth_token == "tk_999"


def test_process_step_down_custom_notification(mock_registry):
    mon = ProcessStepDownMonitor(
        name="ArcGIS Batch",
        target="ArcGISPro.exe",
        initial_count=2,
        priority=5,
        tags="fire,skull",
        title_template="[EMERGENCY] {name} Died",
        click_url="https://runbook.internal/arcgis",
        step_down_priority=3,
        step_down_tags="warning"
    )

    # Step down: 2 -> 1
    mon._get_current_count = lambda: 1
    mon.check(None, mock_registry)
    assert len(mock_registry.sent_alerts) == 1
    a1 = mock_registry.sent_alerts[0]
    assert a1["priority"] == 3
    assert a1["tags"] == "warning"
    assert a1["click_url"] == "https://runbook.internal/arcgis"
    assert a1["markdown"] is True

    # Critical: 1 -> 0
    mon._get_current_count = lambda: 0
    mon.check(None, mock_registry)
    assert len(mock_registry.sent_alerts) == 2
    a2 = mock_registry.sent_alerts[1]
    assert a2["priority"] == 5
    assert a2["tags"] == "fire,skull"
    assert a2["title"] == "[EMERGENCY] ArcGIS Batch Died"


def test_process_instance_custom_notification(mock_registry):
    mon = ProcessInstanceMonitor(
        name="Worker Check",
        target="worker.exe",
        condition="below",
        threshold=2,
        priority=5,
        tags="skull",
        title_template="Worker alert for {target}",
        click_url="http://localhost:8080"
    )

    mon._get_current_count = lambda: 1
    mon.check(None, mock_registry)
    assert len(mock_registry.sent_alerts) == 1
    alert = mock_registry.sent_alerts[0]
    assert alert["priority"] == 5
    assert alert["tags"] == "skull"
    assert alert["title"] == "Worker alert for worker.exe"
    assert alert["click_url"] == "http://localhost:8080"


def test_io_heartbeat_custom_notification(mock_registry, tmp_path):
    mon = IOMonitor(
        name="Data Stream",
        paths=[str(tmp_path)],
        stall_minutes=1.0,
        priority=2,
        tags="hourglass_done",
        title_template="Stall Warning: {name}"
    )

    # Create dummy file with old timestamp
    dummy = tmp_path / "data.csv"
    dummy.write_text("sample")
    import os, time
    old_time = time.time() - 120
    os.utime(dummy, (old_time, old_time))

    mon.check(None, mock_registry)
    assert len(mock_registry.sent_alerts) == 1
    alert = mock_registry.sent_alerts[0]
    assert alert["priority"] == 2
    assert alert["tags"] == "hourglass_done"
    assert alert["title"] == "Stall Warning: Data Stream"


def test_backward_compatibility_deserialization():
    """Verify loading legacy JSON without new notification keys doesn't fail."""
    legacy_data = {
        "id": "mon-legacy-1",
        "type": "ProcessStepDown",
        "name": "Legacy Rule",
        "target": "legacy.exe",
        "initial_count": 1,
        "interval_seconds": 30,
        "channel_id": None,
        "enabled": True
    }

    mon = create_monitor_from_dict(legacy_data)
    assert mon is not None
    assert mon.priority == 5
    assert mon.tags == "skull,rotating_light"
    assert mon.title_template is None
    assert mon.click_url is None
    assert mon.markdown_enabled is True
    assert mon.step_down_priority == 4

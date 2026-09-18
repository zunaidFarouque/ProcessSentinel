import pytest
from monitors.process import ProcessStepDownMonitor

def test_step_down_state_machine(mock_registry):
    """
    Validates the exact user workflow specification:
      - Initial count: 3
      - 3 -> 2: Send 1 notification
      - 2 -> 3: No notification
      - 3 -> 2 again: NO duplicate notification
      - 2 -> 1: Send 1 notification
      - 1 -> 3: No notification
      - 3 -> 2 again: No notification
      - 2 -> 1 again: No notification
      - 1 -> 0: Critical notification (different message and skull tag)
    """
    mon = ProcessStepDownMonitor(
        name="ArcGIS Batch",
        target="ArcGISPro.exe",
        initial_count=3,
        step_down_message="Window count dropped to {count}",
        critical_message="CRITICAL: All {target} closed!"
    )

    # Initial state (3 windows)
    mon._get_current_count = lambda: 3
    mon.check(None, mock_registry)
    assert len(mock_registry.sent_alerts) == 0
    assert mon.status_level == "ok"

    # Step down: 3 -> 2
    mon._get_current_count = lambda: 2
    mon.check(None, mock_registry)
    assert len(mock_registry.sent_alerts) == 1
    assert "dropped to 2" in mock_registry.sent_alerts[-1]["message"]
    assert mon.status_level == "warning"

    # User reopens window: 2 -> 3
    mon._get_current_count = lambda: 3
    mon.check(None, mock_registry)
    assert len(mock_registry.sent_alerts) == 1 # Still only 1 alert

    # Window drops again: 3 -> 2
    mon._get_current_count = lambda: 2
    mon.check(None, mock_registry)
    assert len(mock_registry.sent_alerts) == 1 # NO duplicate alert!

    # Step down: 2 -> 1
    mon._get_current_count = lambda: 1
    mon.check(None, mock_registry)
    assert len(mock_registry.sent_alerts) == 2
    assert "dropped to 1" in mock_registry.sent_alerts[-1]["message"]

    # Drops to 0: Critical alert
    mon._get_current_count = lambda: 0
    mon.check(None, mock_registry)
    assert len(mock_registry.sent_alerts) == 3
    assert "CRITICAL: All ArcGISPro.exe closed!" in mock_registry.sent_alerts[-1]["message"]
    assert "skull" in mock_registry.sent_alerts[-1]["tags"]
    assert mon.status_level == "critical"

def test_step_down_manual_state_reset(mock_registry):
    """Verifies that calling reset_state() clears memory, allowing re-alerting."""
    mon = ProcessStepDownMonitor(
        name="ArcGIS Batch",
        target="ArcGISPro.exe",
        initial_count=3
    )

    mon._get_current_count = lambda: 2
    mon.check(None, mock_registry)
    assert len(mock_registry.sent_alerts) == 1

    # Reset state from UI
    mon.reset_state()
    assert mon.alerted_counts == set()

    # Now dropping to 2 alerts again!
    mon._get_current_count = lambda: 2
    mon.check(None, mock_registry)
    assert len(mock_registry.sent_alerts) == 2

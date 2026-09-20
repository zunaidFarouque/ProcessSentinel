from collections import namedtuple
import pytest
from unittest.mock import patch, MagicMock
from monitors.power import PowerMonitor

# Mock psutil.sensors_battery namedtuple structure
BatteryInfo = namedtuple("sbattery", ["percent", "secsleft", "power_plugged"])

def test_power_monitor_no_battery(mock_registry):
    mon = PowerMonitor(name="Workstation Power")

    with patch("psutil.sensors_battery", return_value=None):
        mon.check(None, mock_registry)
        assert mon.status_level == "ok"
        assert mon.status_text == "OK: Running on AC power (No battery detected)"
        assert len(mock_registry.sent_alerts) == 0
        assert mon.alerted is False

def test_power_monitor_ac_disconnect(mock_registry):
    mon = PowerMonitor(
        name="Laptop UPS Guard",
        alert_on_battery=True,
        battery_threshold=20.0
    )

    unplugged = BatteryInfo(percent=92.0, secsleft=7200, power_plugged=False)
    with patch("psutil.sensors_battery", return_value=unplugged):
        mon.check(None, mock_registry)
        assert mon.status_level == "warning"
        assert len(mock_registry.sent_alerts) == 1
        alert = mock_registry.sent_alerts[0]
        assert "unplugged" in alert["message"].lower() or "battery" in alert["message"].lower()
        assert mon.alerted is True

def test_power_monitor_low_battery_threshold(mock_registry):
    mon = PowerMonitor(
        name="Critical Battery Watch",
        alert_on_battery=False,  # only alert on low threshold
        battery_threshold=15.0
    )

    # Plugged in with 80% battery -> OK
    normal = BatteryInfo(percent=80.0, secsleft=-2, power_plugged=True)
    with patch("psutil.sensors_battery", return_value=normal):
        mon.check(None, mock_registry)
        assert mon.status_level == "ok"
        assert len(mock_registry.sent_alerts) == 0

    # Battery drops to 12% (< 15%)
    low = BatteryInfo(percent=12.0, secsleft=900, power_plugged=False)
    with patch("psutil.sensors_battery", return_value=low):
        mon.check(None, mock_registry)
        assert mon.status_level == "warning"
        assert len(mock_registry.sent_alerts) == 1
        assert "12" in mock_registry.sent_alerts[0]["message"]
        assert mon.alerted is True

def test_power_monitor_recovery_and_debounce(mock_registry):
    mon = PowerMonitor(
        name="Recovering Power",
        alert_on_battery=True,
        battery_threshold=20.0,
        recovery_notification=True
    )

    unplugged = BatteryInfo(percent=85.0, secsleft=5000, power_plugged=False)
    plugged = BatteryInfo(percent=95.0, secsleft=-2, power_plugged=True)

    # 1. Unplug -> alert
    with patch("psutil.sensors_battery", return_value=unplugged):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 1
        assert mon.alerted is True

    # 2. Still unplugged -> debounce (no duplicate)
    with patch("psutil.sensors_battery", return_value=unplugged):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 1

    # 3. Restored -> recovery alert sent
    with patch("psutil.sensors_battery", return_value=plugged):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 2
        rec_alert = mock_registry.sent_alerts[-1]
        assert rec_alert["priority"] == 3
        assert "white_check_mark" in rec_alert["tags"] or "recycle" in rec_alert["tags"] or "battery" in rec_alert["tags"]
        assert mon.alerted is False

    # 4. Still plugged -> no duplicate recovery alert
    with patch("psutil.sensors_battery", return_value=plugged):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 2

def test_power_monitor_trigger_action(mock_registry):
    mon = PowerMonitor(
        name="Power Action Watch",
        alert_on_battery=True,
        action_command="save_and_shutdown.bat"
    )

    unplugged = BatteryInfo(percent=50.0, secsleft=3000, power_plugged=False)
    engine = MagicMock()

    with patch.object(mon, "execute_trigger_action") as mock_action:
        with patch("psutil.sensors_battery", return_value=unplugged):
            mon.check(engine, mock_registry)
            mock_action.assert_called_once_with(engine)

def test_power_monitor_reset_state():
    mon = PowerMonitor(name="ResetPower")
    mon.alerted = True
    mon.status_text = "Triggered: Unplugged"
    mon.status_level = "warning"

    mon.reset_state()
    assert mon.alerted is False
    assert mon.status_text == "State Reset"
    assert mon.status_level == "idle"

def test_power_monitor_serialization():
    mon = PowerMonitor(
        name="SerPower",
        alert_on_battery=True,
        battery_threshold=25.0,
        message="Power Alert: {status_detail}",
        action_command="hibernate.bat",
        action_timeout=50
    )

    d = mon.to_dict()
    assert d["type"] == "PowerMonitor"
    assert d["alert_on_battery"] is True
    assert d["battery_threshold"] == 25.0
    assert d["action_command"] == "hibernate.bat"
    assert d["action_timeout"] == 50

    loaded = PowerMonitor.from_dict(d)
    assert loaded.name == "SerPower"
    assert loaded.alert_on_battery is True
    assert loaded.battery_threshold == 25.0
    assert loaded.action_command == "hibernate.bat"
    assert loaded.action_timeout == 50

import pytest
from unittest.mock import patch
from monitors.storage import StorageMultiTierMonitor

def test_storage_cascading_tiers(mock_registry):
    mon = StorageMultiTierMonitor(
        name="Drive Guard",
        drive="C:\\",
        tiers=[
            {"gb": 30.0, "message": "Warning 30GB", "tag": "warn", "level": "warning", "channel_id": None},
            {"gb": 20.0, "message": "Critical 20GB", "tag": "crit", "level": "critical", "channel_id": None},
            {"gb": 10.0, "message": "Fatal 10GB", "tag": "fatal", "level": "critical", "channel_id": "chan-it"}
        ]
    )

    # 1. 50GB free -> OK, no alert
    with patch("shutil.disk_usage", return_value=(0, 0, 50 * (1024**3))):
        mon.check(None, mock_registry)
        assert mon.status_level == "ok"
        assert len(mock_registry.sent_alerts) == 0

    # 2. Drops to 25GB -> Crosses 30GB tier
    with patch("shutil.disk_usage", return_value=(0, 0, 25 * (1024**3))):
        mon.check(None, mock_registry)
        assert mon.status_level == "warning"
        assert len(mock_registry.sent_alerts) == 1
        assert "Warning 30GB" in mock_registry.sent_alerts[-1]["message"]

    # 3. Drops to 8GB -> Crosses both 20GB and 10GB tiers!
    with patch("shutil.disk_usage", return_value=(0, 0, 8 * (1024**3))):
        mon.check(None, mock_registry)
        assert mon.status_level == "critical"
        # Should have sent 20GB and 10GB alerts
        assert len(mock_registry.sent_alerts) == 3
        assert mock_registry.sent_alerts[-1]["channel_id"] == "chan-it" # Channel override!

    # 4. Same 8GB -> Debounced, no duplicates
    with patch("shutil.disk_usage", return_value=(0, 0, 8 * (1024**3))):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 3

    # 5. Recovery: user cleans up disk, now 35GB free
    with patch("shutil.disk_usage", return_value=(0, 0, 35 * (1024**3))):
        mon.check(None, mock_registry)
        assert mon.status_level == "ok"
        assert len(mon.triggered_tiers) == 0 # Cleared!


def test_storage_custom_tier_priorities(mock_registry):
    """Verifies that each tier can have an independently customized priority level."""
    mon = StorageMultiTierMonitor(
        name="Drive Guard",
        drive="D:\\",
        tiers=[
            {"gb": 30.0, "message": "Low 30GB", "priority": 2, "level": "warning"},
            {"gb": 20.0, "message": "Tight 20GB", "priority": 4, "level": "warning"},
            {"gb": 10.0, "message": "Emergency 10GB", "priority": 5, "level": "critical"}
        ]
    )

    # 1. Drops to 25GB -> Trigger 30GB tier (configured with priority 2)
    with patch("shutil.disk_usage", return_value=(0, 0, 25 * (1024**3))):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 1
        assert mock_registry.sent_alerts[-1]["priority"] == 2

    # 2. Drops to 18GB -> Trigger 20GB tier (configured with priority 4)
    with patch("shutil.disk_usage", return_value=(0, 0, 18 * (1024**3))):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 2
        assert mock_registry.sent_alerts[-1]["priority"] == 4

    # 3. Drops to 5GB -> Trigger 10GB tier (configured with priority 5)
    with patch("shutil.disk_usage", return_value=(0, 0, 5 * (1024**3))):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 3
        assert mock_registry.sent_alerts[-1]["priority"] == 5


def test_storage_step_down_latching_and_hysteresis(mock_registry):
    """
    Verifies:
      - Bouncing above/below threshold does NOT re-trigger when latched.
      - Hitting lower tier triggers the next alert.
      - Manual reset re-arms it.
      - Recovery above threshold + margin un-latches it.
      - step_down_mode=False discards latch immediately upon exceeding threshold.
    """
    mon = StorageMultiTierMonitor(
        name="Latching Storage Guard",
        drive="C:\\",
        tiers=[
            {"gb": 30.0, "message": "Low 30GB", "level": "warning"},
            {"gb": 20.0, "message": "Critical 20GB", "level": "critical"}
        ],
        step_down_mode=True,
        recovery_margin_gb=5.0
    )

    # 1. 40GB free -> OK
    with patch("shutil.disk_usage", return_value=(0, 0, 40 * (1024**3))):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 0
        assert 30.0 not in mon.triggered_tiers

    # 2. Drops to 28GB -> Triggers 30GB tier
    with patch("shutil.disk_usage", return_value=(0, 0, 28 * (1024**3))):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 1
        assert 30.0 in mon.triggered_tiers

    # 3. Bounces up to 32GB (above 30GB, but below 30 + 5 = 35GB)
    # Stays latched! Does NOT un-latch.
    with patch("shutil.disk_usage", return_value=(0, 0, 32 * (1024**3))):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 1
        assert 30.0 in mon.triggered_tiers

    # 4. Bounces back down to 27GB -> Should NOT send duplicate alert!
    with patch("shutil.disk_usage", return_value=(0, 0, 27 * (1024**3))):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 1

    # 5. Drops to 18GB -> Crosses next lower tier (20GB) -> Fires next alert
    with patch("shutil.disk_usage", return_value=(0, 0, 18 * (1024**3))):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 2
        assert "Critical 20GB" in mock_registry.sent_alerts[-1]["message"]
        assert 20.0 in mon.triggered_tiers
        assert 30.0 in mon.triggered_tiers

    # 6. Drops to 17GB -> Debounced, no duplicates
    with patch("shutil.disk_usage", return_value=(0, 0, 17 * (1024**3))):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 2

    # 7. Manual reset re-arms it
    mon.reset_state()
    assert len(mon.triggered_tiers) == 0
    with patch("shutil.disk_usage", return_value=(0, 0, 17 * (1024**3))):
        mon.check(None, mock_registry)
        # Should re-trigger both tiers since state was cleared
        assert len(mock_registry.sent_alerts) == 4

    # 8. Recovery above threshold + margin un-latches it
    # 20GB tier requires >= 25GB, 30GB tier requires >= 35GB
    # Raise to 26GB -> Un-latches 20GB tier, but 30GB tier remains latched
    with patch("shutil.disk_usage", return_value=(0, 0, 26 * (1024**3))):
        mon.check(None, mock_registry)
        assert 20.0 not in mon.triggered_tiers
        assert 30.0 in mon.triggered_tiers

    # Raise to 36GB (above 30 + 5 = 35GB) -> Un-latches 30GB tier completely
    with patch("shutil.disk_usage", return_value=(0, 0, 36 * (1024**3))):
        mon.check(None, mock_registry)
        assert len(mon.triggered_tiers) == 0
        assert mon.status_level == "ok"

    # Now dropping to 28GB re-triggers 30GB tier
    with patch("shutil.disk_usage", return_value=(0, 0, 28 * (1024**3))):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 5
        assert 30.0 in mon.triggered_tiers


def test_storage_step_down_mode_disabled(mock_registry):
    """When step_down_mode is False, tiers un-latch immediately when free_gb > threshold."""
    mon = StorageMultiTierMonitor(
        name="No Hysteresis Guard",
        drive="C:\\",
        tiers=[
            {"gb": 30.0, "message": "Low 30GB", "level": "warning"}
        ],
        step_down_mode=False
    )

    # Trigger at 28GB
    with patch("shutil.disk_usage", return_value=(0, 0, 28 * (1024**3))):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 1
        assert 30.0 in mon.triggered_tiers

    # Rises slightly to 31GB -> immediately discarded because step_down_mode is False
    with patch("shutil.disk_usage", return_value=(0, 0, 31 * (1024**3))):
        mon.check(None, mock_registry)
        assert 30.0 not in mon.triggered_tiers

    # Drops back to 28GB -> re-triggers!
    with patch("shutil.disk_usage", return_value=(0, 0, 28 * (1024**3))):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 2


def test_storage_step_down_serialization():
    mon = StorageMultiTierMonitor(
        name="Serialize Test",
        drive="E:\\",
        step_down_mode=True,
        recovery_margin_gb=8.5
    )
    d = mon.to_dict()
    assert d["step_down_mode"] is True
    assert d["recovery_margin_gb"] == 8.5

    rebuilt = StorageMultiTierMonitor.from_dict(d)
    assert rebuilt.step_down_mode is True
    assert rebuilt.recovery_margin_gb == 8.5



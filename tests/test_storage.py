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

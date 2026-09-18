import os
import time
import pytest
from monitors.io_heartbeat import IOMonitor

def test_io_heartbeat_multi_path_and_filter(tmp_path, mock_registry):
    folder_a = tmp_path / "folder_a"
    folder_b = tmp_path / "folder_b"
    folder_a.mkdir()
    folder_b.mkdir()

    mon = IOMonitor(
        name="GIS Output Watcher",
        paths=[str(folder_a), str(folder_b)],
        filters=["*.shp", "*.gdb"],
        stall_minutes=5.0
    )

    # 1. Non-matching file in folder_a
    (folder_a / "temp.log").write_text("irrelevant")
    mon.check(None, mock_registry)
    assert mon.status_level == "idle"

    # 2. Matching file in folder_b created now
    (folder_b / "output.shp").write_text("shapefile content")
    mon.check(None, mock_registry)
    assert mon.status_level == "ok"
    assert len(mock_registry.sent_alerts) == 0

    # 3. Simulate file being 10 minutes old (stalled)
    old_time = time.time() - 600
    os.utime(str(folder_b / "output.shp"), (old_time, old_time))
    mon.check(None, mock_registry)
    assert mon.status_level == "warning"
    assert len(mock_registry.sent_alerts) == 1
    assert "STALLED" in mon.status_text

    # 4. Debouncing: checking again while still stalled should NOT spam notifications
    mon.check(None, mock_registry)
    assert len(mock_registry.sent_alerts) == 1

    # 5. Activity resumes: new matching file written
    (folder_a / "new_feature.gdb").write_text("new data")
    mon.check(None, mock_registry)
    assert mon.status_level == "ok"
    assert mon.stalled_warned is False

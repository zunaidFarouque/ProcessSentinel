import pytest
import customtkinter as ctk
from unittest.mock import MagicMock, patch

from channels import ChannelRegistry
from engine import MonitorEngine
from monitors.process import ProcessStepDownMonitor
from monitors.storage import StorageMultiTierMonitor
from gui.app import SentinelGUI
from gui.tray import Win32SystemTray

@pytest.fixture
def gui_env(tmp_path):
    root = ctk.CTk()
    root.withdraw()

    registry = ChannelRegistry()
    m1 = ProcessStepDownMonitor(name="Batch Render", target="render.exe", initial_count=2, tags="3d,render")
    m2 = StorageMultiTierMonitor(name="Data Disk", drive="D:\\", tags="storage,backup")
    engine = MonitorEngine(channel_registry=registry, monitors=[m1, m2], log_dir=str(tmp_path / "logs"))

    save_callback = MagicMock(return_value=True)

    app = SentinelGUI(
        root=root,
        engine=engine,
        channel_registry=registry,
        save_callback=save_callback
    )

    yield app, root, engine, registry

    try:
        app._quit_app()
    except Exception:
        try:
            root.destroy()
        except Exception:
            pass

def test_gui_initialization(gui_env):
    app, root, engine, registry = gui_env
    assert hasattr(app, "search_entry")
    assert hasattr(app, "tray")
    assert len(engine.monitors) == 2
    assert "Active Monitors (2 configured)" in app.mon_count_lbl.cget("text")

def test_gui_search_filtering(gui_env):
    app, root, engine, registry = gui_env

    # 1. Filter by name "Batch"
    app.search_entry.delete(0, "end")
    app.search_entry.insert(0, "Batch")
    app._refresh_monitors_list()
    assert "1 matching" in app.mon_count_lbl.cget("text")

    # 2. Filter by tag "backup"
    app.search_entry.delete(0, "end")
    app.search_entry.insert(0, "backup")
    app._refresh_monitors_list()
    assert "1 matching" in app.mon_count_lbl.cget("text")

    # 3. Filter by non-existent text
    app.search_entry.delete(0, "end")
    app.search_entry.insert(0, "NonExistentThing")
    app._refresh_monitors_list()
    assert "0 matching" in app.mon_count_lbl.cget("text")

def test_gui_clone_monitor_logic(gui_env):
    app, root, engine, registry = gui_env
    orig_mon = engine.monitors[0]

    with patch("gui.app.MonitorDialog") as mock_dialog:
        app._open_clone_monitor_dialog(orig_mon)
        assert mock_dialog.called
        _, kwargs = mock_dialog.call_args
        cloned = kwargs["monitor"]
        assert cloned.name == f"{orig_mon.name} (Copy)"
        assert cloned.id != orig_mon.id

def test_tray_graceful_handling():
    tray = Win32SystemTray(tooltip="Test Tray")
    tray.start()
    tray.update_status(True, 5)
    tray.stop()
    assert not tray.is_registered

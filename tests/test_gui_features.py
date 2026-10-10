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

def test_gui_clone_gpu_monitor_with_action(gui_env):
    from monitors.gpu import GPUMonitor
    app, root, engine, registry = gui_env
    gpu_mon = GPUMonitor(name="VRAM Sentinel", gpu_index=0, metric="vram_free_mb", threshold=1024.0, action_command="clean.bat", action_timeout=20)
    engine.add_monitor(gpu_mon)

    with patch("gui.app.MonitorDialog") as mock_dialog:
        app._open_clone_monitor_dialog(gpu_mon)
        assert mock_dialog.called
        _, kwargs = mock_dialog.call_args
        cloned = kwargs["monitor"]
        assert cloned.name == "VRAM Sentinel (Copy)"
        assert cloned.id != gpu_mon.id
        assert cloned.action_command == "clean.bat"
        assert cloned.action_timeout == 20


def test_tray_graceful_handling():
    tray = Win32SystemTray(tooltip="Test Tray")
    tray.start()
    tray.update_status(True, 5)
    tray.stop()
    assert not tray.is_registered


def test_monitor_dialog_edit_step_down_instance_count():
    from gui.dialogs import MonitorDialog
    root = ctk.CTk()
    root.withdraw()

    registry = ChannelRegistry()
    orig_mon = ProcessStepDownMonitor(
        name="ArcGIS Batch",
        target="ArcGISPro.exe",
        initial_count=3,
        alerted_counts=[3]
    )

    saved_mon = []
    def on_save(mon):
        saved_mon.append(mon)

    dialog = MonitorDialog(root, channel_registry=registry, monitor=orig_mon, on_save=on_save)

    # Verify Save button exists and is accessible
    assert hasattr(dialog, "save_btn")
    assert dialog.save_btn.cget("text") == "💾 Save Monitor"

    # Verify initial count entry is preloaded with 3
    assert dialog.init_count_entry.get() == "3"

    # Change count from 3 to 2
    dialog.init_count_entry.delete(0, "end")
    dialog.init_count_entry.insert(0, "2")

    # Trigger save
    dialog._save()

    assert len(saved_mon) == 1
    updated = saved_mon[0]
    assert updated.initial_count == 2
    assert updated.target == "ArcGISPro.exe"
    assert updated.id == orig_mon.id
    # Alerted counts should be cleared when initial count changes to establish fresh baseline
    assert updated.alerted_counts == set()

    try:
        root.destroy()
    except Exception:
        pass


def test_gui_edit_monitor_saves_and_updates_engine(gui_env):
    app, root, engine, registry = gui_env
    step_mon = engine.monitors[0]
    assert isinstance(step_mon, ProcessStepDownMonitor)
    assert step_mon.initial_count == 2

    # Verify target summary helper
    summary = app._get_monitor_target_summary(step_mon)
    assert "🎯 render.exe (target: 2 instances)" in summary

    # Modify monitor: simulate saving updated monitor with 1 instance
    updated_mon = ProcessStepDownMonitor(
        name="Batch Render",
        target="render.exe",
        initial_count=1,
        monitor_id=step_mon.id
    )

    with patch.object(engine, "check_monitor_now") as mock_check:
        with patch("gui.app.MonitorDialog") as mock_dialog:
            app._open_edit_monitor_dialog(step_mon)
            assert mock_dialog.called
            _, kwargs = mock_dialog.call_args
            on_save_cb = kwargs["on_save"]
            on_save_cb(updated_mon)

            # Engine monitor should be updated
            found = engine.get_monitor(step_mon.id)
            assert found.initial_count == 1

            # Auto-save should be triggered
            assert app.save_callback.called

            # Immediate check should be triggered
            mock_check.assert_called_once_with(step_mon.id)


def test_single_instance_checker():
    from single_instance import SingleInstanceChecker
    checker = SingleInstanceChecker(mutex_name="Global\\TestProcessSentinelMutex_12345")
    # First check should succeed
    is_primary = checker.check_and_activate()
    assert is_primary is True
    
    # Second check on same mutex should detect duplicate and attempt activation
    with patch("single_instance.winerror.ERROR_ALREADY_EXISTS", 183):
        with patch("single_instance.win32api.GetLastError", return_value=183):
            duplicate_checker = SingleInstanceChecker(mutex_name="Global\\TestProcessSentinelMutex_12345")
            with patch.object(duplicate_checker, "_activate_existing_instance") as mock_activate:
                assert duplicate_checker.check_and_activate() is False
                assert mock_activate.called

    checker.release()


def test_process_step_down_window_title_fuzzy_extension_matching(monkeypatch):
    from monitors.process import ProcessStepDownMonitor
    import monitors.process as proc_mod

    mon = ProcessStepDownMonitor(
        name="ArcGIS Pro Watcher",
        target="ArcGISPro.exe",
        initial_count=2,
        match_mode="window_title"
    )

    # Mock win32gui.EnumWindows to simulate visible Windows with title "ArcGIS Pro - Project 1"
    mock_titles = [
        (101, "ArcGIS Pro - Project 1"),
        (102, "Untitled - ArcGIS Pro"),
        (103, "Google Chrome")
    ]

    def mock_enum(cb, extra):
        for hwnd, title in mock_titles:
            cb(hwnd, None)

    monkeypatch.setattr(proc_mod, "HAS_WIN32", True)
    monkeypatch.setattr(proc_mod.win32gui, "IsWindowVisible", lambda h: True)
    monkeypatch.setattr(proc_mod.win32gui, "GetWindowText", lambda h: dict(mock_titles)[h])
    monkeypatch.setattr(proc_mod.win32gui, "EnumWindows", mock_enum)

    count = mon._get_current_count()
    # Both 101 and 102 should match "ArcGISPro.exe" via stripped extension/compact comparison
    assert count == 2


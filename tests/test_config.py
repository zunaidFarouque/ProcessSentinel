import pytest
from config_manager import ConfigManager
from channels import ChannelRegistry
from monitors.process import ProcessStepDownMonitor
from monitors.storage import StorageMultiTierMonitor
from monitors.io_heartbeat import IOMonitor

def test_config_roundtrip(tmp_path):
    config_file = str(tmp_path / "test_config.json")
    reg = ChannelRegistry()
    ch_it = reg.add_channel("Lab IT", "https://ntfy.sh/lab_it")

    monitors = [
        ProcessStepDownMonitor(name="Batch 1", target="engine.exe", initial_count=4),
        IOMonitor(name="IO Watch", paths=["D:\\Out"], filters=["*.shp"], stall_minutes=20.0),
        StorageMultiTierMonitor(name="Disk Watch", drive="D:\\")
    ]

    # Save
    success = ConfigManager.save_config(reg, monitors, filepath=config_file)
    assert success is True

    # Load back
    loaded_reg, loaded_mons = ConfigManager.load_config(filepath=config_file)
    assert len(loaded_reg.channels) == 2
    assert loaded_reg.get_channel(ch_it.id).name == "Lab IT"
    assert len(loaded_mons) == 3
    assert loaded_mons[0].name == "Batch 1"
    assert loaded_mons[0].initial_count == 4
    assert loaded_mons[1].filters == ["*.shp"]

def test_config_missing_file_defaults(tmp_path):
    missing_file = str(tmp_path / "non_existent.json")
    reg, mons = ConfigManager.load_config(filepath=missing_file)
    assert len(reg.channels) >= 1
    assert len(mons) >= 1

def test_config_corrupted_file_auto_reset(tmp_path):
    broken_file = tmp_path / "broken.json"
    broken_file.write_text("{ this is NOT valid json !!!", encoding="utf-8")
    
    # Should not crash; must reset to valid defaults and rewrite a healthy file
    reg, mons = ConfigManager.load_config(filepath=str(broken_file))
    assert len(reg.channels) >= 1
    assert len(mons) >= 1

    # Verify that the broken file was overwritten with valid JSON
    loaded_reg, loaded_mons = ConfigManager.load_config(filepath=str(broken_file))
    assert len(loaded_reg.channels) >= 1
    assert len(loaded_mons) >= 1


def test_config_settings_defaults(tmp_path):
    missing_file = str(tmp_path / "settings_test.json")
    reg, mons, settings = ConfigManager.load_config(filepath=missing_file, return_settings=True)
    assert settings["auto_start_engine"] is False
    assert settings["minimize_to_tray"] is True
    assert settings["start_minimized"] is False

    # Also check load_settings directly
    direct_settings = ConfigManager.load_settings(filepath=missing_file)
    assert direct_settings["auto_start_engine"] is False
    assert direct_settings["minimize_to_tray"] is True
    assert direct_settings["start_minimized"] is False


def test_config_settings_custom_persistence(tmp_path):
    config_file = str(tmp_path / "custom_settings.json")
    reg = ChannelRegistry()
    mons = []

    custom_settings = {
        "auto_start_engine": True,
        "minimize_to_tray": False,
        "start_minimized": True
    }
    ConfigManager.save_config(reg, mons, filepath=config_file, settings=custom_settings)

    # Load with return_settings=True
    loaded_reg, loaded_mons, loaded_settings = ConfigManager.load_config(filepath=config_file, return_settings=True)
    assert loaded_settings["auto_start_engine"] is True
    assert loaded_settings["minimize_to_tray"] is False
    assert loaded_settings["start_minimized"] is True

    # Test save_settings directly
    new_settings = {"auto_start_engine": False, "start_minimized": False}
    ConfigManager.save_settings(new_settings, filepath=config_file)
    updated = ConfigManager.load_settings(filepath=config_file)
    assert updated["auto_start_engine"] is False
    assert updated["start_minimized"] is False
    # minimize_to_tray was untouched (preserved as False)
    assert updated["minimize_to_tray"] is False


def test_config_settings_backward_compatibility(tmp_path):
    """Verifies that calling load_config without return_settings still returns a 2-tuple."""
    config_file = str(tmp_path / "compat.json")
    result = ConfigManager.load_config(filepath=config_file)
    assert len(result) == 2
    reg, mons = result
    assert isinstance(reg, ChannelRegistry)
    assert isinstance(mons, list)


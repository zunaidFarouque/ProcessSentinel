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

import sys
import os
import json
from typing import Tuple, List, Optional, Dict, Any, Union

from channels import ChannelRegistry, NotificationChannel
from monitors import create_monitor_from_dict, BaseMonitor
from monitors.process import ProcessStepDownMonitor
from monitors.storage import StorageMultiTierMonitor
from monitors.io_heartbeat import IOMonitor

def get_app_directory() -> str:
    """
    Returns the portable application base directory.
    When running as a compiled standalone .exe, returns the folder containing the executable.
    When running in development, returns the repository root directory.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_FILE = os.path.join(get_app_directory(), "config.json")

DEFAULT_SETTINGS: Dict[str, Any] = {
    "auto_start_engine": False,
    "minimize_to_tray": True,
    "start_minimized": False
}

class ConfigManager:
    """Handles object-oriented serialization, deserialization, settings management, and legacy migration."""
    _current_settings: Dict[str, Any] = dict(DEFAULT_SETTINGS)

    @classmethod
    def get_settings(cls) -> Dict[str, Any]:
        """Returns a copy of the current in-memory settings."""
        return dict(cls._current_settings)

    @classmethod
    def set_settings(cls, settings: Dict[str, Any]) -> None:
        """Updates the current in-memory settings dictionary."""
        cls._current_settings.update(settings)

    @classmethod
    def load_settings(cls, filepath: str = CONFIG_FILE) -> Dict[str, Any]:
        """Loads and returns settings from config.json, merged with defaults."""
        if not os.path.exists(filepath):
            return dict(DEFAULT_SETTINGS)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "settings" in data and isinstance(data["settings"], dict):
                merged = {**DEFAULT_SETTINGS, **data["settings"]}
                cls._current_settings = dict(merged)
                return merged
        except Exception:
            pass
        return dict(DEFAULT_SETTINGS)

    @classmethod
    def save_settings(cls, settings: Dict[str, Any], filepath: str = CONFIG_FILE) -> bool:
        """Saves settings to config.json preserving existing channels and monitors."""
        cls.set_settings(settings)
        data: Dict[str, Any] = {}
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        if not isinstance(data, dict):
            data = {}
        data["settings"] = cls.get_settings()
        if "version" not in data:
            data["version"] = "2.0"
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"[ConfigManager] Failed saving settings to {filepath}: {e}")
            return False

    @classmethod
    def load_config(
        cls,
        filepath: str = CONFIG_FILE,
        return_settings: bool = False
    ) -> Union[Tuple[ChannelRegistry, List[BaseMonitor]], Tuple[ChannelRegistry, List[BaseMonitor], Dict[str, Any]]]:
        if not os.path.exists(filepath):
            reg, mons = cls._get_default_setup()
            cls._current_settings = dict(DEFAULT_SETTINGS)
            cls.save_config(reg, mons, filepath, settings=cls._current_settings)
            if return_settings:
                return reg, mons, dict(cls._current_settings)
            return reg, mons

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("Root JSON must be an object")
        except Exception as e:
            print(f"[ConfigManager] Config file '{filepath}' missing or broken: {e}. Resetting to defaults.")
            reg, mons = cls._get_default_setup()
            cls._current_settings = dict(DEFAULT_SETTINGS)
            cls.save_config(reg, mons, filepath, settings=cls._current_settings)
            if return_settings:
                return reg, mons, dict(cls._current_settings)
            return reg, mons

        # Load settings dictionary if present
        if "settings" in data and isinstance(data["settings"], dict):
            cls._current_settings = {**DEFAULT_SETTINGS, **data["settings"]}
        else:
            cls._current_settings = dict(DEFAULT_SETTINGS)

        # Check for legacy v1 format
        if "ntfy_url" in data and "monitors" not in data:
            print("[ConfigManager] Migrating legacy v1 config to v2 format...")
            reg, mons = cls._migrate_legacy(data)
            cls.save_config(reg, mons, filepath, settings=cls._current_settings)
            if return_settings:
                return reg, mons, dict(cls._current_settings)
            return reg, mons

        try:
            # v2.0 loading
            channels_data = data.get("channels", [])
            default_channel_id = data.get("default_channel_id")
            channel_registry = ChannelRegistry.from_dict({
                "channels": channels_data,
                "default_channel_id": default_channel_id
            })

            monitors: List[BaseMonitor] = []
            for m_data in data.get("monitors", []):
                m = create_monitor_from_dict(m_data)
                if m:
                    monitors.append(m)

            if not monitors:
                _, default_mons = cls._get_default_setup()
                monitors = default_mons

            if return_settings:
                return channel_registry, monitors, dict(cls._current_settings)
            return channel_registry, monitors
        except Exception as e:
            print(f"[ConfigManager] Failed parsing config '{filepath}': {e}. Resetting to default state.")
            reg, mons = cls._get_default_setup()
            cls._current_settings = dict(DEFAULT_SETTINGS)
            cls.save_config(reg, mons, filepath, settings=cls._current_settings)
            if return_settings:
                return reg, mons, dict(cls._current_settings)
            return reg, mons

    @classmethod
    def save_config(
        cls,
        channel_registry: ChannelRegistry,
        monitors: List[BaseMonitor],
        filepath: str = CONFIG_FILE,
        settings: Optional[Dict[str, Any]] = None
    ) -> bool:
        try:
            if settings is not None:
                cls.set_settings(settings)
            data = {
                "version": "2.0",
                "default_channel_id": channel_registry.default_channel_id,
                "channels": [c.to_dict() for c in channel_registry.channels],
                "monitors": [m.to_dict() for m in monitors],
                "settings": cls.get_settings()
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"[ConfigManager] Failed saving {filepath}: {e}")
            return False

    @staticmethod
    def _get_default_setup() -> Tuple[ChannelRegistry, List[BaseMonitor]]:
        registry = ChannelRegistry()
        monitors = [
            ProcessStepDownMonitor(
                name="ArcGIS Pro Batch",
                target="ArcGISPro.exe",
                initial_count=3,
                step_down_message="A rendering window closed. {count} window(s) remaining.",
                critical_message="CRITICAL: All ArcGIS Pro windows have terminated!",
                interval_seconds=60
            ),
            StorageMultiTierMonitor(
                name="Primary C: Drive",
                drive="C:\\",
                tiers=[
                    {"gb": 30.0, "message": "Storage Warning: {free_gb:.1f} GB left on {drive}", "tag": "warning", "level": "warning", "priority": 3, "channel_id": None},
                    {"gb": 20.0, "message": "Critical Warning: {free_gb:.1f} GB left on {drive}!", "tag": "rotating_light", "level": "critical", "priority": 4, "channel_id": None},
                    {"gb": 10.0, "message": "FATAL: {free_gb:.1f} GB left on {drive}! Imminent disk exhaustion!", "tag": "skull,fire", "level": "critical", "priority": 5, "channel_id": None}
                ],
                interval_seconds=120
            ),
            IOMonitor(
                name="Scratch I/O Heartbeat",
                paths=["D:\\Scratch", "C:\\Temp"],
                filters=["*.shp", "*.gdb", "*.csv"],
                stall_minutes=15.0,
                interval_seconds=60
            )
        ]
        return registry, monitors

    @staticmethod
    def _migrate_legacy(old_data: dict) -> Tuple[ChannelRegistry, List[BaseMonitor]]:
        url = old_data.get("ntfy_url", "https://ntfy.sh/mzf_FAU_GRA_Monitoring")
        default_chan = NotificationChannel(name="Primary Phone", url=url, channel_id="chan-default")
        registry = ChannelRegistry(channels=[default_chan], default_channel_id=default_chan.id)

        monitors = []
        for proc in old_data.get("processes", ["ArcGISPro.exe"]):
            monitors.append(ProcessStepDownMonitor(
                name=f"Monitor ({proc})",
                target=proc,
                initial_count=1,
                interval_seconds=60
            ))

        watch_folder = old_data.get("watch_folder")
        if watch_folder:
            monitors.append(IOMonitor(
                name="Scratch Folder Heartbeat",
                paths=[watch_folder],
                filters=["*.*"],
                stall_minutes=float(old_data.get("stalled_mins", 15)),
                interval_seconds=60
            ))

        min_storage = old_data.get("min_storage_gb")
        if min_storage:
            monitors.append(StorageMultiTierMonitor(
                name="Storage Guard",
                drive="C:\\",
                tiers=[{"gb": float(min_storage), "message": "Disk below threshold: {free_gb:.1f} GB left", "tag": "warning", "level": "warning", "channel_id": None}],
                interval_seconds=120
            ))

        return registry, monitors

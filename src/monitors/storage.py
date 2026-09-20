import os
import shutil
from typing import Optional, List, Dict, Any, Set
from monitors.base import BaseMonitor

class StorageMultiTierMonitor(BaseMonitor):
    """
    Monitors available storage on a drive with multiple condition tiers:
      e.g. 30GB = Warning, 20GB = Critical, 10GB = Fatal.
      Each tier can have its own message, tag, level, and optional channel override.
    """
    monitor_type = "StorageMultiTier"
    display_name = "Storage Free Space (Multi-Tier)"

    def __init__(
        self,
        name: str,
        drive: str = "C:\\",
        tiers: Optional[List[Dict[str, Any]]] = None,
        interval_seconds: int = 120,
        channel_id: Optional[str] = None,
        enabled: bool = True,
        monitor_id: Optional[str] = None,
        priority: int = 4,
        tags: str = "floppy_disk",
        title_template: Optional[str] = None,
        click_url: Optional[str] = None,
        markdown_enabled: bool = True,
        recovery_notification: bool = False,
        recovery_message: Optional[str] = None,
        step_down_mode: bool = True,
        recovery_margin_gb: float = 5.0,
        action_command: Optional[str] = None,
        action_timeout: int = 30
    ):
        super().__init__(
            name=name,
            interval_seconds=interval_seconds,
            channel_id=channel_id,
            enabled=enabled,
            monitor_id=monitor_id,
            priority=priority,
            tags=tags,
            title_template=title_template,
            click_url=click_url,
            markdown_enabled=markdown_enabled,
            recovery_notification=recovery_notification,
            recovery_message=recovery_message,
            action_command=action_command,
            action_timeout=action_timeout
        )
        self.drive = drive.strip()
        self.tiers = tiers or [
            {"gb": 30.0, "message": "Storage Warning: Only {free_gb:.1f} GB remaining on {drive}", "tag": "warning", "level": "warning", "priority": 3, "channel_id": None},
            {"gb": 20.0, "message": "CRITICAL STORAGE: Only {free_gb:.1f} GB remaining on {drive}!", "tag": "rotating_light", "level": "critical", "priority": 4, "channel_id": None},
            {"gb": 10.0, "message": "FATAL STORAGE: Only {free_gb:.1f} GB remaining on {drive}! Imminent crash risk!", "tag": "skull,fire", "level": "critical", "priority": 5, "channel_id": None}
        ]
        self.tiers.sort(key=lambda t: float(t.get("gb", 0)), reverse=True)
        self.triggered_tiers: Set[float] = set()
        self.step_down_mode = bool(step_down_mode)
        self.recovery_margin_gb = float(recovery_margin_gb)

    def check(self, engine, channel_registry) -> None:
        try:
            _, _, free = shutil.disk_usage(self.drive)
            free_gb = free / (1024 ** 3)
        except Exception as e:
            self.status_text = f"Error reading drive {self.drive}: {e}"
            self.status_level = "warning"
            return

        highest_triggered_level = "ok"
        for tier in self.tiers:
            threshold_gb = float(tier.get("gb", 0))
            if free_gb <= threshold_gb:
                tier_level = tier.get("level", "warning")
                if tier_level == "critical":
                    highest_triggered_level = "critical"
                elif highest_triggered_level != "critical":
                    highest_triggered_level = "warning"

                if threshold_gb not in self.triggered_tiers:
                    msg = tier.get("message", "Storage alert on {drive}").format(drive=self.drive, free_gb=free_gb)
                    target_channel = tier.get("channel_id") or self.channel_id
                    
                    if "priority" in tier:
                        priority = int(tier["priority"])
                    else:
                        priority = 5 if tier.get("level") == "critical" else self.priority

                    title = self.format_title(f"{self.name}: Low Disk Space", drive=self.drive, free_gb=free_gb)
                    if channel_registry:
                        channel_registry.send_alert(
                            channel_id=target_channel,
                            message=msg,
                            title=title,
                            tags=tier.get("tag", self.tags or "floppy_disk"),
                            priority=priority,
                            click_url=self.click_url,
                            markdown=self.markdown_enabled
                        )
                    self.execute_trigger_action(engine)
                    self.triggered_tiers.add(threshold_gb)
            else:
                if self.step_down_mode:
                    if free_gb >= (threshold_gb + self.recovery_margin_gb):
                        self.triggered_tiers.discard(threshold_gb)
                else:
                    self.triggered_tiers.discard(threshold_gb)

        if highest_triggered_level != "ok":
            self.status_text = f"Alert: {free_gb:.1f} GB free on {self.drive}"
            self.status_level = highest_triggered_level
        elif self.triggered_tiers:
            self.status_text = f"Alert (Latched): {free_gb:.1f} GB free on {self.drive}"
            self.status_level = "warning"
        else:
            self.status_text = f"OK: {free_gb:.1f} GB free on {self.drive}"
            self.status_level = "ok"

    def reset_state(self) -> None:
        self.triggered_tiers.clear()
        self.status_text = "State Reset"
        self.status_level = "idle"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "drive": self.drive,
            "tiers": self.tiers,
            "step_down_mode": self.step_down_mode,
            "recovery_margin_gb": self.recovery_margin_gb
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StorageMultiTierMonitor":
        return cls(
            name=data.get("name", "Storage Space Multi-Tier"),
            drive=data.get("drive", "C:\\"),
            tiers=data.get("tiers", []),
            interval_seconds=data.get("interval_seconds", 120),
            channel_id=data.get("channel_id"),
            enabled=data.get("enabled", True),
            monitor_id=data.get("id"),
            priority=data.get("priority", 4),
            tags=data.get("tags", "floppy_disk"),
            title_template=data.get("title_template"),
            click_url=data.get("click_url"),
            markdown_enabled=data.get("markdown_enabled", True),
            recovery_notification=data.get("recovery_notification", False),
            recovery_message=data.get("recovery_message"),
            step_down_mode=data.get("step_down_mode", True),
            recovery_margin_gb=float(data.get("recovery_margin_gb", 5.0)),
            action_command=data.get("action_command"),
            action_timeout=data.get("action_timeout", 30)
        )


class DirectorySizeMonitor(BaseMonitor):
    """Monitors total size of a specific directory (cache/scratch bloat)."""
    monitor_type = "DirectorySize"
    display_name = "Directory Size Watcher"

    def __init__(
        self,
        name: str,
        path: str,
        max_size_gb: float = 50.0,
        message: str = "Directory '{path}' has exceeded {max_size_gb:.1f} GB (Current: {current_gb:.1f} GB)!",
        interval_seconds: int = 300,
        channel_id: Optional[str] = None,
        enabled: bool = True,
        monitor_id: Optional[str] = None,
        priority: int = 4,
        tags: str = "file_folder,warning",
        title_template: Optional[str] = None,
        click_url: Optional[str] = None,
        markdown_enabled: bool = True,
        recovery_notification: bool = False,
        recovery_message: Optional[str] = None,
        action_command: Optional[str] = None,
        action_timeout: int = 30
    ):
        super().__init__(
            name=name,
            interval_seconds=interval_seconds,
            channel_id=channel_id,
            enabled=enabled,
            monitor_id=monitor_id,
            priority=priority,
            tags=tags,
            title_template=title_template,
            click_url=click_url,
            markdown_enabled=markdown_enabled,
            recovery_notification=recovery_notification,
            recovery_message=recovery_message,
            action_command=action_command,
            action_timeout=action_timeout
        )
        self.path = path.strip()
        self.max_size_gb = float(max_size_gb)
        self.message = message
        self.alerted: bool = False

    def check(self, engine, channel_registry) -> None:
        if not os.path.exists(self.path):
            self.status_text = f"Error: Directory '{self.path}' not found"
            self.status_level = "warning"
            return

        total_bytes = 0
        try:
            for root, _, files in os.walk(self.path):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total_bytes += os.path.getsize(fp)
                    except OSError:
                        pass
        except Exception as e:
            self.status_text = f"Error reading directory: {e}"
            self.status_level = "warning"
            return

        current_gb = total_bytes / (1024 ** 3)
        if current_gb > self.max_size_gb:
            if not self.alerted:
                msg = self.message.format(path=self.path, max_size_gb=self.max_size_gb, current_gb=current_gb)
                title = self.format_title(f"{self.name}: Folder Size Warning", path=self.path, max_size_gb=self.max_size_gb, current_gb=current_gb)
                if channel_registry:
                    channel_registry.send_alert(
                        channel_id=self.channel_id,
                        message=msg,
                        title=title,
                        tags=self.tags,
                        priority=self.priority,
                        click_url=self.click_url,
                        markdown=self.markdown_enabled
                    )
                self.execute_trigger_action(engine)
                self.alerted = True
            self.status_text = f"Bloat: {current_gb:.2f} GB (> {self.max_size_gb:.1f} GB)"
            self.status_level = "warning"
        else:
            self.alerted = False
            self.status_text = f"OK: {current_gb:.2f} GB (Limit: {self.max_size_gb:.1f} GB)"
            self.status_level = "ok"

    def reset_state(self) -> None:
        self.alerted = False
        self.status_text = "State Reset"
        self.status_level = "idle"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "path": self.path,
            "max_size_gb": self.max_size_gb,
            "message": self.message
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DirectorySizeMonitor":
        return cls(
            name=data.get("name", "Directory Size Monitor"),
            path=data.get("path", ""),
            max_size_gb=data.get("max_size_gb", 50.0),
            message=data.get("message", "Directory '{path}' exceeded {max_size_gb:.1f} GB."),
            interval_seconds=data.get("interval_seconds", 300),
            channel_id=data.get("channel_id"),
            enabled=data.get("enabled", True),
            monitor_id=data.get("id"),
            priority=data.get("priority", 4),
            tags=data.get("tags", "file_folder,warning"),
            title_template=data.get("title_template"),
            click_url=data.get("click_url"),
            markdown_enabled=data.get("markdown_enabled", True),
            recovery_notification=data.get("recovery_notification", False),
            recovery_message=data.get("recovery_message"),
            action_command=data.get("action_command"),
            action_timeout=data.get("action_timeout", 30)
        )


import os
import time
import fnmatch
from typing import Optional, List, Dict, Any
from monitors.base import BaseMonitor

class IOMonitor(BaseMonitor):
    """
    Monitors one or more directories for recent read/write activity.
    Supports file extension filters (e.g. *.shp, *.gdb, *.csv).
    If no matching file is modified within stall_minutes, sends alert.
    """
    monitor_type = "IOMonitor"
    display_name = "I/O Heartbeat (Multi-Path & File Filter)"

    def __init__(
        self,
        name: str,
        paths: List[str],
        filters: Optional[List[str]] = None,
        stall_minutes: float = 15.0,
        message: str = "No matching files modified in {stall_mins:.1f} mins across monitored paths. Pipeline stalled!",
        interval_seconds: int = 60,
        channel_id: Optional[str] = None,
        enabled: bool = True,
        monitor_id: Optional[str] = None
    ):
        super().__init__(name, interval_seconds, channel_id, enabled, monitor_id)
        self.paths = [p.strip() for p in paths if p.strip()]
        self.filters = [f.strip().lower() for f in (filters or ["*.*"]) if f.strip()]
        self.stall_minutes = max(1.0, float(stall_minutes))
        self.message = message
        self.stalled_warned: bool = False

    def _matches_filter(self, filename: str) -> bool:
        fn_lower = filename.lower()
        for pat in self.filters:
            if pat == "*.*" or pat == "*" or fnmatch.fnmatch(fn_lower, pat):
                return True
        return False

    def check(self, engine, channel_registry) -> None:
        newest_time: float = 0.0
        found_any_path = False

        for folder in self.paths:
            if os.path.exists(folder):
                found_any_path = True
                try:
                    for root, _, files in os.walk(folder):
                        for file in files:
                            if self._matches_filter(file):
                                file_path = os.path.join(root, file)
                                try:
                                    mtime = os.path.getmtime(file_path)
                                    if mtime > newest_time:
                                        newest_time = mtime
                                except OSError:
                                    pass
                except Exception:
                    pass

        if not found_any_path:
            self.status_text = "Error: Configured paths do not exist"
            self.status_level = "warning"
            return

        if newest_time == 0.0:
            self.status_text = "Idle: No matching files found in folders yet"
            self.status_level = "idle"
            return

        mins_idle = (time.time() - newest_time) / 60.0

        if mins_idle > self.stall_minutes:
            if not self.stalled_warned:
                msg = self.message.format(stall_mins=mins_idle)
                channel_registry.send_alert(
                    channel_id=self.channel_id,
                    message=msg,
                    title=f"{self.name}: I/O Stalled",
                    tags="warning,hourglass_done",
                    priority=4
                )
                self.stalled_warned = True
            self.status_text = f"STALLED: Inactive for {mins_idle:.1f} mins (> {self.stall_minutes:.0f}m)"
            self.status_level = "warning"
        else:
            self.stalled_warned = False
            self.status_text = f"OK: Active {mins_idle:.1f} mins ago"
            self.status_level = "ok"

    def reset_state(self) -> None:
        self.stalled_warned = False
        self.status_text = "State Reset"
        self.status_level = "idle"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "paths": self.paths,
            "filters": self.filters,
            "stall_minutes": self.stall_minutes,
            "message": self.message
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IOMonitor":
        return cls(
            name=data.get("name", "I/O Heartbeat"),
            paths=data.get("paths", []),
            filters=data.get("filters", ["*.*"]),
            stall_minutes=data.get("stall_minutes", 15.0),
            message=data.get("message", "No matching files modified in {stall_mins:.1f} mins across monitored paths."),
            interval_seconds=data.get("interval_seconds", 60),
            channel_id=data.get("channel_id"),
            enabled=data.get("enabled", True),
            monitor_id=data.get("id")
        )

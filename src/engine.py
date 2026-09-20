import os
import time
import threading
import logging
from logging.handlers import RotatingFileHandler
from typing import List, Optional, Callable, Dict, Any
from datetime import datetime

from channels import ChannelRegistry
from monitors.base import BaseMonitor
from config_manager import get_app_directory

class MonitorEngine:
    """Master background engine executing all active monitors."""
    def __init__(
        self,
        channel_registry: ChannelRegistry,
        monitors: Optional[List[BaseMonitor]] = None,
        log_dir: Optional[str] = None
    ):
        self.channel_registry = channel_registry
        self.monitors: List[BaseMonitor] = monitors or []
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # Callbacks for GUI synchronization
        self.on_monitor_updated: Optional[Callable[[BaseMonitor], None]] = None
        self.on_log_message: Optional[Callable[[str], None]] = None

        # In-memory circular log buffer for UI activity feed
        self.logs: List[Dict[str, Any]] = []
        self.max_logs = 200

        # Persistent rotating disk logging
        self.log_dir = log_dir or os.path.join(get_app_directory(), "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, "sentinel.log")

        self.logger = logging.getLogger(f"ProcessSentinel.{id(self)}")
        self.logger.setLevel(logging.DEBUG)

        self._file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        self._file_handler.setFormatter(formatter)
        self.logger.addHandler(self._file_handler)

    def log(self, message: str, level: str = "info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = {"time": timestamp, "message": message, "level": level}
        with self._lock:
            self.logs.append(entry)
            if len(self.logs) > self.max_logs:
                self.logs.pop(0)

        # Write to persistent rotating log file
        level_map = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "warn": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL
        }
        lvl = level_map.get(str(level).lower(), logging.INFO)
        if self.logger:
            self.logger.log(lvl, message)

        if self.on_log_message:
            try:
                self.on_log_message(f"[{timestamp}] {message}")
            except Exception:
                pass

    def close(self):
        """Cleanly closes file handlers."""
        if hasattr(self, "_file_handler") and self._file_handler:
            self._file_handler.close()
            self.logger.removeHandler(self._file_handler)
            self._file_handler = None

    def start(self):
        started = False
        with self._lock:
            if not self.running:
                self.running = True
                self._thread = threading.Thread(target=self._loop, daemon=True)
                self._thread.start()
                started = True
        if started:
            self.log("Monitoring Engine started.", level="info")

    def stop(self):
        with self._lock:
            self.running = False
        self.log("Monitoring Engine stopped.", level="info")

    def is_running(self) -> bool:
        return self.running

    def add_monitor(self, monitor: BaseMonitor):
        with self._lock:
            self.monitors.append(monitor)
        self.log(f"Added monitor '{monitor.name}' ({monitor.display_name}).")

    def remove_monitor(self, monitor_id: str):
        with self._lock:
            self.monitors = [m for m in self.monitors if m.id != monitor_id]
        self.log(f"Removed monitor ID '{monitor_id}'.")

    def get_monitor(self, monitor_id: str) -> Optional[BaseMonitor]:
        with self._lock:
            for m in self.monitors:
                if m.id == monitor_id:
                    return m
        return None

    def reset_monitor(self, monitor_id: str):
        """Flushes the internal alert memory of a specific monitor."""
        m = self.get_monitor(monitor_id)
        if m:
            m.reset_state()
            self.log(f"State reset for monitor '{m.name}'.", level="info")
            if self.on_monitor_updated:
                self.on_monitor_updated(m)

    def check_monitor_now(self, monitor_id: str):
        """Forces an immediate check of a specific monitor."""
        m = self.get_monitor(monitor_id)
        if m:
            threading.Thread(target=self._run_single_check, args=(m,), daemon=True).start()

    def _run_single_check(self, monitor: BaseMonitor):
        try:
            monitor.check(engine=self, channel_registry=self.channel_registry)
            monitor.last_check_time = time.time()
            self.log(f"Checked '{monitor.name}': {monitor.status_text}")
        except Exception as e:
            monitor.status_text = f"Error: {e}"
            monitor.status_level = "warning"
            self.log(f"Check error on '{monitor.name}': {e}", level="error")
        if self.on_monitor_updated:
            try:
                self.on_monitor_updated(monitor)
            except Exception:
                pass

    def _loop(self):
        """Core loop checking monitors according to individual intervals."""
        while self.running:
            now = time.time()
            with self._lock:
                current_monitors = list(self.monitors)

            for monitor in current_monitors:
                if not self.running:
                    break
                if not monitor.enabled:
                    continue

                if now - monitor.last_check_time >= monitor.interval_seconds:
                    self._run_single_check(monitor)

            time.sleep(0.5)

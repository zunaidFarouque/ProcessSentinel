import psutil
from typing import Optional, List, Dict, Any, Set
from monitors.base import BaseMonitor

try:
    import win32gui
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

class ProcessStepDownMonitor(BaseMonitor):
    """
    Monitors visible windows or processes matching a target string.
    Tracks step-down transitions (e.g. 3 -> 2 -> 1 -> 0):
      - Alerts ONCE for each downward step (e.g. 3 -> 2).
      - If instances increase (e.g. 2 -> 3), no alert.
      - If instances drop again to a previously alerted count (e.g. 3 -> 2), NO duplicate alert.
      - Alert at 0 triggers a critical notification.
      - User can reset state from UI to re-arm the step-down tracking.
    """
    monitor_type = "ProcessStepDown"
    display_name = "Process Step-Down (Window High-Watermark)"

    def __init__(
        self,
        name: str,
        target: str,
        initial_count: int = 3,
        match_mode: str = "window_title",
        step_down_message: str = "Tracked window count dropped to {count}.",
        critical_message: str = "CRITICAL: All '{target}' windows have closed!",
        interval_seconds: int = 60,
        channel_id: Optional[str] = None,
        enabled: bool = True,
        monitor_id: Optional[str] = None,
        alerted_counts: Optional[List[int]] = None,
        priority: int = 5,
        tags: str = "skull,rotating_light",
        title_template: Optional[str] = None,
        click_url: Optional[str] = None,
        markdown_enabled: bool = True,
        step_down_priority: int = 4,
        step_down_tags: str = "warning,arrow_down"
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
            markdown_enabled=markdown_enabled
        )
        self.target = target.strip()
        self.initial_count = max(1, int(initial_count))
        self.match_mode = match_mode
        self.step_down_message = step_down_message
        self.critical_message = critical_message
        self.alerted_counts: Set[int] = set(alerted_counts or [])
        self.last_observed_count: Optional[int] = None
        self.step_down_priority = int(step_down_priority)
        self.step_down_tags = (step_down_tags or "").strip()

    def _get_current_count(self) -> int:
        target_lower = self.target.lower()
        if self.match_mode == "window_title" and HAS_WIN32:
            matched_hwnds = []
            def enum_cb(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).strip().lower()
                    if title and target_lower in title:
                        matched_hwnds.append(hwnd)
            win32gui.EnumWindows(enum_cb, None)
            return len(matched_hwnds)
        else:
            count = 0
            for proc in psutil.process_iter(["name"]):
                try:
                    pname = (proc.info.get("name") or "").lower()
                    if target_lower in pname:
                        count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return count

    def check(self, engine, channel_registry) -> None:
        current_count = self._get_current_count()
        self.last_observed_count = current_count

        if current_count >= self.initial_count:
            self.status_text = f"OK: {current_count} instances active (target: {self.initial_count})"
            self.status_level = "ok"
            return

        if current_count == 0:
            if 0 not in self.alerted_counts:
                msg = self.critical_message.format(target=self.target, count=0)
                title = self.format_title(f"{self.name}: All Closed", target=self.target, count=0)
                channel_registry.send_alert(
                    channel_id=self.channel_id,
                    message=msg,
                    title=title,
                    tags=self.tags,
                    priority=self.priority,
                    click_url=self.click_url,
                    markdown=self.markdown_enabled
                )
                self.alerted_counts.add(0)
            self.status_text = f"CRITICAL: 0 instances active (All closed!)"
            self.status_level = "critical"
        else:
            if current_count not in self.alerted_counts:
                msg = self.step_down_message.format(target=self.target, count=current_count)
                title = self.format_title(f"{self.name}: Step-Down Alert", target=self.target, count=current_count)
                channel_registry.send_alert(
                    channel_id=self.channel_id,
                    message=msg,
                    title=title,
                    tags=self.step_down_tags,
                    priority=self.step_down_priority,
                    click_url=self.click_url,
                    markdown=self.markdown_enabled
                )
                self.alerted_counts.add(current_count)
            self.status_text = f"Warning: {current_count}/{self.initial_count} instances active"
            self.status_level = "warning"

    def reset_state(self) -> None:
        self.alerted_counts.clear()
        self.status_text = "State Reset (Memory Cleared)"
        self.status_level = "idle"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "target": self.target,
            "initial_count": self.initial_count,
            "match_mode": self.match_mode,
            "step_down_message": self.step_down_message,
            "critical_message": self.critical_message,
            "alerted_counts": list(self.alerted_counts),
            "step_down_priority": self.step_down_priority,
            "step_down_tags": self.step_down_tags
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessStepDownMonitor":
        return cls(
            name=data.get("name", "Process Step-Down"),
            target=data.get("target", ""),
            initial_count=data.get("initial_count", 3),
            match_mode=data.get("match_mode", "window_title"),
            step_down_message=data.get("step_down_message", "Tracked window count dropped to {count}."),
            critical_message=data.get("critical_message", "CRITICAL: All '{target}' windows closed!"),
            interval_seconds=data.get("interval_seconds", 60),
            channel_id=data.get("channel_id"),
            enabled=data.get("enabled", True),
            monitor_id=data.get("id"),
            alerted_counts=data.get("alerted_counts", []),
            priority=data.get("priority", 5),
            tags=data.get("tags", "skull,rotating_light"),
            title_template=data.get("title_template"),
            click_url=data.get("click_url"),
            markdown_enabled=data.get("markdown_enabled", True),
            step_down_priority=data.get("step_down_priority", 4),
            step_down_tags=data.get("step_down_tags", "warning,arrow_down")
        )


class ProcessInstanceMonitor(BaseMonitor):
    """Checks running processes or windows against a threshold count."""
    monitor_type = "ProcessInstance"
    display_name = "Process Instance Count"

    def __init__(
        self,
        name: str,
        target: str,
        condition: str = "below",
        threshold: int = 1,
        match_mode: str = "process_name",
        message: str = "Process '{target}' instance count is {count} (threshold: {threshold}).",
        interval_seconds: int = 60,
        channel_id: Optional[str] = None,
        enabled: bool = True,
        monitor_id: Optional[str] = None,
        priority: int = 4,
        tags: str = "warning,gear",
        title_template: Optional[str] = None,
        click_url: Optional[str] = None,
        markdown_enabled: bool = True
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
            markdown_enabled=markdown_enabled
        )
        self.target = target.strip()
        self.condition = condition
        self.threshold = int(threshold)
        self.match_mode = match_mode
        self.message = message
        self.alerted: bool = False

    def _get_current_count(self) -> int:
        target_lower = self.target.lower()
        if self.match_mode == "window_title" and HAS_WIN32:
            matched = []
            def cb(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    t = win32gui.GetWindowText(hwnd).strip().lower()
                    if t and target_lower in t:
                        matched.append(hwnd)
            win32gui.EnumWindows(cb, None)
            return len(matched)
        else:
            count = 0
            for proc in psutil.process_iter(["name"]):
                try:
                    pname = (proc.info.get("name") or "").lower()
                    if target_lower in pname:
                        count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return count

    def check(self, engine, channel_registry) -> None:
        count = self._get_current_count()
        triggered = False
        if self.condition == "below" and count < self.threshold:
            triggered = True
        elif self.condition == "above" and count > self.threshold:
            triggered = True
        elif self.condition == "equals" and count == self.threshold:
            triggered = True

        if triggered:
            if not self.alerted:
                msg = self.message.format(target=self.target, count=count, threshold=self.threshold)
                title = self.format_title(f"{self.name}: Instance Alert", target=self.target, count=count, threshold=self.threshold)
                channel_registry.send_alert(
                    channel_id=self.channel_id,
                    message=msg,
                    title=title,
                    tags=self.tags,
                    priority=self.priority,
                    click_url=self.click_url,
                    markdown=self.markdown_enabled
                )
                self.alerted = True
            self.status_text = f"Triggered: {count} instances ({self.condition} {self.threshold})"
            self.status_level = "warning"
        else:
            self.alerted = False
            self.status_text = f"OK: {count} instances active"
            self.status_level = "ok"

    def reset_state(self) -> None:
        self.alerted = False
        self.status_text = "State Reset"
        self.status_level = "idle"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "target": self.target,
            "condition": self.condition,
            "threshold": self.threshold,
            "match_mode": self.match_mode,
            "message": self.message
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessInstanceMonitor":
        return cls(
            name=data.get("name", "Process Instance Monitor"),
            target=data.get("target", ""),
            condition=data.get("condition", "below"),
            threshold=data.get("threshold", 1),
            match_mode=data.get("match_mode", "process_name"),
            message=data.get("message", "Process '{target}' instance count is {count} (threshold: {threshold})."),
            interval_seconds=data.get("interval_seconds", 60),
            channel_id=data.get("channel_id"),
            enabled=data.get("enabled", True),
            monitor_id=data.get("id"),
            priority=data.get("priority", 4),
            tags=data.get("tags", "warning,gear"),
            title_template=data.get("title_template"),
            click_url=data.get("click_url"),
            markdown_enabled=data.get("markdown_enabled", True)
        )

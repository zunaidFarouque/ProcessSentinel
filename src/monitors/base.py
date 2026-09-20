import uuid
import subprocess
from typing import Optional, Dict, Any

class BaseMonitor:
    """Abstract base class for all ProcessSentinel monitors."""
    monitor_type = "BaseMonitor"
    display_name = "Base Monitor"

    def __init__(
        self,
        name: str,
        interval_seconds: int = 60,
        channel_id: Optional[str] = None,
        enabled: bool = True,
        monitor_id: Optional[str] = None,
        priority: int = 3,
        tags: str = "",
        title_template: Optional[str] = None,
        click_url: Optional[str] = None,
        markdown_enabled: bool = True,
        recovery_notification: bool = False,
        recovery_message: Optional[str] = None,
        action_command: Optional[str] = None,
        action_timeout: int = 30
    ):
        self.id = monitor_id or f"mon-{uuid.uuid4().hex[:8]}"
        self.name = name.strip()
        self.interval_seconds = max(5, int(interval_seconds))
        self.channel_id = channel_id
        self.enabled = enabled
        self.priority = int(priority)
        self.tags = (tags or "").strip()
        self.title_template = title_template.strip() if title_template else None
        self.click_url = click_url.strip() if click_url else None
        self.markdown_enabled = markdown_enabled
        self.recovery_notification = bool(recovery_notification)
        self.recovery_message = recovery_message.strip() if recovery_message else None
        self.action_command = action_command.strip() if action_command and action_command.strip() else None
        self.action_timeout = max(1, int(action_timeout)) if action_timeout is not None else 30

        self.last_check_time: float = 0.0
        self.status_text: str = "Initialized"
        self.status_level: str = "idle"  # "ok", "warning", "critical", "idle"

    def format_title(self, fallback: str, **kwargs) -> str:
        """Interpolates title_template with variables or returns fallback."""
        if self.title_template:
            try:
                return self.title_template.format(name=self.name, **kwargs)
            except Exception:
                return self.title_template
        return fallback

    def send_recovery_alert(
        self,
        channel_registry,
        message: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[str] = None
    ) -> bool:
        """Helper to send a recovery ('Resolved') notification."""
        if not channel_registry:
            return False
        final_message = message or self.recovery_message or f"{self.name} has recovered."
        final_title = title or self.format_title(f"RESOLVED: {self.name}")
        final_tags = tags if tags is not None else "white_check_mark,recycle"
        return channel_registry.send_alert(
            channel_id=self.channel_id,
            message=final_message,
            title=final_title,
            tags=final_tags,
            priority=3,
            click_url=self.click_url,
            markdown=self.markdown_enabled
        )

    def execute_trigger_action(self, engine=None) -> Optional[str]:
        """Executes a configured local script or shell command on alert trigger."""
        if not self.action_command:
            return None

        if engine:
            engine.log(f"Executing action command for '{self.name}': {self.action_command}", level="info")

        try:
            result = subprocess.run(
                self.action_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.action_timeout,
                errors="replace"
            )
            out = (result.stdout or "").strip()
            err = (result.stderr or "").strip()
            combined = out if out else err
            snippet = combined[:100].replace("\n", " ") if combined else "No output"
            summary = f"[Action: exit {result.returncode}] {snippet}"
            log_level = "info" if result.returncode == 0 else "warning"
            if engine:
                engine.log(f"Action command finished for '{self.name}': {summary}", level=log_level)
            return summary
        except subprocess.TimeoutExpired:
            summary = f"[Action: timeout ({self.action_timeout}s)]"
            if engine:
                engine.log(f"Action command timed out for '{self.name}' after {self.action_timeout}s", level="error")
            return summary
        except Exception as e:
            summary = f"[Action: error] {e}"
            if engine:
                engine.log(f"Action command error for '{self.name}': {e}", level="error")
            return summary

    def execute_action(self, engine=None) -> Optional[str]:
        """Alias for execute_trigger_action."""
        return self.execute_trigger_action(engine=engine)

    def check(self, engine, channel_registry) -> None:
        """Executes the monitoring condition check. Must update status_text and status_level."""
        raise NotImplementedError

    def reset_state(self) -> None:
        """Manually resets internal state, clearing triggered flags and memory."""
        self.status_text = "State Reset"
        self.status_level = "idle"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.monitor_type,
            "name": self.name,
            "interval_seconds": self.interval_seconds,
            "channel_id": self.channel_id,
            "enabled": self.enabled,
            "priority": self.priority,
            "tags": self.tags,
            "title_template": self.title_template,
            "click_url": self.click_url,
            "markdown_enabled": self.markdown_enabled,
            "recovery_notification": self.recovery_notification,
            "recovery_message": self.recovery_message,
            "action_command": self.action_command,
            "action_timeout": self.action_timeout
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseMonitor":
        return cls(
            name=data.get("name", "Base Monitor"),
            interval_seconds=data.get("interval_seconds", 60),
            channel_id=data.get("channel_id"),
            enabled=data.get("enabled", True),
            monitor_id=data.get("id"),
            priority=data.get("priority", 3),
            tags=data.get("tags", ""),
            title_template=data.get("title_template"),
            click_url=data.get("click_url"),
            markdown_enabled=data.get("markdown_enabled", True),
            recovery_notification=data.get("recovery_notification", False),
            recovery_message=data.get("recovery_message"),
            action_command=data.get("action_command"),
            action_timeout=data.get("action_timeout", 30)
        )


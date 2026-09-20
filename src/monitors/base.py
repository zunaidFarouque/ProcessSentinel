import uuid
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
        recovery_message: Optional[str] = None
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
            "recovery_message": self.recovery_message
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseMonitor":
        raise NotImplementedError

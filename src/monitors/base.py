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
        markdown_enabled: bool = True
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
            "markdown_enabled": self.markdown_enabled
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseMonitor":
        raise NotImplementedError

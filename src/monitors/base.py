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
        monitor_id: Optional[str] = None
    ):
        self.id = monitor_id or f"mon-{uuid.uuid4().hex[:8]}"
        self.name = name.strip()
        self.interval_seconds = max(5, int(interval_seconds))
        self.channel_id = channel_id
        self.enabled = enabled

        self.last_check_time: float = 0.0
        self.status_text: str = "Initialized"
        self.status_level: str = "idle"  # "ok", "warning", "critical", "idle"

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
            "enabled": self.enabled
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseMonitor":
        raise NotImplementedError

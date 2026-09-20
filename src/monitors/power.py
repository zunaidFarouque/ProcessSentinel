import psutil
from typing import Optional, Dict, Any
from monitors.base import BaseMonitor

class PowerMonitor(BaseMonitor):
    """
    Monitors system power status and UPS/battery health:
      - Detects AC mains power loss (unplugged / running on battery).
      - Warns if battery charge falls below critical threshold.
      - Gracefully detects desktop workstations without battery.
      - Can execute emergency actions (e.g. graceful database/service shutdown).
    """
    monitor_type = "PowerMonitor"
    display_name = "Power & Battery Status"

    def __init__(
        self,
        name: str,
        alert_on_battery: bool = True,
        battery_threshold: Optional[float] = 20.0,
        message: str = "Power Alert: {status_detail}",
        interval_seconds: int = 60,
        channel_id: Optional[str] = None,
        enabled: bool = True,
        monitor_id: Optional[str] = None,
        priority: int = 4,
        tags: str = "battery,warning",
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
        self.alert_on_battery = bool(alert_on_battery)
        self.battery_threshold = float(battery_threshold) if battery_threshold is not None else None
        self.message = message
        self.alerted: bool = False

    def check(self, engine, channel_registry) -> None:
        try:
            battery = psutil.sensors_battery()
        except Exception as e:
            self.status_text = f"Error reading battery: {e}"
            self.status_level = "warning"
            return

        if battery is None:
            self.status_text = "OK: Running on AC power (No battery detected)"
            self.status_level = "ok"
            self.alerted = False
            return

        ac_unplugged = (battery.power_plugged is False)
        low_battery = (self.battery_threshold is not None and battery.percent <= self.battery_threshold)

        triggered = (self.alert_on_battery and ac_unplugged) or low_battery

        if triggered:
            if ac_unplugged and low_battery:
                status_detail = f"AC power unplugged and battery low ({battery.percent:.0f}% <= {self.battery_threshold:.0f}%)"
            elif ac_unplugged:
                status_detail = f"AC power unplugged, running on battery ({battery.percent:.0f}%)"
            else:
                status_detail = f"Battery low at {battery.percent:.0f}% (threshold: {self.battery_threshold:.0f}%)"

            if not self.alerted:
                msg = self.message.format(
                    name=self.name,
                    percent=battery.percent,
                    power_plugged=battery.power_plugged,
                    threshold=self.battery_threshold,
                    status_detail=status_detail
                )
                title = self.format_title(
                    f"{self.name}: Power Alert",
                    percent=battery.percent,
                    power_plugged=battery.power_plugged,
                    threshold=self.battery_threshold,
                    status_detail=status_detail
                )
                if channel_registry:
                    channel_registry.send_alert(
                        channel_id=self.channel_id,
                        message=msg,
                        title=title,
                        tags=self.tags or "battery,warning",
                        priority=self.priority,
                        click_url=self.click_url,
                        markdown=self.markdown_enabled
                    )
                self.execute_trigger_action(engine)
                self.alerted = True

            self.status_text = f"Triggered: {status_detail}"
            self.status_level = "warning"
        else:
            if self.alerted and self.recovery_notification:
                rec_msg = self.recovery_message or f"Power restored: AC connected, battery at {battery.percent:.0f}%."
                rec_title = self.format_title(
                    f"{self.name}: Power Restored",
                    percent=battery.percent,
                    power_plugged=battery.power_plugged
                )
                self.send_recovery_alert(channel_registry, message=rec_msg, title=rec_title, tags="white_check_mark,battery")

            self.alerted = False
            ac_str = "AC plugged in" if battery.power_plugged else "Battery"
            self.status_text = f"OK: {battery.percent:.0f}% ({ac_str})"
            self.status_level = "ok"

    def reset_state(self) -> None:
        self.alerted = False
        self.status_text = "State Reset"
        self.status_level = "idle"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "alert_on_battery": self.alert_on_battery,
            "battery_threshold": self.battery_threshold,
            "message": self.message
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PowerMonitor":
        return cls(
            name=data.get("name", "Power Monitor"),
            alert_on_battery=data.get("alert_on_battery", True),
            battery_threshold=data.get("battery_threshold", 20.0),
            message=data.get("message", "Power Alert: {status_detail}"),
            interval_seconds=data.get("interval_seconds", 60),
            channel_id=data.get("channel_id"),
            enabled=data.get("enabled", True),
            monitor_id=data.get("id"),
            priority=data.get("priority", 4),
            tags=data.get("tags", "battery,warning"),
            title_template=data.get("title_template"),
            click_url=data.get("click_url"),
            markdown_enabled=data.get("markdown_enabled", True),
            recovery_notification=data.get("recovery_notification", False),
            recovery_message=data.get("recovery_message"),
            action_command=data.get("action_command"),
            action_timeout=data.get("action_timeout", 30)
        )

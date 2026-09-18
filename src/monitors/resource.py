import psutil
from typing import Optional, Dict, Any
from monitors.base import BaseMonitor

class ResourceMonitor(BaseMonitor):
    """
    Monitors CPU % or RAM consumption of a process:
      - CPU floor check (e.g. CPU < 5% = silent hang / zombie state)
      - RAM ceiling check (e.g. RAM > 16000 MB = memory leak)
    """
    monitor_type = "ResourceMonitor"
    display_name = "Process Resource Usage (CPU % / RAM MB)"

    def __init__(
        self,
        name: str,
        target: str,
        metric: str = "cpu_percent",
        condition: str = "below",
        threshold: float = 5.0,
        message: str = "Process '{target}' {metric} is {val:.1f} ({condition} {threshold}).",
        interval_seconds: int = 60,
        channel_id: Optional[str] = None,
        enabled: bool = True,
        monitor_id: Optional[str] = None
    ):
        super().__init__(name, interval_seconds, channel_id, enabled, monitor_id)
        self.target = target.strip()
        self.metric = metric
        self.condition = condition
        self.threshold = float(threshold)
        self.message = message
        self.alerted: bool = False

    def check(self, engine, channel_registry) -> None:
        target_lower = self.target.lower()
        matched_procs = []
        for proc in psutil.process_iter(["name", "cpu_percent", "memory_info"]):
            try:
                pname = (proc.info.get("name") or "").lower()
                if target_lower in pname:
                    matched_procs.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if not matched_procs:
            self.status_text = f"Idle: '{self.target}' not running"
            self.status_level = "idle"
            return

        total_cpu = 0.0
        total_ram_mb = 0.0
        for p in matched_procs:
            try:
                total_cpu += p.cpu_percent(interval=0.1)
                mem = p.memory_info()
                total_ram_mb += mem.rss / (1024 * 1024)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        val = total_cpu if self.metric == "cpu_percent" else total_ram_mb
        unit = "%" if self.metric == "cpu_percent" else "MB"

        triggered = False
        if self.condition == "below" and val < self.threshold:
            triggered = True
        elif self.condition == "above" and val > self.threshold:
            triggered = True

        if triggered:
            if not self.alerted:
                msg = self.message.format(
                    target=self.target,
                    metric=self.metric,
                    val=val,
                    condition=self.condition,
                    threshold=self.threshold
                )
                channel_registry.send_alert(
                    channel_id=self.channel_id,
                    message=msg,
                    title=f"{self.name}: Resource Alert",
                    tags="chart_with_upwards_trend" if self.condition == "above" else "chart_with_downwards_trend",
                    priority=4
                )
                self.alerted = True
            self.status_text = f"Triggered: {self.target} {self.metric}={val:.1f}{unit} ({self.condition} {self.threshold}{unit})"
            self.status_level = "warning"
        else:
            self.alerted = False
            self.status_text = f"OK: {self.target} {self.metric}={val:.1f}{unit}"
            self.status_level = "ok"

    def reset_state(self) -> None:
        self.alerted = False
        self.status_text = "State Reset"
        self.status_level = "idle"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "target": self.target,
            "metric": self.metric,
            "condition": self.condition,
            "threshold": self.threshold,
            "message": self.message
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceMonitor":
        return cls(
            name=data.get("name", "Resource Monitor"),
            target=data.get("target", ""),
            metric=data.get("metric", "cpu_percent"),
            condition=data.get("condition", "below"),
            threshold=data.get("threshold", 5.0),
            message=data.get("message", "Process '{target}' {metric} is {val:.1f} ({condition} {threshold})."),
            interval_seconds=data.get("interval_seconds", 60),
            channel_id=data.get("channel_id"),
            enabled=data.get("enabled", True),
            monitor_id=data.get("id")
        )

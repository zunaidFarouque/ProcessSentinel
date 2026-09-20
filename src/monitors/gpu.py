import subprocess
from typing import Optional, Dict, Any
from monitors.base import BaseMonitor

class GPUMonitor(BaseMonitor):
    """
    Monitors NVIDIA GPU health, VRAM, and temperatures via nvidia-smi:
      - Temperature ceiling (e.g. Temp > 85°C = throttling or fan failure)
      - VRAM leak ceiling (e.g. VRAM Used > 14000 MB)
      - VRAM minimum floor (e.g. VRAM Free < 1000 MB = Out-of-Memory imminent)
      - GPU compute load / utilization percentage
    """
    monitor_type = "GPUMonitor"
    display_name = "GPU VRAM & Temperature"

    def __init__(
        self,
        name: str,
        gpu_index: int = 0,
        metric: str = "temperature",
        condition: str = "above",
        threshold: float = 85.0,
        message: str = "GPU {gpu_index} {metric} is {val:.1f}{unit} ({condition} {threshold:.1f}{unit}).",
        interval_seconds: int = 60,
        channel_id: Optional[str] = None,
        enabled: bool = True,
        monitor_id: Optional[str] = None,
        priority: int = 4,
        tags: str = "",
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
        self.gpu_index = int(gpu_index)
        self.metric = metric
        self.condition = condition
        self.threshold = float(threshold)
        self.message = message
        self.alerted: bool = False

    def _get_unit(self) -> str:
        unit_map = {
            "temperature": "°C",
            "vram_used_mb": "MB",
            "vram_free_mb": "MB",
            "gpu_util_percent": "%"
        }
        return unit_map.get(self.metric, "")

    def check(self, engine, channel_registry) -> None:
        cmd = [
            "nvidia-smi",
            "--query-gpu=index,utilization.gpu,utilization.memory,memory.total,memory.used,memory.free,temperature.gpu",
            "--format=csv,noheader,nounits"
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                errors="replace"
            )
            if proc.returncode != 0:
                self.status_text = "Error: nvidia-smi unavailable"
                self.status_level = "warning"
                return
            output = proc.stdout
        except (FileNotFoundError, subprocess.SubprocessError, Exception):
            self.status_text = "Error: nvidia-smi unavailable"
            self.status_level = "warning"
            return

        gpu_data = {}
        for line in output.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 7:
                try:
                    idx = int(parts[0])
                    gpu_data[idx] = {
                        "gpu_util_percent": float(parts[1]),
                        "vram_util_percent": float(parts[2]),
                        "vram_total_mb": float(parts[3]),
                        "vram_used_mb": float(parts[4]),
                        "vram_free_mb": float(parts[5]),
                        "temperature": float(parts[6]),
                    }
                except ValueError:
                    continue

        if self.gpu_index not in gpu_data:
            self.status_text = f"Error: GPU {self.gpu_index} not found"
            self.status_level = "warning"
            return

        metrics = gpu_data[self.gpu_index]
        val = metrics.get(self.metric, 0.0)
        unit = self._get_unit()

        triggered = False
        if self.condition == "above" and val > self.threshold:
            triggered = True
        elif self.condition == "below" and val < self.threshold:
            triggered = True

        if triggered:
            if not self.alerted:
                msg = self.message.format(
                    name=self.name,
                    gpu_index=self.gpu_index,
                    metric=self.metric,
                    val=val,
                    unit=unit,
                    condition=self.condition,
                    threshold=self.threshold
                )
                default_tag = "fire,warning" if self.metric == "temperature" else "warning,bar_chart"
                tags = self.tags or default_tag
                title = self.format_title(
                    f"{self.name}: GPU {self.gpu_index} Alert",
                    gpu_index=self.gpu_index,
                    metric=self.metric,
                    val=val,
                    unit=unit,
                    condition=self.condition,
                    threshold=self.threshold
                )
                if channel_registry:
                    channel_registry.send_alert(
                        channel_id=self.channel_id,
                        message=msg,
                        title=title,
                        tags=tags,
                        priority=self.priority,
                        click_url=self.click_url,
                        markdown=self.markdown_enabled
                    )
                self.execute_trigger_action(engine)
                self.alerted = True
            self.status_text = f"Triggered: GPU {self.gpu_index} {self.metric}={val:.1f}{unit} ({self.condition} {self.threshold:.1f}{unit})"
            self.status_level = "warning"
        else:
            if self.alerted and self.recovery_notification:
                rec_msg = self.recovery_message or f"GPU {self.gpu_index} {self.metric} returned to normal ({val:.1f}{unit})."
                rec_title = self.format_title(
                    f"{self.name}: Recovered",
                    gpu_index=self.gpu_index,
                    metric=self.metric,
                    val=val,
                    unit=unit
                )
                self.send_recovery_alert(channel_registry, message=rec_msg, title=rec_title, tags="white_check_mark,recycle")
            self.alerted = False
            self.status_text = f"OK: GPU {self.gpu_index} {self.metric}={val:.1f}{unit}"
            self.status_level = "ok"

    def reset_state(self) -> None:
        self.alerted = False
        self.status_text = "State Reset"
        self.status_level = "idle"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "gpu_index": self.gpu_index,
            "metric": self.metric,
            "condition": self.condition,
            "threshold": self.threshold,
            "message": self.message
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GPUMonitor":
        return cls(
            name=data.get("name", "GPU Monitor"),
            gpu_index=data.get("gpu_index", 0),
            metric=data.get("metric", "temperature"),
            condition=data.get("condition", "above"),
            threshold=data.get("threshold", 85.0),
            message=data.get("message", "GPU {gpu_index} {metric} is {val:.1f}{unit} ({condition} {threshold:.1f}{unit})."),
            interval_seconds=data.get("interval_seconds", 60),
            channel_id=data.get("channel_id"),
            enabled=data.get("enabled", True),
            monitor_id=data.get("id"),
            priority=data.get("priority", 4),
            tags=data.get("tags", ""),
            title_template=data.get("title_template"),
            click_url=data.get("click_url"),
            markdown_enabled=data.get("markdown_enabled", True),
            recovery_notification=data.get("recovery_notification", False),
            recovery_message=data.get("recovery_message"),
            action_command=data.get("action_command"),
            action_timeout=data.get("action_timeout", 30)
        )

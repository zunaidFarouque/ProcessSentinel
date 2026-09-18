import socket
import requests
from typing import Optional, Dict, Any
from monitors.base import BaseMonitor

class HTTPEndpointMonitor(BaseMonitor):
    """Pings a local or remote URL to ensure web services/APIs are online."""
    monitor_type = "HTTPEndpoint"
    display_name = "HTTP / Web Endpoint Check"

    def __init__(
        self,
        name: str,
        url: str,
        expected_status: int = 200,
        timeout_seconds: float = 5.0,
        message: str = "HTTP Check failed for {url}! Status: {status}, Error: {error}",
        interval_seconds: int = 60,
        channel_id: Optional[str] = None,
        enabled: bool = True,
        monitor_id: Optional[str] = None
    ):
        super().__init__(name, interval_seconds, channel_id, enabled, monitor_id)
        self.url = url.strip()
        self.expected_status = int(expected_status)
        self.timeout_seconds = float(timeout_seconds)
        self.message = message
        self.alerted: bool = False

    def check(self, engine, channel_registry) -> None:
        err = ""
        status_code = None
        try:
            resp = requests.get(self.url, timeout=self.timeout_seconds)
            status_code = resp.status_code
        except Exception as e:
            err = str(e)

        failed = (status_code != self.expected_status)
        if failed:
            if not self.alerted:
                msg = self.message.format(url=self.url, status=status_code or "Down", error=err or "Unexpected status")
                channel_registry.send_alert(
                    channel_id=self.channel_id,
                    message=msg,
                    title=f"{self.name}: HTTP Offline",
                    tags="globe_with_meridians,warning",
                    priority=4
                )
                self.alerted = True
            self.status_text = f"Offline: {status_code or 'Failed'} ({err[:25]})"
            self.status_level = "warning"
        else:
            self.alerted = False
            self.status_text = f"OK: Status {status_code}"
            self.status_level = "ok"

    def reset_state(self) -> None:
        self.alerted = False
        self.status_text = "State Reset"
        self.status_level = "idle"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "url": self.url,
            "expected_status": self.expected_status,
            "timeout_seconds": self.timeout_seconds,
            "message": self.message
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HTTPEndpointMonitor":
        return cls(
            name=data.get("name", "HTTP Endpoint Monitor"),
            url=data.get("url", ""),
            expected_status=data.get("expected_status", 200),
            timeout_seconds=data.get("timeout_seconds", 5.0),
            message=data.get("message", "HTTP Check failed for {url}!"),
            interval_seconds=data.get("interval_seconds", 60),
            channel_id=data.get("channel_id"),
            enabled=data.get("enabled", True),
            monitor_id=data.get("id")
        )


class LocalPortMonitor(BaseMonitor):
    """Checks if a local TCP port (e.g. 5432 Postgres, 6379 Redis) is listening."""
    monitor_type = "LocalPort"
    display_name = "Local Network Port Check"

    def __init__(
        self,
        name: str,
        port: int,
        host: str = "127.0.0.1",
        message: str = "Port {port} on {host} is unreachable!",
        interval_seconds: int = 60,
        channel_id: Optional[str] = None,
        enabled: bool = True,
        monitor_id: Optional[str] = None
    ):
        super().__init__(name, interval_seconds, channel_id, enabled, monitor_id)
        self.port = int(port)
        self.host = host.strip() or "127.0.0.1"
        self.message = message
        self.alerted: bool = False

    def check(self, engine, channel_registry) -> None:
        is_open = False
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        try:
            s.connect((self.host, self.port))
            is_open = True
        except Exception:
            is_open = False
        finally:
            s.close()

        if not is_open:
            if not self.alerted:
                msg = self.message.format(port=self.port, host=self.host)
                channel_registry.send_alert(
                    channel_id=self.channel_id,
                    message=msg,
                    title=f"{self.name}: Port Down",
                    tags="electric_plug,warning",
                    priority=4
                )
                self.alerted = True
            self.status_text = f"Down: Port {self.port} closed"
            self.status_level = "warning"
        else:
            self.alerted = False
            self.status_text = f"OK: Port {self.port} listening"
            self.status_level = "ok"

    def reset_state(self) -> None:
        self.alerted = False
        self.status_text = "State Reset"
        self.status_level = "idle"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "port": self.port,
            "host": self.host,
            "message": self.message
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LocalPortMonitor":
        return cls(
            name=data.get("name", "Local Port Monitor"),
            port=data.get("port", 5432),
            host=data.get("host", "127.0.0.1"),
            message=data.get("message", "Port {port} on {host} is unreachable!"),
            interval_seconds=data.get("interval_seconds", 60),
            channel_id=data.get("channel_id"),
            enabled=data.get("enabled", True),
            monitor_id=data.get("id")
        )

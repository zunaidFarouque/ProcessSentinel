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
        monitor_id: Optional[str] = None,
        priority: int = 4,
        tags: str = "globe_with_meridians,warning",
        title_template: Optional[str] = None,
        click_url: Optional[str] = None,
        markdown_enabled: bool = True,
        recovery_notification: bool = False,
        recovery_message: Optional[str] = None
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
            recovery_message=recovery_message
        )
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
                title = self.format_title(f"{self.name}: HTTP Offline", url=self.url, status=status_code or "Down", error=err or "Unexpected status")
                click = self.click_url or (self.url if self.url.startswith("http") else None)
                channel_registry.send_alert(
                    channel_id=self.channel_id,
                    message=msg,
                    title=title,
                    tags=self.tags,
                    priority=self.priority,
                    click_url=click,
                    markdown=self.markdown_enabled
                )
                self.alerted = True
            self.status_text = f"Offline: {status_code or 'Failed'} ({err[:25]})"
            self.status_level = "warning"
        else:
            if self.alerted and self.recovery_notification:
                rec_msg = self.recovery_message or f"HTTP Check recovered for {self.url}! Status: {status_code}"
                rec_title = self.format_title(f"{self.name}: Recovered", url=self.url, status=status_code)
                self.send_recovery_alert(channel_registry, message=rec_msg, title=rec_title, tags="white_check_mark,recycle")
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
            monitor_id=data.get("id"),
            priority=data.get("priority", 4),
            tags=data.get("tags", "globe_with_meridians,warning"),
            title_template=data.get("title_template"),
            click_url=data.get("click_url"),
            markdown_enabled=data.get("markdown_enabled", True),
            recovery_notification=data.get("recovery_notification", False),
            recovery_message=data.get("recovery_message")
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
        monitor_id: Optional[str] = None,
        priority: int = 4,
        tags: str = "electric_plug,warning",
        title_template: Optional[str] = None,
        click_url: Optional[str] = None,
        markdown_enabled: bool = True,
        recovery_notification: bool = False,
        recovery_message: Optional[str] = None
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
            recovery_message=recovery_message
        )
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
                title = self.format_title(f"{self.name}: Port Down", port=self.port, host=self.host)
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
            self.status_text = f"Down: Port {self.port} closed"
            self.status_level = "warning"
        else:
            if self.alerted and self.recovery_notification:
                rec_msg = self.recovery_message or f"Port {self.port} on {self.host} is now open and reachable!"
                rec_title = self.format_title(f"{self.name}: Port Recovered", port=self.port, host=self.host)
                self.send_recovery_alert(channel_registry, message=rec_msg, title=rec_title, tags="white_check_mark,recycle")
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
            monitor_id=data.get("id"),
            priority=data.get("priority", 4),
            tags=data.get("tags", "electric_plug,warning"),
            title_template=data.get("title_template"),
            click_url=data.get("click_url"),
            markdown_enabled=data.get("markdown_enabled", True),
            recovery_notification=data.get("recovery_notification", False),
            recovery_message=data.get("recovery_message")
        )

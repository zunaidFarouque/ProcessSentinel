import uuid
import requests

from typing import Optional, List, Dict, Any

class NotificationChannel:
    """Represents a named notification endpoint (e.g. 'My Phone', 'Telegram Bot', 'Discord Webhook')."""
    def __init__(
        self,
        name: str,
        url: str = "",
        channel_id: Optional[str] = None,
        channel_type: str = "ntfy",
        auth_token: Optional[str] = None,
        chat_id: Optional[str] = None
    ):
        self.id = channel_id or f"chan-{uuid.uuid4().hex[:8]}"
        self.name = name.strip() if name else "Unnamed Channel"
        self.url = url.strip() if url else ""
        self.channel_type = (channel_type or "ntfy").strip().lower()
        self.auth_token = auth_token.strip() if auth_token else None
        self.chat_id = str(chat_id).strip() if chat_id is not None and str(chat_id).strip() else None

    def send(
        self,
        message: str,
        title: str = "ProcessSentinel Alert",
        tags: str = "",
        priority: int = 3,
        click_url: Optional[str] = None,
        markdown: bool = True,
        actions: Optional[str] = None
    ) -> bool:
        """Dispatches notification according to channel_type."""
        if self.channel_type == "telegram":
            return self._send_telegram(message, title)
        elif self.channel_type == "discord":
            return self._send_discord(message, title)
        elif self.channel_type == "slack":
            return self._send_slack(message, title)
        else:
            return self._send_ntfy(message, title, tags, priority, click_url, markdown, actions)

    def _send_ntfy(
        self,
        message: str,
        title: str,
        tags: str,
        priority: int,
        click_url: Optional[str],
        markdown: bool,
        actions: Optional[str]
    ) -> bool:
        """Sends an HTTP POST notification to ntfy.sh with timeout and safe exception handling."""
        if not self.url:
            return False

        headers = {
            "Title": title,
            "Priority": str(priority)
        }
        if tags:
            headers["Tags"] = tags
        if click_url:
            headers["Click"] = click_url
        if markdown:
            headers["Markdown"] = "yes"
        if actions:
            headers["Actions"] = actions
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        try:
            response = requests.post(
                self.url,
                data=message.encode("utf-8"),
                headers=headers,
                timeout=5
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[Channel '{self.name}'] Network error sending to {self.url}: {e}")
            return False

    def _send_telegram(self, message: str, title: str) -> bool:
        """Sends an HTTP POST notification via Telegram Bot API."""
        if not self.chat_id:
            print(f"[Channel '{self.name}'] Telegram error: missing chat_id")
            return False

        endpoint = self.url
        if not endpoint or ("api.telegram.org" not in endpoint and not endpoint.startswith("http")):
            if self.auth_token:
                endpoint = f"https://api.telegram.org/bot{self.auth_token}/sendMessage"
            else:
                endpoint = self.url
        if not endpoint:
            print(f"[Channel '{self.name}'] Telegram error: missing bot token or API URL")
            return False

        text = f"*{title}*\n\n{message}" if title else message
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }

        try:
            response = requests.post(
                endpoint,
                json=payload,
                timeout=5
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[Channel '{self.name}'] Network error sending to Telegram ({endpoint}): {e}")
            return False

    def _send_discord(self, message: str, title: str) -> bool:
        """Sends an HTTP POST notification to a Discord webhook."""
        if not self.url:
            return False

        content = f"**{title}**\n{message}" if title else message
        payload = {"content": content}

        try:
            response = requests.post(
                self.url,
                json=payload,
                timeout=5
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[Channel '{self.name}'] Network error sending to Discord ({self.url}): {e}")
            return False

    def _send_slack(self, message: str, title: str) -> bool:
        """Sends an HTTP POST notification to a Slack webhook."""
        if not self.url:
            return False

        text = f"*{title}*\n{message}" if title else message
        payload = {"text": text}

        try:
            response = requests.post(
                self.url,
                json=payload,
                timeout=5
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[Channel '{self.name}'] Network error sending to Slack ({self.url}): {e}")
            return False

    def to_dict(self) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "channel_type": self.channel_type
        }
        if self.auth_token:
            data["auth_token"] = self.auth_token
        if self.chat_id:
            data["chat_id"] = self.chat_id
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "NotificationChannel":
        return cls(
            name=data.get("name", "Unnamed Channel"),
            url=data.get("url", ""),
            channel_id=data.get("id"),
            channel_type=data.get("channel_type", "ntfy"),
            auth_token=data.get("auth_token"),
            chat_id=data.get("chat_id")
        )


class ChannelRegistry:
    """Manages all configured notification channels and default routing."""
    def __init__(self, channels=None, default_channel_id=None):
        self.channels = channels or []
        self.default_channel_id = default_channel_id

        # Guarantee at least one fallback channel exists
        if not self.channels:
            default_chan = NotificationChannel(
                name="Primary Phone",
                url="https://ntfy.sh/mzf_FAU_GRA_Monitoring",
                channel_id="chan-default"
            )
            self.channels.append(default_chan)
            self.default_channel_id = default_chan.id

        if not self.default_channel_id and self.channels:
            self.default_channel_id = self.channels[0].id

    def get_channel(self, channel_id: str = None) -> NotificationChannel:
        """Returns the channel matching channel_id, or falls back to the default channel."""
        if channel_id:
            for chan in self.channels:
                if chan.id == channel_id:
                    return chan
        for chan in self.channels:
            if chan.id == self.default_channel_id:
                return chan
        return self.channels[0] if self.channels else NotificationChannel("Default", "")

    def get_default_channel(self) -> NotificationChannel:
        return self.get_channel(self.default_channel_id)

    def set_default(self, channel_id: str):
        if any(c.id == channel_id for c in self.channels):
            self.default_channel_id = channel_id

    def add_channel(
        self,
        name: str,
        url: str = "",
        auth_token: Optional[str] = None,
        channel_type: str = "ntfy",
        chat_id: Optional[str] = None
    ) -> NotificationChannel:
        chan = NotificationChannel(
            name=name,
            url=url,
            channel_type=channel_type,
            auth_token=auth_token,
            chat_id=chat_id
        )
        self.channels.append(chan)
        if not self.default_channel_id:
            self.default_channel_id = chan.id
        return chan

    def remove_channel(self, channel_id: str):
        self.channels = [c for c in self.channels if c.id != channel_id]
        if self.default_channel_id == channel_id:
            self.default_channel_id = self.channels[0].id if self.channels else None

    def send_alert(
        self,
        channel_id: str = None,
        message: str = "",
        title: str = "Alert",
        tags: str = "",
        priority: int = 3,
        click_url: Optional[str] = None,
        markdown: bool = True,
        actions: Optional[str] = None
    ) -> bool:
        channel = self.get_channel(channel_id)
        return channel.send(
            message=message,
            title=title,
            tags=tags,
            priority=priority,
            click_url=click_url,
            markdown=markdown,
            actions=actions
        )

    def to_dict(self) -> dict:
        return {
            "channels": [c.to_dict() for c in self.channels],
            "default_channel_id": self.default_channel_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChannelRegistry":
        channels = [NotificationChannel.from_dict(c) for c in data.get("channels", [])]
        default_id = data.get("default_channel_id")
        return cls(channels=channels, default_channel_id=default_id)

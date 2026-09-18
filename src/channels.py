import uuid
import requests

class NotificationChannel:
    """Represents a named notification endpoint (e.g. 'My Phone', 'Lab IT')."""
    def __init__(self, name: str, url: str, channel_id: str = None):
        self.id = channel_id or f"chan-{uuid.uuid4().hex[:8]}"
        self.name = name.strip()
        self.url = url.strip()

    def send(self, message: str, title: str = "ProcessSentinel Alert", tags: str = "", priority: int = 3) -> bool:
        """Sends an HTTP POST notification to ntfy.sh with timeout and safe exception handling."""
        if not self.url:
            return False

        headers = {
            "Title": title,
            "Priority": str(priority)
        }
        if tags:
            headers["Tags"] = tags

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

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NotificationChannel":
        return cls(
            name=data.get("name", "Unnamed Channel"),
            url=data.get("url", ""),
            channel_id=data.get("id")
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

    def add_channel(self, name: str, url: str) -> NotificationChannel:
        chan = NotificationChannel(name, url)
        self.channels.append(chan)
        if not self.default_channel_id:
            self.default_channel_id = chan.id
        return chan

    def remove_channel(self, channel_id: str):
        self.channels = [c for c in self.channels if c.id != channel_id]
        if self.default_channel_id == channel_id:
            self.default_channel_id = self.channels[0].id if self.channels else None

    def send_alert(self, channel_id: str = None, message: str = "", title: str = "Alert", tags: str = "", priority: int = 3) -> bool:
        channel = self.get_channel(channel_id)
        return channel.send(message=message, title=title, tags=tags, priority=priority)

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

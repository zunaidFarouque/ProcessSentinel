import sys
import os
import pytest

# Ensure src/ is on sys.path for all pytest tests
sys.path.insert(0, os.path.abspath("src"))

from channels import ChannelRegistry, NotificationChannel

class MockChannelRegistry(ChannelRegistry):
    """Test double recording sent alerts without network calls."""
    def __init__(self):
        super().__init__()
        self.sent_alerts = []

    def send_alert(self, channel_id=None, message="", title="Alert", tags="", priority=3):
        self.sent_alerts.append({
            "channel_id": channel_id,
            "message": message,
            "title": title,
            "tags": tags,
            "priority": priority
        })
        return True

@pytest.fixture
def mock_registry():
    return MockChannelRegistry()

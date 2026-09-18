import pytest
from unittest.mock import patch, MagicMock
from channels import NotificationChannel, ChannelRegistry

def test_channel_initialization():
    ch = NotificationChannel(name="Test Channel", url="https://ntfy.sh/test_topic")
    assert ch.name == "Test Channel"
    assert ch.url == "https://ntfy.sh/test_topic"
    assert ch.id.startswith("chan-")

def test_channel_send_network_call():
    ch = NotificationChannel(name="Test", url="https://ntfy.sh/test")
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        result = ch.send("Hello world", title="Alert Title", tags="warning", priority=4)
        assert result is True
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://ntfy.sh/test"
        assert kwargs["headers"]["Title"] == "Alert Title"
        assert kwargs["headers"]["Tags"] == "warning"
        assert kwargs["headers"]["Priority"] == "4"

def test_channel_network_exception_handling():
    import requests
    ch = NotificationChannel(name="Test", url="https://ntfy.sh/test")
    with patch("requests.post", side_effect=requests.RequestException("Connection error")):
        result = ch.send("Message")
        assert result is False

def test_channel_registry_default_fallback():
    reg = ChannelRegistry()
    assert len(reg.channels) == 1
    default_ch = reg.get_default_channel()
    assert default_ch is not None
    assert reg.get_channel("non-existent-id").id == default_ch.id

def test_channel_registry_add_remove_and_set_default():
    reg = ChannelRegistry()
    ch2 = reg.add_channel("Second Channel", "https://ntfy.sh/second")
    assert len(reg.channels) == 2

    reg.set_default(ch2.id)
    assert reg.get_default_channel().id == ch2.id

    reg.remove_channel(ch2.id)
    assert len(reg.channels) == 1
    assert reg.get_default_channel().id != ch2.id

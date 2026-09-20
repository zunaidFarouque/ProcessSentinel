import pytest
from unittest.mock import patch, MagicMock
import json
import requests

from channels import NotificationChannel, ChannelRegistry
from remote_actions import RemoteCommandListener
from engine import MonitorEngine
from monitors.process import ProcessInstanceMonitor


# =====================================================================
# TELEGRAM CHANNEL TESTS
# =====================================================================

def test_telegram_channel_send_success():
    channel = NotificationChannel(
        name="Telegram Alerts",
        url="",
        channel_type="telegram",
        auth_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        chat_id="987654321"
    )

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        ok = channel.send(
            message="ArcGIS batch completed with 0 errors.",
            title="Batch Complete",
            priority=3
        )

        assert ok is True
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/sendMessage"
        payload = kwargs.get("json", {})
        assert payload.get("chat_id") == "987654321"
        assert "*Batch Complete*" in payload.get("text", "")
        assert "ArcGIS batch completed with 0 errors." in payload.get("text", "")
        assert payload.get("parse_mode") == "Markdown"
        assert kwargs.get("timeout") == 5


def test_telegram_channel_custom_url():
    channel = NotificationChannel(
        name="Telegram Custom Proxy",
        url="https://telegram-proxy.internal.corp/botSECRET/sendMessage",
        channel_type="telegram",
        chat_id="-100123456789"
    )

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        ok = channel.send(message="Custom proxy test")
        assert ok is True
        args, kwargs = mock_post.call_args
        assert args[0] == "https://telegram-proxy.internal.corp/botSECRET/sendMessage"
        assert kwargs.get("json", {}).get("chat_id") == "-100123456789"


def test_telegram_channel_missing_chat_id():
    channel = NotificationChannel(
        name="Telegram Bad",
        url="",
        channel_type="telegram",
        auth_token="123456:ABC",
        chat_id=None
    )

    with patch("requests.post") as mock_post:
        ok = channel.send(message="Should fail")
        assert ok is False
        mock_post.assert_not_called()


def test_telegram_channel_network_error():
    channel = NotificationChannel(
        name="Telegram Error",
        url="",
        channel_type="telegram",
        auth_token="123456:ABC",
        chat_id="123"
    )

    with patch("requests.post", side_effect=requests.RequestException("Telegram API timeout")):
        ok = channel.send(message="Test")
        assert ok is False


# =====================================================================
# DISCORD CHANNEL TESTS
# =====================================================================

def test_discord_channel_send_success():
    channel = NotificationChannel(
        name="Discord IT Alerts",
        url="https://discord.internal/api/webhooks/123456789/mock_token",
        channel_type="discord"
    )

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        ok = channel.send(
            message="PostgreSQL disk free space below 10 GB!",
            title="Storage Warning",
            priority=4
        )

        assert ok is True
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://discord.internal/api/webhooks/123456789/mock_token"
        payload = kwargs.get("json", {})
        assert "**Storage Warning**" in payload.get("content", "")
        assert "PostgreSQL disk free space below 10 GB!" in payload.get("content", "")
        assert kwargs.get("timeout") == 5


def test_discord_channel_network_error():
    channel = NotificationChannel(
        name="Discord Error",
        url="https://discord.com/api/webhooks/123/xyz",
        channel_type="discord"
    )

    with patch("requests.post", side_effect=requests.RequestException("Discord 500")):
        ok = channel.send(message="Test message")
        assert ok is False


# =====================================================================
# SLACK CHANNEL TESTS
# =====================================================================

def test_slack_channel_send_success():
    channel = NotificationChannel(
        name="Slack Devops",
        url="https://hooks.slack.internal/services/mock_team/mock_bot/mock_secret",
        channel_type="slack"
    )

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        ok = channel.send(
            message="GPU Temperature reached 88C!",
            title="GPU Overheat Alert",
            priority=5
        )

        assert ok is True
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://hooks.slack.internal/services/mock_team/mock_bot/mock_secret"
        payload = kwargs.get("json", {})
        assert "*GPU Overheat Alert*" in payload.get("text", "")
        assert "GPU Temperature reached 88C!" in payload.get("text", "")
        assert kwargs.get("timeout") == 5


def test_slack_channel_network_error():
    channel = NotificationChannel(
        name="Slack Error",
        url="https://hooks.slack.com/services/T00/B00/X00",
        channel_type="slack"
    )

    with patch("requests.post", side_effect=requests.RequestException("Slack connection failed")):
        ok = channel.send(message="Test slack error")
        assert ok is False


# =====================================================================
# SERIALIZATION & BACKWARD COMPATIBILITY TESTS
# =====================================================================

def test_channel_serialization_all_types():
    ch_ntfy = NotificationChannel(name="Ntfy Primary", url="https://ntfy.sh/alerts", auth_token="tk_123")
    ch_tg = NotificationChannel(name="Telegram", url="", channel_type="telegram", auth_token="bot123", chat_id="chat999")
    ch_dc = NotificationChannel(name="Discord", url="https://discord.com/webhook", channel_type="discord")
    ch_sl = NotificationChannel(name="Slack", url="https://hooks.slack.com/services/x", channel_type="slack")

    # Roundtrip ntfy
    d_ntfy = ch_ntfy.to_dict()
    assert d_ntfy["channel_type"] == "ntfy"
    assert d_ntfy["auth_token"] == "tk_123"
    rec_ntfy = NotificationChannel.from_dict(d_ntfy)
    assert rec_ntfy.channel_type == "ntfy"
    assert rec_ntfy.auth_token == "tk_123"

    # Roundtrip telegram
    d_tg = ch_tg.to_dict()
    assert d_tg["channel_type"] == "telegram"
    assert d_tg["chat_id"] == "chat999"
    assert d_tg["auth_token"] == "bot123"
    rec_tg = NotificationChannel.from_dict(d_tg)
    assert rec_tg.channel_type == "telegram"
    assert rec_tg.chat_id == "chat999"
    assert rec_tg.auth_token == "bot123"

    # Roundtrip discord
    d_dc = ch_dc.to_dict()
    assert d_dc["channel_type"] == "discord"
    rec_dc = NotificationChannel.from_dict(d_dc)
    assert rec_dc.channel_type == "discord"

    # Roundtrip slack
    d_sl = ch_sl.to_dict()
    assert d_sl["channel_type"] == "slack"
    rec_sl = NotificationChannel.from_dict(d_sl)
    assert rec_sl.channel_type == "slack"


def test_channel_backward_compatibility_defaults():
    legacy_data = {
        "id": "chan-legacy",
        "name": "Legacy Topic",
        "url": "https://ntfy.sh/legacy"
    }
    chan = NotificationChannel.from_dict(legacy_data)
    assert chan.channel_type == "ntfy"
    assert chan.chat_id is None
    assert chan.auth_token is None


def test_channel_registry_with_multi_types():
    reg = ChannelRegistry()
    tg = reg.add_channel(
        name="Telegram Bot",
        url="",
        auth_token="tg_bot_token",
        channel_type="telegram",
        chat_id="12345"
    )
    dc = reg.add_channel(
        name="Discord Webhook",
        url="https://discord.com/api/webhooks/xyz",
        channel_type="discord"
    )

    assert len(reg.channels) == 3
    assert reg.get_channel(tg.id).channel_type == "telegram"
    assert reg.get_channel(dc.id).channel_type == "discord"

    # Test registry roundtrip
    reg_dict = reg.to_dict()
    reloaded_reg = ChannelRegistry.from_dict(reg_dict)
    assert len(reloaded_reg.channels) == 3
    assert reloaded_reg.get_channel(tg.id).chat_id == "12345"
    assert reloaded_reg.get_channel(dc.id).channel_type == "discord"


# =====================================================================
# REMOTE COMMAND LISTENER TESTS
# =====================================================================

def test_remote_command_listener_auth_success():
    channel_reg = ChannelRegistry()
    engine = MonitorEngine(channel_registry=channel_reg)
    mon = ProcessInstanceMonitor(name="Worker", target="worker.exe", monitor_id="mon-test-1")
    mon.alerted = True
    engine.add_monitor(mon)

    listener = RemoteCommandListener(engine=engine, auth_token="super_secret_cmd_key")

    cmd = {
        "action": "reset",
        "monitor_id": "mon-test-1",
        "token": "super_secret_cmd_key"
    }
    result = listener.handle_command(cmd)
    assert result["success"] is True
    assert result["action"] == "reset"
    assert mon.alerted is False


def test_remote_command_listener_auth_failure():
    channel_reg = ChannelRegistry()
    engine = MonitorEngine(channel_registry=channel_reg)
    mon = ProcessInstanceMonitor(name="Worker", target="worker.exe", monitor_id="mon-test-2")
    mon.triggered = True
    engine.add_monitor(mon)

    listener = RemoteCommandListener(engine=engine, auth_token="correct_token")

    # Mismatched token
    cmd = {
        "action": "reset",
        "monitor_id": "mon-test-2",
        "token": "wrong_token"
    }
    result = listener.handle_command(cmd)
    assert result["success"] is False
    assert result.get("error") == "Unauthorized"
    assert mon.triggered is True  # State was not reset


def test_remote_command_listener_run_action():
    channel_reg = ChannelRegistry()
    engine = MonitorEngine(channel_registry=channel_reg)
    mon = ProcessInstanceMonitor(
        name="Worker",
        target="worker.exe",
        monitor_id="mon-test-3",
        action_command="echo action_triggered"
    )
    engine.add_monitor(mon)

    listener = RemoteCommandListener(engine=engine, auth_token="secret")

    with patch.object(mon, "execute_action", return_value={"success": True, "returncode": 0}) as mock_act:
        cmd = {
            "action": "run_action",
            "monitor_id": "mon-test-3",
            "token": "secret"
        }
        result = listener.handle_command(cmd)
        assert result["success"] is True
        mock_act.assert_called_once()


def test_remote_command_listener_check_now():
    channel_reg = ChannelRegistry()
    engine = MonitorEngine(channel_registry=channel_reg)
    mon = ProcessInstanceMonitor(name="Worker", target="worker.exe", monitor_id="mon-test-4")
    engine.add_monitor(mon)

    listener = RemoteCommandListener(engine=engine)

    with patch.object(engine, "check_monitor_now") as mock_check:
        cmd = {
            "action": "check_now",
            "monitor_id": "mon-test-4"
        }
        result = listener.handle_command(cmd)
        assert result["success"] is True
        mock_check.assert_called_once_with("mon-test-4")


def test_remote_command_listener_invalid_json_and_unknown_action():
    channel_reg = ChannelRegistry()
    engine = MonitorEngine(channel_registry=channel_reg)
    listener = RemoteCommandListener(engine=engine)

    # Invalid JSON string
    res_bad_json = listener.handle_command("not-a-json-payload")
    assert res_bad_json["success"] is False

    # Unknown action
    res_unknown = listener.handle_command({"action": "self_destruct", "monitor_id": "123"})
    assert res_unknown["success"] is False
    assert "Unknown action" in res_unknown["error"]


# =====================================================================
# CHANNEL DIALOG & GUI TESTS
# =====================================================================

def test_channel_dialog_ui_switch_and_save():
    import customtkinter as ctk
    from gui.dialogs import ChannelDialog

    root = ctk.CTk()
    root.withdraw()

    saved_data = {}
    def on_save(name, url, token, ctype, chat_id, cid):
        saved_data.update({
            "name": name,
            "url": url,
            "token": token,
            "channel_type": ctype,
            "chat_id": chat_id,
            "cid": cid
        })

    dialog = ChannelDialog(root, channel=None, on_save=on_save)

    # 1. Verify default ntfy fields
    assert hasattr(dialog, "url_entry")
    assert hasattr(dialog, "token_entry")
    assert not hasattr(dialog, "chat_id_entry")

    # 2. Switch to Telegram
    dialog.type_var.set("Telegram Bot")
    dialog._on_type_changed("Telegram Bot")
    assert hasattr(dialog, "chat_id_entry")
    assert hasattr(dialog, "token_entry")

    # Fill Telegram fields and save
    dialog.name_entry.delete(0, "end")
    dialog.name_entry.insert(0, "My Telegram Bot")
    dialog.token_entry.delete(0, "end")
    dialog.token_entry.insert(0, "123456:bottoken")
    dialog.chat_id_entry.delete(0, "end")
    dialog.chat_id_entry.insert(0, "-100987654")

    dialog._save()

    assert saved_data["name"] == "My Telegram Bot"
    assert saved_data["channel_type"] == "telegram"
    assert saved_data["token"] == "123456:bottoken"
    assert saved_data["chat_id"] == "-100987654"

    try:
        root.destroy()
    except Exception:
        pass


def test_channel_dialog_discord_and_slack_switch():
    import customtkinter as ctk
    from gui.dialogs import ChannelDialog

    root = ctk.CTk()
    root.withdraw()

    dialog = ChannelDialog(root, channel=None)

    # Switch to Discord
    dialog.type_var.set("Discord Webhook")
    dialog._on_type_changed("Discord Webhook")
    assert hasattr(dialog, "url_entry")
    assert not hasattr(dialog, "chat_id_entry")

    # Switch to Slack
    dialog.type_var.set("Slack Webhook")
    dialog._on_type_changed("Slack Webhook")
    assert hasattr(dialog, "url_entry")
    assert not hasattr(dialog, "chat_id_entry")

    try:
        dialog.destroy()
        root.destroy()
    except Exception:
        pass


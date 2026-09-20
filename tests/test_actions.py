import subprocess
import pytest
from unittest.mock import patch, MagicMock
from monitors.base import BaseMonitor

class ConcreteMonitor(BaseMonitor):
    monitor_type = "Concrete"
    display_name = "Concrete Monitor"

    def check(self, engine, channel_registry) -> None:
        pass

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data.get("name", "Concrete"),
            interval_seconds=data.get("interval_seconds", 60),
            channel_id=data.get("channel_id"),
            enabled=data.get("enabled", True),
            monitor_id=data.get("id"),
            priority=data.get("priority", 3),
            tags=data.get("tags", ""),
            title_template=data.get("title_template"),
            click_url=data.get("click_url"),
            markdown_enabled=data.get("markdown_enabled", True),
            recovery_notification=data.get("recovery_notification", False),
            recovery_message=data.get("recovery_message"),
            action_command=data.get("action_command"),
            action_timeout=data.get("action_timeout", 30)
        )

def test_execute_trigger_action_no_command():
    mon = ConcreteMonitor(name="NoAction", action_command=None)
    engine = MagicMock()
    res = mon.execute_trigger_action(engine)
    assert res is None
    engine.log.assert_not_called()

    mon_empty = ConcreteMonitor(name="EmptyAction", action_command="   ")
    res_empty = mon_empty.execute_trigger_action(engine)
    assert res_empty is None
    engine.log.assert_not_called()

def test_execute_trigger_action_success():
    mon = ConcreteMonitor(name="RestartSvc", action_command="net stop Spooler", action_timeout=15)
    engine = MagicMock()

    mock_cp = subprocess.CompletedProcess(
        args="net stop Spooler",
        returncode=0,
        stdout="The Print Spooler service was stopped successfully.\n",
        stderr=""
    )

    with patch("subprocess.run", return_value=mock_cp) as mock_run:
        res = mon.execute_trigger_action(engine)
        mock_run.assert_called_once_with(
            "net stop Spooler",
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
            errors="replace"
        )
        assert "[Action: exit 0]" in res
        assert "Print Spooler service was stopped successfully" in res
        assert engine.log.call_count >= 2
        # Check that exit code and command execution were logged
        logged_msgs = [call.args[0] for call in engine.log.call_args_list]
        assert any("Executing action" in m for m in logged_msgs)
        assert any("exit 0" in m for m in logged_msgs)

def test_execute_trigger_action_nonzero_exit():
    mon = ConcreteMonitor(name="FailScript", action_command="exit 2", action_timeout=10)
    engine = MagicMock()

    mock_cp = subprocess.CompletedProcess(
        args="exit 2",
        returncode=2,
        stdout="",
        stderr="Access denied"
    )

    with patch("subprocess.run", return_value=mock_cp):
        res = mon.execute_trigger_action(engine)
        assert "[Action: exit 2]" in res
        assert "Access denied" in res
        logged_calls = engine.log.call_args_list
        assert any("exit 2" in call.args[0] for call in logged_calls)

def test_execute_trigger_action_timeout():
    mon = ConcreteMonitor(name="HangScript", action_command="sleep 100", action_timeout=5)
    engine = MagicMock()

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="sleep 100", timeout=5)):
        res = mon.execute_trigger_action(engine)
        assert "[Action: timeout" in res
        assert "5s" in res
        logged_calls = engine.log.call_args_list
        assert any("timed out" in call.args[0].lower() for call in logged_calls)

def test_execute_trigger_action_exception():
    mon = ConcreteMonitor(name="BadScript", action_command="bad_cmd", action_timeout=5)
    engine = MagicMock()

    with patch("subprocess.run", side_effect=OSError("System executable not found")):
        res = mon.execute_trigger_action(engine)
        assert "[Action: error]" in res
        assert "System executable not found" in res
        logged_calls = engine.log.call_args_list
        assert any("error" in call.args[0].lower() for call in logged_calls)

def test_action_serialization():
    mon = ConcreteMonitor(
        name="SerAction",
        action_command="powershell -File C:\\restart.ps1",
        action_timeout=45
    )
    d = mon.to_dict()
    assert d["action_command"] == "powershell -File C:\\restart.ps1"
    assert d["action_timeout"] == 45

    loaded = ConcreteMonitor.from_dict(d)
    assert loaded.action_command == "powershell -File C:\\restart.ps1"
    assert loaded.action_timeout == 45

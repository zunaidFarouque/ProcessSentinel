import time
import pytest
from engine import MonitorEngine
from monitors.base import BaseMonitor

class FlakyMonitor(BaseMonitor):
    monitor_type = "Flaky"
    def __init__(self, name="Flaky"):
        super().__init__(name=name, interval_seconds=5)
        self.check_count = 0

    def check(self, engine, channel_registry):
        self.check_count += 1
        if self.check_count == 1:
            raise RuntimeError("Simulated crash in monitor check!")
        self.status_text = "Recovered"
        self.status_level = "ok"

def test_engine_error_isolation(mock_registry):
    """Verifies that an unhandled exception in one monitor does not kill the engine."""
    flaky = FlakyMonitor()
    engine = MonitorEngine(channel_registry=mock_registry, monitors=[flaky])

    # First check raises exception
    engine._run_single_check(flaky)
    assert flaky.status_level == "warning"
    assert "Simulated crash" in flaky.status_text

    # Second check recovers
    engine._run_single_check(flaky)
    assert flaky.status_level == "ok"
    assert flaky.status_text == "Recovered"

def test_engine_start_stop(mock_registry):
    engine = MonitorEngine(channel_registry=mock_registry, monitors=[])
    assert not engine.is_running()
    engine.start()
    assert engine.is_running()
    time.sleep(0.1)
    engine.stop()
    assert not engine.is_running()

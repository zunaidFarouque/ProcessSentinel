import subprocess
import pytest
from unittest.mock import patch, MagicMock
from monitors.gpu import GPUMonitor

SAMPLE_NVIDIA_SMI_OUTPUT = """0, 25, 40, 8192, 4096, 4096, 72
"""

SAMPLE_MULTI_GPU_OUTPUT = """0, 20, 30, 8192, 2048, 6144, 60
1, 98, 90, 16384, 15000, 1384, 88
"""

def test_gpu_monitor_above_threshold_temperature(mock_registry):
    mon = GPUMonitor(
        name="GPU 0 Heat Guard",
        gpu_index=0,
        metric="temperature",
        condition="above",
        threshold=70.0
    )

    mock_cp = subprocess.CompletedProcess(
        args=["nvidia-smi"],
        returncode=0,
        stdout=SAMPLE_NVIDIA_SMI_OUTPUT,
        stderr=""
    )

    with patch("subprocess.run", return_value=mock_cp):
        mon.check(None, mock_registry)
        assert mon.status_level == "warning"
        assert "Triggered" in mon.status_text
        assert "72.0°C" in mon.status_text
        assert len(mock_registry.sent_alerts) == 1
        alert = mock_registry.sent_alerts[0]
        assert "72.0" in alert["message"]
        assert mon.alerted is True

def test_gpu_monitor_below_threshold_vram_free(mock_registry):
    mon = GPUMonitor(
        name="GPU 0 VRAM Floor",
        gpu_index=0,
        metric="vram_free_mb",
        condition="below",
        threshold=5000.0
    )

    mock_cp = subprocess.CompletedProcess(
        args=["nvidia-smi"],
        returncode=0,
        stdout=SAMPLE_NVIDIA_SMI_OUTPUT,
        stderr=""
    )

    with patch("subprocess.run", return_value=mock_cp):
        mon.check(None, mock_registry)
        assert mon.status_level == "warning"
        assert len(mock_registry.sent_alerts) == 1
        assert "4096.0MB" in mon.status_text

def test_gpu_monitor_ok_state(mock_registry):
    mon = GPUMonitor(
        name="Cool GPU",
        gpu_index=0,
        metric="temperature",
        condition="above",
        threshold=80.0
    )

    mock_cp = subprocess.CompletedProcess(
        args=["nvidia-smi"],
        returncode=0,
        stdout=SAMPLE_NVIDIA_SMI_OUTPUT,
        stderr=""
    )

    with patch("subprocess.run", return_value=mock_cp):
        mon.check(None, mock_registry)
        assert mon.status_level == "ok"
        assert "OK" in mon.status_text
        assert len(mock_registry.sent_alerts) == 0
        assert mon.alerted is False

def test_gpu_monitor_multi_gpu_indexing(mock_registry):
    mon = GPUMonitor(
        name="Second GPU Load",
        gpu_index=1,
        metric="gpu_util_percent",
        condition="above",
        threshold=90.0
    )

    mock_cp = subprocess.CompletedProcess(
        args=["nvidia-smi"],
        returncode=0,
        stdout=SAMPLE_MULTI_GPU_OUTPUT,
        stderr=""
    )

    with patch("subprocess.run", return_value=mock_cp):
        mon.check(None, mock_registry)
        assert mon.status_level == "warning"
        assert "98.0%" in mon.status_text
        assert len(mock_registry.sent_alerts) == 1
        assert "GPU 1" in mock_registry.sent_alerts[0]["title"]

def test_gpu_monitor_missing_gpu_index(mock_registry):
    mon = GPUMonitor(
        name="Missing GPU",
        gpu_index=3,
        metric="temperature",
        condition="above",
        threshold=80.0
    )

    mock_cp = subprocess.CompletedProcess(
        args=["nvidia-smi"],
        returncode=0,
        stdout=SAMPLE_NVIDIA_SMI_OUTPUT,
        stderr=""
    )

    with patch("subprocess.run", return_value=mock_cp):
        mon.check(None, mock_registry)
        assert mon.status_level == "warning"
        assert "GPU 3 not found" in mon.status_text

def test_gpu_monitor_nvidia_smi_unavailable_filenotfound(mock_registry):
    mon = GPUMonitor(name="No Nvidia")

    with patch("subprocess.run", side_effect=FileNotFoundError):
        mon.check(None, mock_registry)
        assert mon.status_text == "Error: nvidia-smi unavailable"
        assert mon.status_level == "warning"
        assert len(mock_registry.sent_alerts) == 0

def test_gpu_monitor_nvidia_smi_error_code(mock_registry):
    mon = GPUMonitor(name="Driver Crash")

    mock_cp = subprocess.CompletedProcess(
        args=["nvidia-smi"],
        returncode=12,
        stdout="",
        stderr="NVIDIA-SMI has failed"
    )

    with patch("subprocess.run", return_value=mock_cp):
        mon.check(None, mock_registry)
        assert mon.status_text == "Error: nvidia-smi unavailable"
        assert mon.status_level == "warning"

def test_gpu_monitor_recovery_and_debounce(mock_registry):
    mon = GPUMonitor(
        name="RecGPU",
        gpu_index=0,
        metric="temperature",
        condition="above",
        threshold=70.0,
        recovery_notification=True
    )

    hot_cp = subprocess.CompletedProcess(args=[], returncode=0, stdout="0, 50, 20, 8192, 4000, 4192, 85\n", stderr="")
    cool_cp = subprocess.CompletedProcess(args=[], returncode=0, stdout="0, 10, 10, 8192, 1000, 7192, 50\n", stderr="")

    with patch("subprocess.run", return_value=hot_cp):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 1
        assert mon.alerted is True

    # Debounce check
    with patch("subprocess.run", return_value=hot_cp):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 1

    # Recovery check
    with patch("subprocess.run", return_value=cool_cp):
        mon.check(None, mock_registry)
        assert len(mock_registry.sent_alerts) == 2
        rec_alert = mock_registry.sent_alerts[-1]
        assert rec_alert["priority"] == 3
        assert "white_check_mark,recycle" in rec_alert["tags"]
        assert mon.alerted is False

def test_gpu_monitor_trigger_action(mock_registry):
    mon = GPUMonitor(
        name="ActionGPU",
        gpu_index=0,
        metric="temperature",
        condition="above",
        threshold=70.0,
        action_command="reboot_gpu.bat"
    )

    hot_cp = subprocess.CompletedProcess(args=[], returncode=0, stdout="0, 50, 20, 8192, 4000, 4192, 85\n", stderr="")
    engine = MagicMock()

    with patch.object(mon, "execute_trigger_action") as mock_action:
        with patch("subprocess.run", return_value=hot_cp):
            mon.check(engine, mock_registry)
            mock_action.assert_called_once_with(engine)

def test_gpu_monitor_serialization():
    mon = GPUMonitor(
        name="SerGPU",
        gpu_index=1,
        metric="vram_used_mb",
        condition="above",
        threshold=12000.0,
        message="GPU VRAM high: {val}",
        action_command="clear_cache.bat",
        action_timeout=20
    )

    d = mon.to_dict()
    assert d["type"] == "GPUMonitor"
    assert d["gpu_index"] == 1
    assert d["metric"] == "vram_used_mb"
    assert d["threshold"] == 12000.0
    assert d["action_command"] == "clear_cache.bat"
    assert d["action_timeout"] == 20

    loaded = GPUMonitor.from_dict(d)
    assert loaded.name == "SerGPU"
    assert loaded.gpu_index == 1
    assert loaded.metric == "vram_used_mb"
    assert loaded.threshold == 12000.0
    assert loaded.action_command == "clear_cache.bat"
    assert loaded.action_timeout == 20

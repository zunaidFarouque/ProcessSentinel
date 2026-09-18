import pytest
from unittest.mock import patch, MagicMock
from monitors.resource import ResourceMonitor
from monitors.storage import DirectorySizeMonitor
from monitors.network import HTTPEndpointMonitor, LocalPortMonitor

def test_resource_monitor(mock_registry):
    mon = ResourceMonitor(name="CPU Guard", target="test_app.exe", metric="cpu_percent", condition="below", threshold=5.0)
    
    # Mock psutil process
    mock_p = MagicMock()
    mock_p.info = {"name": "test_app.exe"}
    mock_p.cpu_percent.return_value = 1.2
    
    with patch("psutil.process_iter", return_value=[mock_p]):
        mon.check(None, mock_registry)
        assert mon.status_level == "warning"
        assert len(mock_registry.sent_alerts) == 1
        assert "is 1.2" in mock_registry.sent_alerts[-1]["message"]

def test_directory_size_monitor(tmp_path, mock_registry):
    mon = DirectorySizeMonitor(name="Cache Watch", path=str(tmp_path), max_size_gb=0.000001) # tiny threshold
    (tmp_path / "big_file.bin").write_bytes(b"x" * 20000)
    mon.check(None, mock_registry)
    assert mon.status_level == "warning"
    assert len(mock_registry.sent_alerts) == 1

def test_http_endpoint_monitor(mock_registry):
    mon = HTTPEndpointMonitor(name="API Watch", url="http://localhost:8080/health", expected_status=200)
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_get.return_value = mock_resp
        
        mon.check(None, mock_registry)
        assert mon.status_level == "warning"
        assert len(mock_registry.sent_alerts) == 1
        assert "500" in mock_registry.sent_alerts[-1]["message"]

def test_local_port_monitor(mock_registry):
    mon = LocalPortMonitor(name="DB Port", port=65500, host="127.0.0.1")
    # Unopened port should trigger Down
    mon.check(None, mock_registry)
    assert mon.status_level == "warning"
    assert len(mock_registry.sent_alerts) == 1
    assert "closed" in mon.status_text

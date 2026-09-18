from typing import Dict, Any, Optional

from monitors.base import BaseMonitor
from monitors.process import ProcessStepDownMonitor, ProcessInstanceMonitor
from monitors.storage import StorageMultiTierMonitor, DirectorySizeMonitor
from monitors.io_heartbeat import IOMonitor
from monitors.resource import ResourceMonitor
from monitors.network import HTTPEndpointMonitor, LocalPortMonitor

MONITOR_CLASSES = {
    ProcessStepDownMonitor.monitor_type: ProcessStepDownMonitor,
    ProcessInstanceMonitor.monitor_type: ProcessInstanceMonitor,
    IOMonitor.monitor_type: IOMonitor,
    StorageMultiTierMonitor.monitor_type: StorageMultiTierMonitor,
    ResourceMonitor.monitor_type: ResourceMonitor,
    DirectorySizeMonitor.monitor_type: DirectorySizeMonitor,
    HTTPEndpointMonitor.monitor_type: HTTPEndpointMonitor,
    LocalPortMonitor.monitor_type: LocalPortMonitor,
}

def create_monitor_from_dict(data: Dict[str, Any]) -> Optional[BaseMonitor]:
    m_type = data.get("type")
    cls = MONITOR_CLASSES.get(m_type)
    if cls:
        return cls.from_dict(data)
    print(f"[Monitors] Unknown monitor type '{m_type}', skipping.")
    return None

__all__ = [
    "BaseMonitor",
    "ProcessStepDownMonitor",
    "ProcessInstanceMonitor",
    "IOMonitor",
    "StorageMultiTierMonitor",
    "ResourceMonitor",
    "DirectorySizeMonitor",
    "HTTPEndpointMonitor",
    "LocalPortMonitor",
    "MONITOR_CLASSES",
    "create_monitor_from_dict"
]

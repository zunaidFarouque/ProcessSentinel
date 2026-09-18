# Complete Monitors Guide & Reference

ProcessSentinel 2.0 features **8 specialized monitor types**, covering process lifecycles, file I/O freshness, storage capacity, hardware resource saturation, and network service availability.

This reference explains the internal operational logic, exact configuration parameters, and state behaviors for each monitor.

---

## 📋 Common Settings (All Monitors)

Every monitor in ProcessSentinel shares these common base settings:

* **Monitor Name**: A human-friendly label (e.g., `"Nightly Blender Render Watchdog"`).
* **Interval (sec)**: How often (in seconds) the background engine evaluates this rule. Defaults to `60` seconds. For rapid crash detection, set to `10`–`30`s. For disk space or directory sizes, `300`–`600`s is recommended.
* **Channel**: Select `[Inherit Default Channel]` or pick a specific channel alias to override routing for this rule.
* **Enabled Toggle**: Allows toggling rules active or inactive without losing their configuration.
* **↺ Reset State**: Clears internal state memory (high-watermark, triggered flags, last file timestamps) to re-arm the monitor.

---

## 1. Process Step-Down (Window High-Watermark)

### Overview
Ideal for batch simulation tools, CAD software, and rendering engines (e.g. ArcGIS Pro, Blender, 3ds Max, COMSOL, MATLAB) that open multiple visible windows or parallel instances and close them as tasks finish.

### How It Works
1. When armed, it discovers running windows or processes and establishes a **High-Watermark** (peak count).
2. As worker windows finish and close, the count steps downward (e.g., from 4 → 3 → 2 → 1).
3. **Single Alert per Step**: Sends one notification whenever the count decreases. It will not spam if the count stays at 3 for several hours.
4. **All Closed Trigger**: When the count reaches `0`, it dispatches a high-priority Critical alert letting you know the entire batch has completed or crashed.

### Parameters
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **Target String** | Text | *(Required)* | Window title substring or process executable name (e.g., `ArcGISPro.exe` or `Blender`). |
| **Initial Count** | Integer | `3` | Expected starting count / initial watermark baseline. |
| **Match Mode** | Dropdown | `window_title` | `window_title` (inspects visible desktop window titles via Win32 API) or `process_name` (inspects running task executable names). |
| **Step-Down Message** | Template | `Tracked window count dropped to {count}.` | Notification text sent on downward step. `{count}` is replaced dynamically. |
| **Critical Message** | Template | `CRITICAL: All '{target}' windows have closed!` | Notification text sent when count hits 0. |

> [!TIP]
> Use **↺ Reset State** whenever you start a new batch so the monitor can detect the new high-watermark peak.

---

## 2. Process Instance Count (Headless / Daemon)

### Overview
Monitors background daemons, worker processes, API services, or automation agents that have no visible windows.

### How It Works
Checks the operating system process table for exact matching executable names and compares the running count against your chosen threshold using relational operators (`below`, `above`, `equals`).

### Parameters
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **Target Process Name** | Text | *(Required)* | Executable file name (e.g., `python.exe`, `celery.exe`, `mysqld.exe`). |
| **Condition** | Dropdown | `below` | Operator to test: `below` (<), `above` (>), or `equals` (==). |
| **Threshold** | Integer | `1` | Instance count threshold. E.g., Condition `below` with threshold `1` triggers when the service stops running. |

---

## 3. I/O Heartbeat (Multi-Path & File Filter)

### Overview
Solves the "frozen/zombie process" problem: a long simulation software process might still be running in Task Manager, but internal memory corruption or a deadlock has caused it to stop generating output.

### How It Works
1. Recursively watches one or more output directories.
2. Filters for specific output file patterns (e.g., `*.csv`, `*.log`, `*.png`, `*.shp`).
3. Tracks the most recent file modification timestamp (`mtime`).
4. If no files are created or modified within the configured **Stall Alert After** window, it sends an alert warning you that output has stalled.

### Parameters
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **Folders to Watch** | Text | *(Required)* | Semicolon-separated folder paths (e.g. `D:\Sim\Output; E:\Scratch`). Use the **Add Folder** button to browse. |
| **File Filters** | Text | `*.shp, *.gdb, *.csv` | Comma-separated glob patterns to match against. |
| **Stall Alert After** | Float | `15.0` | Inactivity threshold in minutes before declaring an I/O stall. |

---

## 4. Storage Free Space (Multi-Tier)

### Overview
Monitors available free disk space on any local drive partition or mapped network drive with three cascading alert thresholds.

### How It Works
Evaluates free storage space in Gigabytes (GB). Alerts are escalated across three severity tiers:
* **Warning Tier**: Early reminder that disk is getting low.
* **Critical Tier**: Urgent reminder to clear temporary files.
* **Fatal Tier**: Highest priority alert when disk is almost completely exhausted.

To prevent alert flooding, once a tier triggers, it will not repeat until storage fluctuates or state is reset.

### Parameters
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **Target Drive Letter** | Text | `C:\` | Target drive root (e.g., `C:\`, `D:\`, `Z:\`). |
| **Warning Tier (GB)** | Float | `30.0` | Triggers when free space falls below this number of GB. |
| **Critical Tier (GB)** | Float | `20.0` | Triggers when free space falls below this number of GB. |
| **Fatal Tier (GB)** | Float | `10.0` | Triggers when free space falls below this number of GB. |

---

## 5. Process Resource Usage (CPU % / RAM MB)

### Overview
Monitors hardware resource consumption of specific running processes to catch memory leaks or thread runaway.

### How It Works
Samples the process's CPU utilization percentage or working set memory footprint in megabytes (MB).
* **CPU Ceiling**: Detects infinite loops or spinning worker threads (e.g., CPU > 95%).
* **CPU Floor**: Detects idle/hung tasks that should be computing (e.g., CPU < 2%).
* **RAM Ceiling**: Detects memory leaks before Windows runs out of commit memory (e.g., RAM > 16384 MB).

### Parameters
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **Target Process Name** | Text | *(Required)* | Executable name (e.g., `ArcGISPro.exe`, `node.exe`). |
| **Metric** | Dropdown | `cpu_percent` | `cpu_percent` (% of CPU capacity) or `memory_mb` (RAM footprint in MB). |
| **Condition** | Dropdown | `below` | `below` or `above`. |
| **Threshold** | Float | `5.0` | Threshold value (% for CPU, MB for RAM). |

---

## 6. Directory Size Watcher

### Overview
Monitors the cumulative byte size of a target folder hierarchy to prevent disk runaway in cache, log, or scratch directories.

### How It Works
Calculates the total size of all files within a directory tree. If the directory exceeds **Max Size Allowed (GB)**, an alert is dispatched.

### Parameters
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **Directory Path** | Text | *(Required)* | Target folder path. Use the **Browse** button to locate. |
| **Max Size Allowed (GB)**| Float | `50.0` | Maximum acceptable storage threshold for this folder. |

---

## 7. HTTP / Web Endpoint Check

### Overview
Performs periodic health checks against local or remote web services, REST APIs, or application servers.

### How It Works
Sends an HTTP `GET` request to the target URL with an automated timeout (10s). If the server fails to respond, throws a connection error, or returns a status code different from **Expected Status Code**, an alert is dispatched.

### Parameters
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **Target URL** | Text | *(Required)* | Web URL (e.g., `http://localhost:8080/health`, `http://127.0.0.1:5000/api/status`). |
| **Expected Status Code** | Integer | `200` | HTTP response status code denoting healthy status. |

---

## 8. Local Network Port Check

### Overview
Verifies that essential database engines, cache daemons, license servers, or custom network listeners are bound and accepting TCP socket connections.

### How It Works
Attempts a TCP socket handshake to the specified `host:port` with a 5-second connection timeout. If the socket connection is refused, times out, or host is unreachable, an alert is triggered.

### Parameters
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **Port Number** | Integer | `5432` | TCP port number (e.g., PostgreSQL `5432`, Redis `6379`, MySQL `3306`, Custom `9000`). |
| **Host Address** | Text | `127.0.0.1` | Hostname or IP address (e.g., `127.0.0.1` for local machine, or LAN IP). |

---

## ⏭️ Next Step

Learn how to manage and route notifications in **[Notification Channels & Alert Routing](channels-and-routing.md)**.

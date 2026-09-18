# ProcessSentinel 2.0

**ProcessSentinel** is a modular, rule-based Windows watchdog engine and modern desktop dashboard designed to monitor long-running computational batches, background services, and system health.

Built with **CustomTkinter** and powered by an asynchronous monitoring daemon, it dispatches instant push notifications to your mobile phone or desktop via **ntfy.sh** whenever critical conditions occur.

---

## 📚 Documentation & User Guides

Comprehensive documentation is available in the [`docs/`](docs/index.md) directory:

* 📖 **[Documentation Home & Index](docs/index.md)** — Architecture overview and navigation hub.
* 🚀 **[Getting Started & Portable Setup](docs/getting-started.md)** — Portable executable layout, self-healing config, and UI walkthrough.
* 📱 **[Mobile Push Notifications Setup](docs/mobile-setup.md)** — Android & iOS app links, ntfy.sh setup, and alert testing.
* 🎛️ **[Complete Monitors Guide & Reference](docs/monitors-guide.md)** — Detailed parameters, operational logic, and settings for all 8 monitors.
* 📡 **[Channels & Alert Routing](docs/channels-and-routing.md)** — Managing topic aliases, defaults, priority mappings, and overrides.
* 💡 **[Real-World Use Cases & Cookbooks](docs/use-cases.md)** — Recipes for 3D renders, deep learning, GIS pipelines, and databases.
* ⚙️ **[Configuration & Backup Guide](docs/configuration.md)** — JSON schema, automatic quarantine, and import/export.

---

## Key Features

### 1. Flexible Multi-Channel Routing
* **Topic Aliases**: Configure multiple named notification endpoints (e.g., *"My Phone"*, *"Lab IT Alerts"*).
* **Rule-Level Routing**: Inherit a global default channel or route specific monitors (or alert tiers) to distinct channels.

### 2. Rich Monitor Types
* **Process Step-Down (High-Watermark)**: Stateful instance and visible window tracking. Alerts once for each downward step (e.g. 3 -> 2 -> 1) without duplicate alert spam, plus critical alerts when all instances terminate.
* **Process Instance Count**: Monitored thresholds for headless daemons or workers (alerts when instances go below, above, or equal a target).
* **I/O Heartbeat**: Multi-path directory stall detection with file extension glob filtering (`*.shp`, `*.gdb`, `*.csv`). Alerts when no matching files are modified within a specified timeout.
* **Storage Free Space (Multi-Tier)**: Cascading storage warnings on any drive (e.g., 30 GB Warning, 20 GB Critical, 10 GB Fatal) with per-tier messages and optional channel overrides.
* **Process Resource Usage**: Monitors CPU % and RAM (MB) to detect "zombie" hung processes (CPU floor) or memory leaks (RAM ceiling).
* **Directory Size Watcher**: Prevents folder cache bloat (e.g., scratch folders or temporary data exceeding a size limit).
* **HTTP Endpoint Check**: Pings local or remote web APIs to verify health status.
* **Local Network Port Check**: Verifies that database or service ports (Postgres, Redis, custom sockets) remain open.

### 3. Interactive Management & State Control
* **Manual State Reset**: Flush a monitor's alert memory (`[↺ Reset State]`) directly from the UI to re-arm notifications after resolving an issue.
* **Live Activity Stream**: Real-time event log tab showing checks, triggers, and notification deliveries.
* **Object-Oriented Configuration**: Full JSON serialization of all channels and monitors via `config.json`.

---

## Installation & Setup

### Option 1: Install via Scoop (Recommended)

If you use the [Scoop](https://scoop.sh) Windows package manager:

```powershell
# Add the bucket
scoop bucket add zunaid https://github.com/zunaidFarouque/Zunaid-Scoop-Bucket

# Install ProcessSentinel
scoop install processsentinel
```

Or install directly from the manifest URL without subscribing to a bucket:
```powershell
scoop install https://raw.githubusercontent.com/zunaidFarouque/ProcessSentinel/main/processsentinel.json
```

---

### Option 2: Standalone Portable Binary (Zero Install)

1. Download **`ProcessSentinel-v2.0.0-windows-x64.zip`** from the [Latest Release](https://github.com/zunaidFarouque/ProcessSentinel/releases/latest).
2. Extract the folder anywhere (e.g. `C:\Tools\ProcessSentinel` or a USB drive).
3. Double-click **`ProcessSentinel.exe`** to start.

---

### Option 3: Run from Python Source (Developers)

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/zunaidFarouque/ProcessSentinel.git
   cd ProcessSentinel
   ```

2. **Set Up Python Virtual Environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. **Launch the Dashboard**:
   ```powershell
   python main.py
   ```

---

## Project Structure

```text
ProcessSentinel/
├── .venv/                      # Python virtual environment
├── .vscode/
│   └── settings.json           # VS Code Python environment configuration
├── src/
│   ├── channels.py             # NotificationChannel & ChannelRegistry (ntfy.sh)
│   ├── config_manager.py       # Object-oriented config persistence (config.json)
│   ├── engine.py               # MonitorEngine background execution thread
│   ├── main.py                 # Application bootstrapper
│   ├── gui/                    # CustomTkinter Dark Mode GUI
│   │   ├── app.py              # Main dashboard window & tabs
│   │   └── dialogs.py          # Channel & Monitor modal wizard dialogs
│   └── monitors/               # Modular monitor implementations
│       ├── base.py             # BaseMonitor abstract class
│       ├── process.py          # ProcessStepDownMonitor & ProcessInstanceMonitor
│       ├── storage.py          # StorageMultiTierMonitor & DirectorySizeMonitor
│       ├── io_heartbeat.py     # IOMonitor (multi-path & glob filter)
│       ├── resource.py         # ResourceMonitor (CPU % / RAM MB)
│       └── network.py          # HTTPEndpointMonitor & LocalPortMonitor
├── tests/
│   └── test_v2.py              # Automated test suite
├── requirements.txt            # Project dependencies
└── main.py                     # Root entrypoint redirector
```
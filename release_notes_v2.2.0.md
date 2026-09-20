### What's Changed in v2.2.0 (Major Overhaul 1)

ProcessSentinel v2.2.0 is a major evolutionary release transforming ProcessSentinel from a local polling dashboard into an autonomous, self-healing, multi-channel watchdog engine.

#### 🚀 Core Ergonomics & System Integration
* **Windows System Tray Support**: ProcessSentinel now runs seamlessly in the background with tray icon minimization and close-to-tray protection. The tray context menu provides instant actions (*Show Dashboard*, *Start/Stop Engine*, *Check All*, and *Quit*).
* **Auto-Start Engine on Boot/Launch**: Engine state can now be set to auto-start immediately on application startup via the new **⚙ Settings** modal dialog.
* **Storage Step-Down Latching & Debounce Hysteresis**: Disk space alerts now latch monotonically as storage descends (e.g. 30 GB → 20 GB → 10 GB), completely eliminating flapping alert storms. Monitors re-arm on manual reset or when free space climbs safely past `threshold + margin`.
* **Auto-Recovery ("Resolved") Notifications**: Supported monitors can automatically emit clear recovery alerts when an incident resolves.
* **Persistent Disk Logging**: Automatic rotating log handler writing to `logs/sentinel.log` (5 MB max, 3 backups) alongside the live in-memory GUI buffer.
* **Dashboard Ergonomics**: Real-time search/filter bar across monitor cards and one-click `[📋 Clone]` button to duplicate monitor configurations.

#### 🛡️ New Watchdogs & Self-Healing Actions
* **GPU VRAM & Temperature Watcher (`GPUMonitor`)**: Zero-dependency GPU monitoring via native `nvidia-smi` CLI tracking temperature (°C), GPU utilization %, and VRAM allocation.
* **Active Log File Scanner (`LogScannerMonitor`)**: Efficient byte-offset tailing of active log files with keyword and regex pattern matching (`CUDA out of memory`, `Traceback`, `FATAL`) and log rotation detection.
* **Power & Battery Monitor (`PowerMonitor`)**: Tracks AC mains connectivity and battery discharge levels via `psutil.sensors_battery` for UPS and laptop monitoring.
* **Self-Healing Trigger Actions**: Any monitor can now be configured with an `action_command` to execute local remediation scripts (`.bat`, `.ps1`, `.py`, `.exe`) asynchronously upon alert.

#### 🌐 Multi-Channel Notification Routing & Remote Remediation
* **Multi-Provider Notification Channels**: Built-in native dispatch for:
  * **ntfy.sh**: Push notifications with priority levels, emojis, tags, and actions.
  * **Telegram Bot**: Markdown alert dispatch directly to channels or direct messages.
  * **Discord Webhook**: Rich alert notifications posted to Discord server channels.
  * **Slack Webhook**: Team incident dispatch via incoming webhooks.
* **⚡ Test Alert Button**: In-dialog test dispatch to verify provider credentials and webhook URLs before saving.
* **Remote Action Command Listener**: Token-authenticated background daemon capable of receiving remote remediation triggers.

#### 🧪 Test Suite & Quality
* Unit test coverage expanded from 26 to **93 tests** with 100% passing rate under Test-Driven Development (TDD).
* Full backward compatibility preserved for older configuration schemas.

# Getting Started with ProcessSentinel 2.0

This guide walks you through setting up and running ProcessSentinel on Windows, understanding its portable architecture, and navigating the interface.

---

## 💻 System Requirements

* **Operating System**: Windows 10 or Windows 11 (64-bit).
* **Permissions**: Standard user permissions (Administrator rights are **not** required unless monitoring system-level services owned by `NT AUTHORITY\SYSTEM`).
* **Network**: Outbound HTTPS access to `ntfy.sh` (port 443) or your internal corporate/lab ntfy server.
* **Disk Space**: ~45 MB for the portable package.

---

## 📦 Portable Architecture & Folder Structure

ProcessSentinel was designed from the ground up to be **100% portable**. You can copy the folder to any directory, run it from a USB flash drive, or place it on a network share without running any installers or modifying Windows registry keys.

The distribution layout is structured cleanly:

```text
ProcessSentinel/
├── ProcessSentinel.exe         <-- Primary executable (double-click to run)
├── config.json                 <-- Auto-created active state and settings file
└── ProcessSentinel_files/      <-- Bundled Python runtime, DLLs, and GUI libraries
```

### Self-Healing Configuration
* ProcessSentinel automatically looks for `config.json` located directly adjacent to `ProcessSentinel.exe`.
* If `config.json` does not exist (such as on first launch), ProcessSentinel generates a clean, default template with a sample channel and standard monitors.
* If `config.json` is ever damaged or edited with invalid syntax, ProcessSentinel automatically renames the corrupt file to `config.json.corrupt_<timestamp>` and re-initializes a fresh configuration so the application never crashes on startup.

---

## 🖥️ Running from Source (Developers)

If you prefer to run ProcessSentinel directly from source code or modify its internals:

```powershell
# 1. Clone the repository
git clone https://github.com/zunaidFarouque/ProcessSentinel.git
cd ProcessSentinel

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install required dependencies
pip install -r requirements.txt

# 4. Launch the application
python main.py
```

To build your own portable executable package, simply run:
```powershell
.\build-portable.bat
```
The compiled, standalone portable distribution will be output to `dist/ProcessSentinel/`.

---

## 🎛️ Dashboard Tour & Navigation

The user interface is divided into an intuitive header bar and three functional tabs:

![ProcessSentinel Dashboard](images/dashboard_preview.png)
*(Note: Interface renders in native Windows Dark Mode)*

### Top Control Bar
* **Status Indicator**: Displays `● IDLE` (engine paused) or `● RUNNING` (actively polling).
* **▶ START ENGINE / ⏹ STOP ENGINE**: Starts or stops the background monitoring thread.
* **📥 Import**: Load an external JSON configuration file.
* **📤 Export**: Export your current monitors and channels to a shareable backup JSON file.
* **💾 Save**: Explicitly persist your current configuration to `config.json`.
* **❓ Help**: Opens this documentation directly in your default web browser.

---

### Tab 1: Active Monitors
This is your main operational command center:
* **Monitor Cards**: Each active rule is rendered as an interactive card displaying its monitor type badge, friendly name, polling interval, and assigned notification channel.
* **Live Status Badge**:
  * 🟢 **● OK**: Condition satisfied / within safe boundaries.
  * 🟠 **● WARNING**: Condition approaching alert threshold.
  * 🔴 **● CRITICAL**: Condition triggered / alert active.
* **Enabled Toggle**: Quickly turn individual monitors on or off without deleting them.
* **⚡ Check All Now**: Force an immediate evaluation across all enabled monitors without waiting for their timer intervals.
* **↺ Reset State**: Manually clear a monitor's historical state (e.g. high-watermark peak or alerted flags). Use this when launching a new batch run.
* **✏ Edit / 🗑 Delete**: Modify parameters or remove rules.

---

### Tab 2: Notification Channels
Manage where alerts are sent:
* **Channel List**: View all configured push endpoints.
* **Default Channel**: One channel is designated as the fallback channel (`[Default]`). Any monitor without an explicit override routes here.
* **Test Alert**: Sends an instant test push notification to verify connectivity. The button updates to `"Sending..."` asynchronously so the UI never freezes.
* **Set as Default**: Switch the primary broadcast destination with a single click.

---

### Tab 3: Live Activity Log
* Displays a real-time, color-coded audit trail of engine actions, cycle ticks, metric measurements, threshold evaluations, and push notification dispatches.
* Click **Clear Log** to reset the window view at any time.

---

## ⏭️ Next Step

Now that you are familiar with the interface, continue to **[Mobile Push Notifications Setup](mobile-setup.md)** to connect your phone!

# Configuration & Backup Guide

ProcessSentinel stores all runtime settings, channel credentials, and monitoring rules in a clean, human-readable JSON format.

---

## 🗂️ Configuration Storage & Portability

### Location of `config.json`
ProcessSentinel looks for its configuration file in the following priority order:
1. **Portable Bundle Directory**: When running as `ProcessSentinel.exe`, it reads/writes `config.json` located directly in the same folder as the `.exe`.
2. **Current Working Directory / Script Root**: When running directly from Python source (`python main.py`), it reads/writes `config.json` at the root of the repository.

This structure allows you to place ProcessSentinel on an external drive or a network volume and move it between workstations without losing your custom rules.

---

## 🛡️ Self-Healing Configuration Engine

Workstation crashes, unexpected power loss, or manual editing errors can sometimes corrupt local configuration files. ProcessSentinel includes a built-in **self-healing engine**:

1. **Automatic Initialization**: If `config.json` is missing (such as on a fresh installation), ProcessSentinel automatically creates a standard default configuration with sample monitors.
2. **Crash Resilience & Quarantine**: If `config.json` contains invalid JSON or syntax errors:
   * ProcessSentinel captures the error.
   * It safely renames the damaged file to `config.json.corrupt_YYYYMMDD_HHMMSS` to preserve any data you might want to recover.
   * It generates a pristine, fresh `config.json` and logs a prominent warning in the Live Activity Log.
   * The application **never crashes on launch due to a malformed config**.

---

## 💾 Importing and Exporting Configurations

ProcessSentinel makes it easy to back up your setup or deploy identical monitoring presets across multiple lab machines:

### Exporting a Configuration
1. Click the **📤 Export** button in the top header bar.
2. Choose a destination folder and file name (e.g. `blender_cluster_preset.json`).
3. ProcessSentinel serializes all active channels and monitor rules into the file.

### Importing a Configuration
1. Click the **📥 Import** button in the top header bar.
2. Select your exported JSON file.
3. ProcessSentinel immediately validates the file structure:
   * Reconstructs all notification channels and monitor objects.
   * Updates the UI cards and lists instantly.
   * Seamlessly persists the imported rules as your new active `config.json`.

---

## 📝 Sample `config.json` Structure

For advanced users or automated configuration scripts, here is the standard schema:

```json
{
  "channels": [
    {
      "id": "c-1742445890-default",
      "name": "My Phone",
      "url": "https://ntfy.sh/my_private_lab_topic"
    }
  ],
  "default_channel_id": "c-1742445890-default",
  "settings": {
    "auto_start_engine": false,
    "minimize_to_tray": true,
    "start_minimized": false
  },
  "monitors": [
    {
      "id": "m-1742445890-stepdown",
      "name": "Blender Batch Render",
      "type": "ProcessStepDown",
      "enabled": true,
      "interval_seconds": 30,
      "channel_id": null,
      "target": "blender.exe",
      "initial_count": 4,
      "match_mode": "process_name",
      "step_down_message": "Tracked window count dropped to {count}.",
      "critical_message": "CRITICAL: All '{target}' windows have closed!"
    },
    {
      "id": "m-1742445890-storage",
      "name": "Drive C: Low Space Warning",
      "type": "StorageMultiTier",
      "enabled": true,
      "interval_seconds": 60,
      "channel_id": null,
      "drive": "C:\\",
      "step_down_mode": true,
      "recovery_margin_gb": 5.0,
      "tiers": [
        {"gb": 30.0, "message": "Storage Warning", "priority": 3},
        {"gb": 20.0, "message": "Critical Warning", "priority": 4},
        {"gb": 10.0, "message": "Fatal Warning", "priority": 5}
      ]
    }
  ]
}
```

---

## 📜 Persistent Disk Logging (`logs/sentinel.log`)

ProcessSentinel provides dual-layer logging:
* **Live In-Memory Buffer**: Displayed directly within the **Live Activity Log** tab in the GUI (last 200 events).
* **Rotating Disk Log File**: Stored in `logs/sentinel.log` adjacent to the executable or project root. ProcessSentinel uses an automated rotating handler (5 MB max per file, up to 3 backup archives) ensuring complete auditability without unbounded disk growth.

---

## 🏠 Return to Index

Return to the **[Documentation Index](index.md)**.

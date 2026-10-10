### What's Changed in v2.2.1

#### 🛠️ Monitor Dialog Ergonomics & Registration
* **Permanently Docked Action Buttons**: Re-architected `MonitorDialog` and `ChannelDialog` button bars so the **Save** and **Cancel** buttons are always pinned to the bottom of the dialog, visible across all display resolutions and high-DPI scaling factors (125%, 150%).
* **Keyboard Navigation**: Bound `<Return>` to save and `<Escape>` to close dialogs.
* **Step-Down Instance Count Updates**: Fixed issue where editing the target / expected instance count on a `ProcessStepDown` monitor did not properly persist or re-arm state tracking. Editing the instance count now automatically resets the state machine baseline.
* **Instant Engine Sync & Auto-Save**: Monitor and channel edits, additions, and deletions immediately update the engine in memory and persist to `config.json`.

#### 🚀 Single-Instance Restoration & System Tray
* **Single-Instance Mutex & Activator**: Added native Win32 single-instance handling (`src/single_instance.py`). Launching ProcessSentinel when an instance is already running (such as minimized to the system tray) automatically restores the existing window and brings it to the foreground.
* **Window Forefront & Centering**: Ensured the dashboard centers itself and forces foreground focus on startup and on restore from the system tray.

#### 🎯 Process & Window Title Matching
* **Fuzzy & Space-Tolerant Window Matching**: `window_title` match mode now tolerates `.exe` suffixes and spacing differences (e.g. configuring `ArcGISPro.exe` automatically matches windows titled `ArcGIS Pro`).
* **Match Mode Guidance**: Added UI helper captions to clarify `window_title` (for visible desktop app windows) vs `process_name` (for background / headless tasks in Task Manager).

#### 🧪 Verification
* Added comprehensive unit tests in `tests/test_gui_features.py`. All 97 tests pass cleanly.

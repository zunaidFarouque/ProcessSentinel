# AGENTS.md — Development & Operational Playbook for ProcessSentinel

Welcome, AI agent! This document contains essential instructions, conventions, and safety rules for developing, testing, building, and releasing **ProcessSentinel**.

---

## ⛔ CRITICAL SAFETY RULE: RELEASES

> [!CAUTION]
> **NEVER EXECUTE `release.bat` OR `scripts/release.ps1` WITHOUT THE USER'S EXPLICIT, DIRECT PERMISSION IN THE CURRENT PROMPT.**
> * You are fully authorized to write code, edit files, run `pytest`, and run `build-portable.bat`.
> * You MUST **NEVER** autonomously trigger an official GitHub release or push release tags unless the user has explicitly commanded: *"Please release version X.Y.Z"* or gave direct permission to execute the release.
> * If in doubt, STOP and ask the user for confirmation.

---

## 🏗️ Project Architecture & Tech Stack

* **GUI Framework**: Modern Dark Mode desktop dashboard built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter).
* **Execution Engine**: Asynchronous, multi-threaded `MonitorEngine` (`src/engine.py`) with stateful condition evaluation.
* **Notification Routing**: Multi-channel pub-sub dispatch via `ntfy.sh` (`src/channels.py`) with priority mapping (`3` Info, `4` Warning, `5` Urgent).
* **Persistence & Portability**: Self-healing `config.json` adjacent to `ProcessSentinel.exe` (`src/config_manager.py`). If corrupted, automatically quarantined and reset.
* **Packaging**: Compiled using PyInstaller into a portable single folder with `--contents-directory "ProcessSentinel_files"` (`build-portable.bat`).
* **Scoop Integration**: Canonical manifest `processsentinel.json` at root; synced to `zunaidFarouque/Zunaid-Scoop-Bucket`.

---

## 🧪 Testing & Verification

Always run unit tests before making commits:

```powershell
# Run the complete test suite
.\.venv\Scripts\pytest.exe -v
```

All 18+ tests in `tests/` must pass cleanly before any code change is considered complete.

---

## 📦 Building the Portable Executable

To compile the application into a standalone portable binary:

```powershell
.\build-portable.bat
```

* **Output**: `dist\ProcessSentinel\`
  * `ProcessSentinel.exe`
  * `ProcessSentinel_files\` (internal libraries and Python runtime)

---

## 🚀 Official Release Pipeline (USER-AUTHORIZED ONLY)

**Only execute this when the user explicitly requests a release:**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\release.ps1 `
  -Version "X.Y.Z" `
  -Title "ProcessSentinel vX.Y.Z - <Short Summary>" `
  -Notes "### What's Changed in vX.Y.Z`n* Feature 1`n* Feature 2" `
  -Force
```

### What `scripts/release.ps1` Does:
1. **Pre-flight verification**: Ensures `dist\ProcessSentinel\ProcessSentinel.exe` exists, `gh` is authenticated, and git tag does not conflict.
2. **Compresses** `dist\ProcessSentinel` into `ProcessSentinel-vX.Y.Z-windows-x64.zip`.
3. **Calculates SHA-256** checksum.
4. **Updates `processsentinel.json`** with the new version, download URL, and hash, strictly enforcing **CRLF line endings** and **UTF-8 without BOM**.
5. **Commits and pushes** the manifest update to GitHub `main`.
6. **Publishes the GitHub Release** with the zip asset attached via `gh release create`.
7. **Dispatches workflow sync** to `zunaidFarouque/Zunaid-Scoop-Bucket` via `gh workflow run sync-processsentinel.yml`.
8. **Cleans up** local zip artifacts.

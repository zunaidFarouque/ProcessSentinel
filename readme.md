# ProcessSentinel

**ProcessSentinel** is a lightweight, asynchronous Python monitoring tool designed to track long-running, headless background tasks. It ensures heavy computational batches do not silently fail, hang, or exhaust system resources.

## Features
* **Process Tracking:** Binds to specific executables and sends instant push notifications if a critical application unexpectedly terminates.
* **I/O Heartbeat:** Monitors a designated scratch/temp directory to verify the background engine is actively reading and writing files.
* **Storage Failsafe:** Continuously checks the primary drive's capacity, issuing warnings before storage exhaustion crashes the active batch.
* **Asynchronous GUI:** A lightweight `tkinter` dashboard allows for real-time configuration without interrupting the active monitoring daemon.

## Installation
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt` (requires `psutil` and `requests`).
3. Run `python main.py` to launch the dashboard and configure your target paths.
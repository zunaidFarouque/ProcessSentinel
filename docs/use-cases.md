# Real-World Use Cases & Cookbooks

This cookbook provides plug-and-play recipes for setting up ProcessSentinel across real-world workflows, including 3D rendering, machine learning model training, geospatial batch automation, and research server health.

---

## 🎨 Recipe 1: Overnight 3D Render Watchdog (Blender / Maya / Cinema 4D)

### The Problem
You queue an overnight animation render using 4 parallel instances of Blender or Maya. If one instance crashes due to a GPU VRAM exhaustion or a driver timeout, you might only discover it the next morning. Furthermore, rendering gigabytes of uncompressed EXR frames can quickly deplete your drive.

### Recommended Configuration
1. **Process Step-Down Monitor**:
   * **Name**: `Blender Parallel Workers`
   * **Type**: `Process Step-Down (Window High-Watermark)`
   * **Target String**: `blender.exe`
   * **Match Mode**: `process_name`
   * **Initial Count**: `4`
   * **Interval**: `30` seconds
   * *Benefit*: Notifies your phone as each render finishes (`"Tracked count dropped to 3... 2... 1..."`), and sends an urgent wake-up alert when all 4 instances exit.
2. **I/O Heartbeat Monitor**:
   * **Name**: `Frame Output Watcher`
   * **Type**: `I/O Heartbeat`
   * **Folders to Watch**: `D:\Renders\ProjectX\Frames`
   * **File Extension Filters**: `*.exr, *.png`
   * **Stall Alert After**: `15.0` minutes
   * *Benefit*: If a tile render crashes or deadlocks with the process still open at 0% GPU, this detects that no new frames have been saved and alerts you immediately.
3. **Storage Free Space Monitor**:
   * **Name**: `Render Drive Space Guard`
   * **Type**: `Storage Free Space (Multi-Tier)`
   * **Target Drive**: `D:\`
   * **Warning / Critical / Fatal**: `50.0` / `20.0` / `5.0` GB

---

## 🧠 Recipe 2: Machine Learning Model Training (PyTorch / TensorFlow)

### The Problem
Long deep learning training runs (e.g., 20+ hours) can suffer from gradual CPU RAM leaks in Python data loader worker processes (`torch.utils.data.DataLoader`), or silent training loop hangs during epoch evaluation.

### Recommended Configuration
1. **Process Resource Usage Monitor**:
   * **Name**: `PyTorch Training RAM Guard`
   * **Type**: `Process Resource Usage`
   * **Target Process**: `python.exe`
   * **Metric**: `memory_mb`
   * **Condition**: `above`
   * **Threshold**: `28000` MB (e.g. on a 32 GB system)
   * *Benefit*: Alerts you if memory consumption runs away before Windows begins page swapping or kills the job with Out-Of-Memory.
2. **I/O Heartbeat Monitor**:
   * **Name**: `Model Checkpoint Heartbeat`
   * **Type**: `I/O Heartbeat`
   * **Folders to Watch**: `C:\Experiments\checkpoints`
   * **File Extension Filters**: `*.pt, *.ckpt, *.safetensors`
   * **Stall Alert After**: `45.0` minutes
   * *Benefit*: Ensures model weights and optimizer checkpoints are regularly committed to disk.
3. **HTTP Endpoint Check**:
   * **Name**: `TensorBoard Health Check`
   * **Type**: `HTTP / Web Endpoint Check`
   * **Target URL**: `http://localhost:6006`
   * **Expected Status**: `200`
   * *Benefit*: Confirms your experiment tracking dashboard remains accessible.

---

## 🗺️ Recipe 3: Batch GIS & Geodatabase Processing (ArcGIS Pro / QGIS / FME)

### The Problem
A multi-threaded spatial analyst script opens several ArcGIS Pro geoprocessing windows to convert massive shapefiles and raster elevation models into File Geodatabases. Intermediate scratch files can quickly bloat Windows Temp folders and crash the run.

### Recommended Configuration
1. **Process Step-Down Monitor**:
   * **Name**: `ArcGIS Pro Batch Jobs`
   * **Type**: `Process Step-Down (Window High-Watermark)`
   * **Target String**: `ArcGIS Pro`
   * **Match Mode**: `window_title`
   * **Initial Count**: `3`
   * *Benefit*: Tracks visible desktop task windows as each geoprocessing operation concludes.
2. **Directory Size Watcher**:
   * **Name**: `ArcGIS Temp Scratch Watcher`
   * **Type**: `Directory Size Watcher`
   * **Directory Path**: `C:\Users\User\AppData\Local\Temp\ArcGISPro_Scratch`
   * **Max Size Allowed**: `35.0` GB
   * *Benefit*: Warns you if intermediate scratch rasters accumulate beyond threshold before they fill your primary OS drive.

---

## 🗄️ Recipe 4: Local Research Microservices & Database Rig

### The Problem
Your workstation runs local database daemons (PostgreSQL, MongoDB, or Redis) and background ETL ingestion scripts. If the database crashes or port binding fails, downstream analyses fail silently.

### Recommended Configuration
1. **Local Network Port Check**:
   * **Name**: `PostgreSQL Listener Check`
   * **Type**: `Local Network Port Check`
   * **Host Address**: `127.0.0.1`
   * **Port Number**: `5432`
   * *Benefit*: Directly attempts a TCP socket handshake every 60 seconds; triggers an urgent alert if PostgreSQL stops accepting connections.
2. **Process Instance Count Monitor**:
   * **Name**: `ETL Worker Daemon`
   * **Type**: `Process Instance Count (Headless / Daemon)`
   * **Target Process Name**: `ingest_daemon.exe`
   * **Condition**: `below`
   * **Threshold**: `1`
   * *Benefit*: Alerts immediately if the background Python or C++ daemon unexpectedly terminates.

---

## 💡 Pro-Tips for Maximum Reliability

* **Tag Your Jobs**: Name your monitors clearly with project or ticket numbers (e.g. `[PROJ-412] Batch Mesh Solver`).
* **Use State Reset for New Batches**: When starting a second round of tasks, remember to click the `↺ Reset State` button on the monitor card so that previous high-watermarks and alerts are cleanly flushed.
* **Export Your Templates**: After tuning monitors for a specific workflow, click **📤 Export** in the top bar to save a `.json` preset. You can reload it anytime via **📥 Import**!

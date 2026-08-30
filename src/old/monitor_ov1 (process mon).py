import os
import time
import psutil
import shutil
import threading

class MonitoringDaemon:
    def __init__(self, notifier):
        self.notifier = notifier
        self.running = False
        
        # Default Configurations (will be overwritten by the GUI)
        self.target_processes = []
        self.watch_folder = ""
        self.stalled_mins = 15
        self.min_storage_gb = 10
        
        # State / Throttling tracking (prevents spamming notifications)
        self.storage_warned = False
        self.stalled_warned = False
        self.known_dead_processes = set()

    def update_config(self, processes, folder, stall_mins, storage_gb):
        """Receives dynamic updates from the GUI."""
        self.target_processes = [p.strip().lower() for p in processes if p.strip()]
        self.watch_folder = folder
        self.stalled_mins = float(stall_mins)
        self.min_storage_gb = float(storage_gb)
        
        # Reset throttling when configuration is manually updated
        self.storage_warned = False
        self.stalled_warned = False
        self.known_dead_processes.clear()

    def start(self):
        """Boots the daemon thread."""
        if not self.running:
            self.running = True
            # daemon=True ensures this thread dies instantly when the main GUI closes
            threading.Thread(target=self._monitor_loop, daemon=True).start()

    def stop(self):
        """Safely breaks the while loop."""
        self.running = False

    def _monitor_loop(self):
        """The core loop. Sleeps for 60 seconds between checks."""
        while self.running:
            if self.target_processes:
                self._check_processes()
            
            if self.watch_folder and os.path.exists(self.watch_folder):
                self._check_io_heartbeat()
                
            self._check_storage()
            
            time.sleep(60)

    def _check_processes(self):
        """Validates that all target executables are currently running."""
        # Pull a fresh list of all active process names
        running_proc_names = [p.name().lower() for p in psutil.process_iter(['name'])]
        
        for target in self.target_processes:
            if target not in running_proc_names:
                if target not in self.known_dead_processes:
                    self.notifier.send(
                        f"Target process '{target}' has unexpectedly terminated.", 
                        "Process Stopped/Crashed", 
                        "skull"
                    )
                    self.known_dead_processes.add(target)
            else:
                # If the user restarts the process, reset the warning flag
                if target in self.known_dead_processes:
                    self.known_dead_processes.remove(target)

    def _check_io_heartbeat(self):
        """Scans the designated scratch folder for recent read/write activity."""
        newest_time = 0
        
        try:
            for root, _, files in os.walk(self.watch_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        mtime = os.path.getmtime(file_path)
                        if mtime > newest_time:
                            newest_time = mtime
                    except OSError:
                        # Files created and deleted instantly (rapid temp files) might throw an error.
                        pass 
        except Exception:
            return

        if newest_time == 0:
            return # Folder is empty, nothing to scan yet

        mins_since_last_edit = (time.time() - newest_time) / 60

        if mins_since_last_edit > self.stalled_mins:
            if not self.stalled_warned:
                self.notifier.send(
                    f"No files written in {mins_since_last_edit:.1f} mins. Process stalled.",
                    "I/O Heartbeat Stalled",
                    "warning"
                )
                self.stalled_warned = True
        else:
            self.stalled_warned = False # Reset flag if I/O resumes

    def _check_storage(self):
        """Checks the C: drive for critical storage exhaustion."""
        try:
            _, _, free = shutil.disk_usage("C:\\")
            free_gb = free / (2**30) # Convert bytes to Gigabytes
            
            if free_gb < self.min_storage_gb:
                if not self.storage_warned:
                    self.notifier.send(
                        f"Critical Storage: Only {free_gb:.1f} GB remaining on C: drive.",
                        "Storage Failsafe",
                        "floppy_disk,rotating_light"
                    )
                    self.storage_warned = True
            else:
                self.storage_warned = False
        except Exception:
            pass
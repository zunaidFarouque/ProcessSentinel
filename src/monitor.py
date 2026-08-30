import os
import time
import shutil
import threading
import win32gui

class MonitoringDaemon:
    def __init__(self, notifier):
        self.notifier = notifier
        self.running = False
        
        # Configurations
        self.target_window_titles = [] 
        self.watch_folder = ""
        self.stalled_mins = 15
        self.min_storage_gb = 10
        
        # State tracking
        self.storage_warned = False
        self.stalled_warned = False
        
        # HWND Lock Dictionary: { 123456: "Textron Systems", 654321: "Textron Systems" }
        self.locked_hwnds = {} 
        self.known_dead_hwnds = set()

    def update_config(self, processes, folder, stall_mins, storage_gb):
        """Receives dynamic updates from the GUI. 'processes' now acts as window titles."""
        self.target_window_titles = [p.strip().lower() for p in processes if p.strip()]
        self.watch_folder = folder
        self.stalled_mins = float(stall_mins)
        self.min_storage_gb = float(storage_gb)
        
        # Reset tracking states
        self.storage_warned = False
        self.stalled_warned = False
        self.locked_hwnds.clear()
        self.known_dead_hwnds.clear()

    def start(self):
        """Boots the daemon and locks onto target windows."""
        if not self.running:
            self._lock_target_windows()
            
            self.running = True
            threading.Thread(target=self._monitor_loop, daemon=True).start()

    def stop(self):
        """Safely breaks the while loop."""
        self.running = False

    def _lock_target_windows(self):
            """Scans the OS and stores the HWNDs of all VISIBLE windows matching the target titles."""
            self.locked_hwnds.clear()
            
            def callback(hwnd, extra):
                # NEW: Filter out hidden/invisible background worker windows
                if not win32gui.IsWindowVisible(hwnd):
                    return
                    
                # Only look at windows that actually have a title
                title = win32gui.GetWindowText(hwnd).strip().lower()
                if title:
                    for target in self.target_window_titles:
                        if target in title:
                            # Save the unique HWND and its exact original title
                            self.locked_hwnds[hwnd] = win32gui.GetWindowText(hwnd)
            
            if self.target_window_titles:
                win32gui.EnumWindows(callback, None)
                
            print(f"DEBUG: Locked onto {len(self.locked_hwnds)} target windows.")

    def _monitor_loop(self):
        """The core loop. Sleeps for 60 seconds between checks."""
        while self.running:
            if self.locked_hwnds:
                self._check_windows()
            
            if self.watch_folder and os.path.exists(self.watch_folder):
                self._check_io_heartbeat()
                
            self._check_storage()
            
            time.sleep(60)

    def _check_windows(self):
        """Validates that the specific locked HWNDs still exist."""
        for hwnd, title in self.locked_hwnds.items():
            if hwnd in self.known_dead_hwnds:
                continue
                
            # win32gui.IsWindow checks the OS handle table directly. 
            # It works flawlessly even if the PC is locked on the Secure Desktop.
            if not win32gui.IsWindow(hwnd):
                self.notifier.send(
                    f"The tracked window '{title}' has closed. Batch finished or crashed.", 
                    "Window Terminated", 
                    "skull"
                )
                self.known_dead_hwnds.add(hwnd)

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
                        pass 
        except Exception:
            return

        if newest_time == 0:
            return 

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
            self.stalled_warned = False 

    def _check_storage(self):
        """Checks the C: drive for critical storage exhaustion."""
        try:
            _, _, free = shutil.disk_usage("C:\\")
            free_gb = free / (2**30) 
            
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
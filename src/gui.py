import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class SentinelGUI:
    def __init__(self, root, daemon, notifier, default_config, save_callback):
        self.root = root
        self.daemon = daemon
        self.notifier = notifier
        self.save_callback = save_callback
        
        self.root.title("ProcessSentinel - Lab Watchdog")
        self.root.geometry("500x600")
        self.root.resizable(False, False)

        # State Variables
        self.ntfy_url_var = tk.StringVar(value=default_config.get("ntfy_url", "https://ntfy.sh/mzf_FAU_GRA_Monitoring"))
        self.folder_var = tk.StringVar(value=default_config.get("watch_folder", ""))
        self.stall_var = tk.StringVar(value=str(default_config.get("stalled_mins", 15)))
        self.storage_var = tk.StringVar(value=str(default_config.get("min_storage_gb", 10)))
        self.processes = default_config.get("processes", ["ArcGISPro.exe"])

        self._build_ui()
        self._update_process_listbox()

    def _build_ui(self):
        """Constructs the visual layout."""
        pad = {'padx': 10, 'pady': 5}
        
        # --- Network Settings ---
        network_frame = ttk.LabelFrame(self.root, text="Notification Settings")
        network_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(network_frame, text="Ntfy Topic URL:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(network_frame, textvariable=self.ntfy_url_var, width=45).grid(row=0, column=1, **pad)

        # --- Process Tracking ---
        proc_frame = ttk.LabelFrame(self.root, text="Target Processes")
        proc_frame.pack(fill="x", padx=10, pady=5)

        self.proc_entry = ttk.Entry(proc_frame, width=30)
        self.proc_entry.grid(row=0, column=0, **pad)
        ttk.Button(proc_frame, text="Add Process", command=self._add_process).grid(row=0, column=1, **pad)
        
        self.proc_listbox = tk.Listbox(proc_frame, height=4, width=45)
        self.proc_listbox.grid(row=1, column=0, columnspan=2, **pad)
        ttk.Button(proc_frame, text="Remove Selected", command=self._remove_process).grid(row=2, column=0, columnspan=2, sticky="ew", **pad)

        # --- I/O & Storage Monitoring ---
        io_frame = ttk.LabelFrame(self.root, text="I/O and Storage Heartbeat")
        io_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(io_frame, text="Scratch/Temp Folder:").grid(row=0, column=0, sticky="w", **pad)
        folder_subframe = ttk.Frame(io_frame)
        folder_subframe.grid(row=1, column=0, columnspan=2, sticky="ew", **pad)
        ttk.Entry(folder_subframe, textvariable=self.folder_var, width=35).pack(side="left", padx=(0, 5))
        ttk.Button(folder_subframe, text="Browse", command=self._browse_folder).pack(side="left")

        ttk.Label(io_frame, text="Stall Alert (mins of inactivity):").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(io_frame, textvariable=self.stall_var, width=10).grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(io_frame, text="Storage Warning Threshold (GB):").grid(row=3, column=0, sticky="w", **pad)
        ttk.Entry(io_frame, textvariable=self.storage_var, width=10).grid(row=3, column=1, sticky="w", **pad)

        # --- Controls ---
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill="x", padx=10, pady=20)

        self.status_lbl = ttk.Label(control_frame, text="Status: IDLE", font=("Arial", 12, "bold"), foreground="gray")
        self.status_lbl.pack(pady=5)

        self.btn_start = ttk.Button(control_frame, text="START MONITORING", command=self._start_monitoring)
        self.btn_start.pack(fill="x", pady=2)
        
        self.btn_stop = ttk.Button(control_frame, text="STOP MONITORING", command=self._stop_monitoring, state="disabled")
        self.btn_stop.pack(fill="x", pady=2)

    def _update_process_listbox(self):
        """Refreshes the visual list of tracked processes."""
        self.proc_listbox.delete(0, tk.END)
        for p in self.processes:
            self.proc_listbox.insert(tk.END, p)

    def _add_process(self):
        proc = self.proc_entry.get().strip()
        if proc and proc not in self.processes:
            self.processes.append(proc)
            self._update_process_listbox()
            self.proc_entry.delete(0, tk.END)

    def _remove_process(self):
        selection = self.proc_listbox.curselection()
        if selection:
            index = selection[0]
            del self.processes[index]
            self._update_process_listbox()

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Select Scratch/Output Folder")
        if folder:
            self.folder_var.set(folder)

    def _start_monitoring(self):
        """Passes current GUI settings to the background thread and starts it."""
        try:
            stall = float(self.stall_var.get())
            storage = float(self.storage_var.get())
        except ValueError:
            messagebox.showerror("Input Error", "Stall Alert and Storage Threshold must be numbers.")
            return

        # Update the notifier and daemon with the latest GUI values
        self.notifier.set_topic(self.ntfy_url_var.get())
        self.daemon.update_config(
            processes=self.processes,
            folder=self.folder_var.get(),
            stall_mins=stall,
            storage_gb=storage
        )
        
        # Save config for next launch
        self._save_current_config()
        
        self.daemon.start()
        
        self.status_lbl.config(text="Status: MONITORING ACTIVE", foreground="green")
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.notifier.send("Dashboard started monitoring pipeline.", "ProcessSentinel Started", "rocket")

    def _stop_monitoring(self):
        """Kills the background thread."""
        self.daemon.stop()
        self.status_lbl.config(text="Status: IDLE", foreground="gray")
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.notifier.send("Monitoring manually stopped via dashboard.", "ProcessSentinel Stopped", "stop_sign")

    def _save_current_config(self):
        """Packages GUI data and sends it to main.py to save to config.json."""
        current_data = {
            "ntfy_url": self.ntfy_url_var.get(),
            "processes": self.processes,
            "watch_folder": self.folder_var.get(),
            "stalled_mins": float(self.stall_var.get()),
            "min_storage_gb": float(self.storage_var.get())
        }
        self.save_callback(current_data)
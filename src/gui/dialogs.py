import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from typing import Optional

from channels import ChannelRegistry, NotificationChannel
from monitors.base import BaseMonitor
from monitors.process import ProcessStepDownMonitor, ProcessInstanceMonitor
from monitors.storage import StorageMultiTierMonitor, DirectorySizeMonitor
from monitors.io_heartbeat import IOMonitor
from monitors.resource import ResourceMonitor
from monitors.network import HTTPEndpointMonitor, LocalPortMonitor

class ChannelDialog(ctk.CTkToplevel):
    def __init__(self, parent, channel: Optional[NotificationChannel] = None, on_save=None):
        super().__init__(parent)
        self.channel = channel
        self.on_save = on_save

        self.title("Edit Channel" if channel else "Add Notification Channel")
        self.geometry("450x260")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 15, "pady": 8}
        ctk.CTkLabel(self, text="Channel Alias Name:", font=("Segoe UI", 12, "bold")).pack(anchor="w", **pad)
        self.name_entry = ctk.CTkEntry(self, width=400, placeholder_text="e.g. My Phone, Lab IT Alerts")
        self.name_entry.pack(anchor="w", padx=15)
        if self.channel:
            self.name_entry.insert(0, self.channel.name)

        ctk.CTkLabel(self, text="ntfy.sh Topic URL:", font=("Segoe UI", 12, "bold")).pack(anchor="w", **pad)
        self.url_entry = ctk.CTkEntry(self, width=400, placeholder_text="e.g. https://ntfy.sh/my_private_topic")
        self.url_entry.pack(anchor="w", padx=15)
        if self.channel:
            self.url_entry.insert(0, self.channel.url)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=20)

        ctk.CTkButton(btn_frame, text="Save Channel", command=self._save, width=120).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, fg_color="gray", width=90).pack(side="right", padx=5)

    def _save(self):
        name = self.name_entry.get().strip()
        url = self.url_entry.get().strip()
        if not name or not url:
            messagebox.showerror("Validation Error", "Both Channel Name and Topic URL are required.")
            return

        if self.on_save:
            self.on_save(name, url, self.channel.id if self.channel else None)
        self.destroy()

class MonitorDialog(ctk.CTkToplevel):
    def __init__(self, parent, channel_registry: ChannelRegistry, monitor: Optional[BaseMonitor] = None, on_save=None):
        super().__init__(parent)
        self.channel_registry = channel_registry
        self.monitor = monitor
        self.on_save = on_save

        self.title("Edit Monitor" if monitor else "Add New Monitor")
        self.geometry("620x720")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 15, "pady": 6}

        scroll = ctk.CTkScrollableFrame(self, width=580, height=620)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(scroll, text="Monitor Name:", font=("Segoe UI", 12, "bold")).pack(anchor="w", **pad)
        self.name_entry = ctk.CTkEntry(scroll, width=540, placeholder_text="e.g. ArcGIS Pro Batch Watcher")
        self.name_entry.pack(anchor="w", padx=15)
        if self.monitor:
            self.name_entry.insert(0, self.monitor.name)

        ctk.CTkLabel(scroll, text="Monitor Type:", font=("Segoe UI", 12, "bold")).pack(anchor="w", **pad)
        self.type_options = {
            "Process Step-Down (Window High-Watermark)": "ProcessStepDown",
            "Process Instance Count (Headless / Daemon)": "ProcessInstance",
            "I/O Heartbeat (Multi-Path & File Filter)": "IOMonitor",
            "Storage Free Space (Multi-Tier)": "StorageMultiTier",
            "Process Resource Usage (CPU % / RAM MB)": "ResourceMonitor",
            "Directory Size Watcher": "DirectorySize",
            "HTTP / Web Endpoint Check": "HTTPEndpoint",
            "Local Network Port Check": "LocalPort"
        }
        self.reverse_type_options = {v: k for k, v in self.type_options.items()}

        current_display_type = self.reverse_type_options.get(self.monitor.monitor_type if self.monitor else "ProcessStepDown")
        self.type_var = ctk.StringVar(value=current_display_type)
        self.type_menu = ctk.CTkOptionMenu(
            scroll,
            values=list(self.type_options.keys()),
            variable=self.type_var,
            command=self._on_type_changed,
            width=540
        )
        self.type_menu.pack(anchor="w", padx=15)

        meta_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        meta_frame.pack(fill="x", padx=15, pady=8)

        ctk.CTkLabel(meta_frame, text="Interval (sec):", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        self.interval_entry = ctk.CTkEntry(meta_frame, width=90)
        self.interval_entry.grid(row=0, column=1, padx=8, sticky="w")
        self.interval_entry.insert(0, str(self.monitor.interval_seconds if self.monitor else 60))

        ctk.CTkLabel(meta_frame, text="Channel:", font=("Segoe UI", 12, "bold")).grid(row=0, column=2, padx=(12, 0), sticky="w")
        self.channel_map = {"[Inherit Default Channel]": None}
        for ch in self.channel_registry.channels:
            label = f"{ch.name} ({ch.url[:22]}...)"
            self.channel_map[label] = ch.id

        selected_label = "[Inherit Default Channel]"
        if self.monitor and self.monitor.channel_id:
            for lbl, cid in self.channel_map.items():
                if cid == self.monitor.channel_id:
                    selected_label = lbl
                    break

        self.channel_var = ctk.StringVar(value=selected_label)
        self.channel_menu = ctk.CTkOptionMenu(
            meta_frame,
            values=list(self.channel_map.keys()),
            variable=self.channel_var,
            width=230
        )
        self.channel_menu.grid(row=0, column=3, padx=8, sticky="w")

        ctk.CTkFrame(scroll, height=2, fg_color="gray30").pack(fill="x", padx=15, pady=10)

        self.dynamic_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.dynamic_frame.pack(fill="both", expand=True, padx=15, pady=5)
        self._render_dynamic_fields()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=10)
        ctk.CTkButton(btn_frame, text="Save Monitor", command=self._save, width=140).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, fg_color="gray", width=90).pack(side="right", padx=5)

    def _on_type_changed(self, choice):
        self._render_dynamic_fields()

    def _render_dynamic_fields(self):
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()

        selected_code = self.type_options[self.type_var.get()]
        m = self.monitor if (self.monitor and self.monitor.monitor_type == selected_code) else None

        if selected_code == "ProcessStepDown":
            ctk.CTkLabel(self.dynamic_frame, text="Target Window / Process String:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 2))
            self.target_entry = ctk.CTkEntry(self.dynamic_frame, width=520, placeholder_text="e.g. ArcGISPro.exe or Textron Systems")
            self.target_entry.pack(anchor="w")
            if m: self.target_entry.insert(0, m.target)

            ctk.CTkLabel(self.dynamic_frame, text="Initial Instance/Window Count:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            self.init_count_entry = ctk.CTkEntry(self.dynamic_frame, width=120)
            self.init_count_entry.pack(anchor="w")
            self.init_count_entry.insert(0, str(m.initial_count if m else 3))

            ctk.CTkLabel(self.dynamic_frame, text="Match Mode:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            self.match_mode_var = ctk.StringVar(value=m.match_mode if m else "window_title")
            ctk.CTkOptionMenu(self.dynamic_frame, values=["window_title", "process_name"], variable=self.match_mode_var).pack(anchor="w")

            ctk.CTkLabel(self.dynamic_frame, text="Step-Down Message Template:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            self.step_msg_entry = ctk.CTkEntry(self.dynamic_frame, width=520)
            self.step_msg_entry.pack(anchor="w")
            self.step_msg_entry.insert(0, m.step_down_message if m else "Tracked window count dropped to {count}.")

            ctk.CTkLabel(self.dynamic_frame, text="Critical (All Closed) Message Template:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            self.crit_msg_entry = ctk.CTkEntry(self.dynamic_frame, width=520)
            self.crit_msg_entry.pack(anchor="w")
            self.crit_msg_entry.insert(0, m.critical_message if m else "CRITICAL: All '{target}' windows have closed!")

        elif selected_code == "ProcessInstance":
            ctk.CTkLabel(self.dynamic_frame, text="Target Process Name:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 2))
            self.target_entry = ctk.CTkEntry(self.dynamic_frame, width=520, placeholder_text="e.g. worker.exe")
            self.target_entry.pack(anchor="w")
            if m: self.target_entry.insert(0, m.target)

            ctk.CTkLabel(self.dynamic_frame, text="Trigger Condition & Threshold:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            cond_frame = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            cond_frame.pack(fill="x")
            self.cond_var = ctk.StringVar(value=m.condition if m else "below")
            ctk.CTkOptionMenu(cond_frame, values=["below", "above", "equals"], variable=self.cond_var, width=120).pack(side="left")
            ctk.CTkLabel(cond_frame, text=" Threshold: ").pack(side="left")
            self.thresh_entry = ctk.CTkEntry(cond_frame, width=80)
            self.thresh_entry.pack(side="left")
            self.thresh_entry.insert(0, str(m.threshold if m else 1))

        elif selected_code == "IOMonitor":
            ctk.CTkLabel(self.dynamic_frame, text="Folders to Watch (Semicolon Separated):", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 2))
            path_frame = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            path_frame.pack(fill="x")
            self.paths_entry = ctk.CTkEntry(path_frame, width=420, placeholder_text="D:\\GIS\\Outputs; E:\\Temp")
            self.paths_entry.pack(side="left", fill="x", expand=True)
            if m: self.paths_entry.insert(0, "; ".join(m.paths))
            ctk.CTkButton(path_frame, text="Add Folder", width=90, command=self._browse_folder).pack(side="left", padx=(5, 0))

            ctk.CTkLabel(self.dynamic_frame, text="File Extension Filters (e.g. *.shp, *.gdb, *.csv):", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            self.filters_entry = ctk.CTkEntry(self.dynamic_frame, width=520, placeholder_text="*.shp, *.gdb, *.csv")
            self.filters_entry.pack(anchor="w")
            self.filters_entry.insert(0, ", ".join(m.filters) if m else "*.shp, *.gdb, *.csv")

            ctk.CTkLabel(self.dynamic_frame, text="Stall Alert After (Minutes of Inactivity):", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            self.stall_entry = ctk.CTkEntry(self.dynamic_frame, width=120)
            self.stall_entry.pack(anchor="w")
            self.stall_entry.insert(0, str(m.stall_minutes if m else 15.0))

        elif selected_code == "StorageMultiTier":
            ctk.CTkLabel(self.dynamic_frame, text="Target Drive Letter:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 2))
            self.drive_entry = ctk.CTkEntry(self.dynamic_frame, width=120, placeholder_text="C:\\")
            self.drive_entry.pack(anchor="w")
            self.drive_entry.insert(0, m.drive if m else "C:\\")

            ctk.CTkLabel(self.dynamic_frame, text="Warning Tier Threshold (GB):", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            self.tier1_entry = ctk.CTkEntry(self.dynamic_frame, width=120)
            self.tier1_entry.pack(anchor="w")
            self.tier1_entry.insert(0, "30.0")

            ctk.CTkLabel(self.dynamic_frame, text="Critical Tier Threshold (GB):", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            self.tier2_entry = ctk.CTkEntry(self.dynamic_frame, width=120)
            self.tier2_entry.pack(anchor="w")
            self.tier2_entry.insert(0, "20.0")

            ctk.CTkLabel(self.dynamic_frame, text="Fatal Tier Threshold (GB):", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            self.tier3_entry = ctk.CTkEntry(self.dynamic_frame, width=120)
            self.tier3_entry.pack(anchor="w")
            self.tier3_entry.insert(0, "10.0")

        elif selected_code == "ResourceMonitor":
            ctk.CTkLabel(self.dynamic_frame, text="Target Process Name:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 2))
            self.target_entry = ctk.CTkEntry(self.dynamic_frame, width=520, placeholder_text="e.g. ArcGISPro.exe")
            self.target_entry.pack(anchor="w")
            if m: self.target_entry.insert(0, m.target)

            ctk.CTkLabel(self.dynamic_frame, text="Metric:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            self.metric_var = ctk.StringVar(value=m.metric if m else "cpu_percent")
            ctk.CTkOptionMenu(self.dynamic_frame, values=["cpu_percent", "memory_mb"], variable=self.metric_var).pack(anchor="w")

            ctk.CTkLabel(self.dynamic_frame, text="Condition & Threshold:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            r_frame = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            r_frame.pack(fill="x")
            self.cond_var = ctk.StringVar(value=m.condition if m else "below")
            ctk.CTkOptionMenu(r_frame, values=["below", "above"], variable=self.cond_var, width=100).pack(side="left")
            self.r_thresh_entry = ctk.CTkEntry(r_frame, width=120)
            self.r_thresh_entry.pack(side="left", padx=10)
            self.r_thresh_entry.insert(0, str(m.threshold if m else 5.0))

        elif selected_code == "DirectorySize":
            ctk.CTkLabel(self.dynamic_frame, text="Directory Path:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 2))
            d_frame = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            d_frame.pack(fill="x")
            self.dir_path_entry = ctk.CTkEntry(d_frame, width=420)
            self.dir_path_entry.pack(side="left", fill="x", expand=True)
            if m: self.dir_path_entry.insert(0, m.path)
            ctk.CTkButton(d_frame, text="Browse", width=90, command=self._browse_single_dir).pack(side="left", padx=(5, 0))

            ctk.CTkLabel(self.dynamic_frame, text="Max Size Allowed (GB):", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            self.dir_size_entry = ctk.CTkEntry(self.dynamic_frame, width=120)
            self.dir_size_entry.pack(anchor="w")
            self.dir_size_entry.insert(0, str(m.max_size_gb if m else 50.0))

        elif selected_code == "HTTPEndpoint":
            ctk.CTkLabel(self.dynamic_frame, text="Target URL:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 2))
            self.url_entry = ctk.CTkEntry(self.dynamic_frame, width=520, placeholder_text="http://localhost:8080/health")
            self.url_entry.pack(anchor="w")
            if m: self.url_entry.insert(0, m.url)

            ctk.CTkLabel(self.dynamic_frame, text="Expected Status Code:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            self.status_code_entry = ctk.CTkEntry(self.dynamic_frame, width=120)
            self.status_code_entry.pack(anchor="w")
            self.status_code_entry.insert(0, str(m.expected_status if m else 200))

        elif selected_code == "LocalPort":
            ctk.CTkLabel(self.dynamic_frame, text="Port Number (e.g. 5432, 6379):", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 2))
            self.port_entry = ctk.CTkEntry(self.dynamic_frame, width=120)
            self.port_entry.pack(anchor="w")
            self.port_entry.insert(0, str(m.port if m else 5432))

            ctk.CTkLabel(self.dynamic_frame, text="Host Address:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            self.host_entry = ctk.CTkEntry(self.dynamic_frame, width=200)
            self.host_entry.pack(anchor="w")
            self.host_entry.insert(0, m.host if m else "127.0.0.1")

    def _browse_folder(self):
        f = filedialog.askdirectory(title="Select Output/Scratch Folder to Watch")
        if f:
            cur = self.paths_entry.get().strip()
            self.paths_entry.delete(0, tk.END)
            self.paths_entry.insert(0, f"{cur}; {f}" if cur else f)

    def _browse_single_dir(self):
        f = filedialog.askdirectory(title="Select Folder")
        if f:
            self.dir_path_entry.delete(0, tk.END)
            self.dir_path_entry.insert(0, f)

    def _save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Monitor Name is required.")
            return

        try:
            interval = int(self.interval_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Interval must be an integer (seconds).")
            return

        channel_id = self.channel_map.get(self.channel_var.get())
        selected_code = self.type_options[self.type_var.get()]
        mon_id = self.monitor.id if self.monitor else None

        try:
            if selected_code == "ProcessStepDown":
                target = self.target_entry.get().strip()
                if not target: raise ValueError("Target process/window name is required.")
                init_cnt = int(self.init_count_entry.get().strip())
                new_mon = ProcessStepDownMonitor(
                    name=name,
                    target=target,
                    initial_count=init_cnt,
                    match_mode=self.match_mode_var.get(),
                    step_down_message=self.step_msg_entry.get().strip(),
                    critical_message=self.crit_msg_entry.get().strip(),
                    interval_seconds=interval,
                    channel_id=channel_id,
                    monitor_id=mon_id
                )

            elif selected_code == "ProcessInstance":
                target = self.target_entry.get().strip()
                if not target: raise ValueError("Target process name is required.")
                thresh = int(self.thresh_entry.get().strip())
                new_mon = ProcessInstanceMonitor(
                    name=name,
                    target=target,
                    condition=self.cond_var.get(),
                    threshold=thresh,
                    interval_seconds=interval,
                    channel_id=channel_id,
                    monitor_id=mon_id
                )

            elif selected_code == "IOMonitor":
                paths = [p.strip() for p in self.paths_entry.get().split(";") if p.strip()]
                if not paths: raise ValueError("At least one watch path is required.")
                filters = [f.strip() for f in self.filters_entry.get().split(",") if f.strip()]
                stall_m = float(self.stall_entry.get().strip())
                new_mon = IOMonitor(
                    name=name,
                    paths=paths,
                    filters=filters,
                    stall_minutes=stall_m,
                    interval_seconds=interval,
                    channel_id=channel_id,
                    monitor_id=mon_id
                )

            elif selected_code == "StorageMultiTier":
                drive = self.drive_entry.get().strip()
                t1 = float(self.tier1_entry.get().strip())
                t2 = float(self.tier2_entry.get().strip())
                t3 = float(self.tier3_entry.get().strip())
                tiers = [
                    {"gb": t1, "message": f"Storage Warning: Only {{free_gb:.1f}} GB remaining on {drive}", "tag": "warning", "level": "warning", "channel_id": None},
                    {"gb": t2, "message": f"Critical Warning: Only {{free_gb:.1f}} GB remaining on {drive}!", "tag": "rotating_light", "level": "critical", "channel_id": None},
                    {"gb": t3, "message": f"FATAL: Only {{free_gb:.1f}} GB remaining on {drive}!", "tag": "skull,fire", "level": "critical", "channel_id": None}
                ]
                new_mon = StorageMultiTierMonitor(
                    name=name,
                    drive=drive,
                    tiers=tiers,
                    interval_seconds=interval,
                    channel_id=channel_id,
                    monitor_id=mon_id
                )

            elif selected_code == "ResourceMonitor":
                target = self.target_entry.get().strip()
                if not target: raise ValueError("Target process name is required.")
                thresh = float(self.r_thresh_entry.get().strip())
                new_mon = ResourceMonitor(
                    name=name,
                    target=target,
                    metric=self.metric_var.get(),
                    condition=self.cond_var.get(),
                    threshold=thresh,
                    interval_seconds=interval,
                    channel_id=channel_id,
                    monitor_id=mon_id
                )

            elif selected_code == "DirectorySize":
                path = self.dir_path_entry.get().strip()
                if not path: raise ValueError("Directory path is required.")
                max_gb = float(self.dir_size_entry.get().strip())
                new_mon = DirectorySizeMonitor(
                    name=name,
                    path=path,
                    max_size_gb=max_gb,
                    interval_seconds=interval,
                    channel_id=channel_id,
                    monitor_id=mon_id
                )

            elif selected_code == "HTTPEndpoint":
                url = self.url_entry.get().strip()
                if not url: raise ValueError("URL is required.")
                sc = int(self.status_code_entry.get().strip())
                new_mon = HTTPEndpointMonitor(
                    name=name,
                    url=url,
                    expected_status=sc,
                    interval_seconds=interval,
                    channel_id=channel_id,
                    monitor_id=mon_id
                )

            elif selected_code == "LocalPort":
                port = int(self.port_entry.get().strip())
                host = self.host_entry.get().strip() or "127.0.0.1"
                new_mon = LocalPortMonitor(
                    name=name,
                    port=port,
                    host=host,
                    interval_seconds=interval,
                    channel_id=channel_id,
                    monitor_id=mon_id
                )

            if self.on_save:
                self.on_save(new_mon)
            self.destroy()

        except Exception as e:
            messagebox.showerror("Validation Error", str(e))

import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from typing import Optional, List, Dict, Any

from channels import ChannelRegistry, NotificationChannel
from monitors.base import BaseMonitor
from monitors.process import ProcessStepDownMonitor, ProcessInstanceMonitor
from monitors.storage import StorageMultiTierMonitor, DirectorySizeMonitor
from monitors.io_heartbeat import IOMonitor
from monitors.resource import ResourceMonitor
from monitors.network import HTTPEndpointMonitor, LocalPortMonitor
from gui.collapsible_frame import CTkCollapsibleFrame

class ChannelDialog(ctk.CTkToplevel):
    def __init__(self, parent, channel: Optional[NotificationChannel] = None, on_save=None):
        super().__init__(parent)
        self.channel = channel
        self.on_save = on_save

        self.title("Edit Channel" if channel else "Add Notification Channel")
        self.geometry("480x350")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 15, "pady": 6}
        ctk.CTkLabel(self, text="Channel Alias Name:", font=("Segoe UI", 12, "bold")).pack(anchor="w", **pad)
        self.name_entry = ctk.CTkEntry(self, width=440, placeholder_text="e.g. My Phone, Lab IT Alerts")
        self.name_entry.pack(anchor="w", padx=15)
        if self.channel:
            self.name_entry.insert(0, self.channel.name)

        ctk.CTkLabel(self, text="ntfy.sh Topic URL:", font=("Segoe UI", 12, "bold")).pack(anchor="w", **pad)
        self.url_entry = ctk.CTkEntry(self, width=440, placeholder_text="e.g. https://ntfy.sh/my_private_topic")
        self.url_entry.pack(anchor="w", padx=15)
        if self.channel:
            self.url_entry.insert(0, self.channel.url)

        ctk.CTkLabel(self, text="Access Token (Optional - for private / self-hosted topics):", font=("Segoe UI", 12, "bold")).pack(anchor="w", **pad)
        self.token_entry = ctk.CTkEntry(self, width=440, placeholder_text="e.g. tk_... (leave empty for public topics)", show="*")
        self.token_entry.pack(anchor="w", padx=15)
        if self.channel and self.channel.auth_token:
            self.token_entry.insert(0, self.channel.auth_token)

        self.show_token_var = ctk.BooleanVar(value=False)
        def toggle_token():
            self.token_entry.configure(show="" if self.show_token_var.get() else "*")
        ctk.CTkCheckBox(self, text="Show Token", variable=self.show_token_var, command=toggle_token, font=("Segoe UI", 11)).pack(anchor="w", padx=15, pady=(4, 0))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(15, 10))

        ctk.CTkButton(btn_frame, text="Save Channel", command=self._save, width=120).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, fg_color="gray", width=90).pack(side="right", padx=5)

    def _save(self):
        name = self.name_entry.get().strip()
        url = self.url_entry.get().strip()
        token = self.token_entry.get().strip() or None
        if not name or not url:
            messagebox.showerror("Validation Error", "Both Channel Name and Topic URL are required.")
            return

        if self.on_save:
            self.on_save(name, url, token, self.channel.id if self.channel else None)
        self.destroy()


class MonitorDialog(ctk.CTkToplevel):
    def __init__(self, parent, channel_registry: ChannelRegistry, monitor: Optional[BaseMonitor] = None, on_save=None):
        super().__init__(parent)
        self.channel_registry = channel_registry
        self.monitor = monitor
        self.on_save = on_save

        self.title("Edit Monitor" if monitor else "Add New Monitor")
        self.geometry("640x760")
        self.resizable(True, True)
        self.minsize(580, 600)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 15, "pady": 5}

        scroll = ctk.CTkScrollableFrame(self, width=600, height=660)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        self.scroll = scroll

        # 1. Name
        ctk.CTkLabel(scroll, text="Monitor Name:", font=("Segoe UI", 12, "bold")).pack(anchor="w", **pad)
        self.name_entry = ctk.CTkEntry(scroll, width=560, placeholder_text="e.g. ArcGIS Pro Batch Watcher")
        self.name_entry.pack(anchor="w", padx=15)
        if self.monitor:
            self.name_entry.insert(0, self.monitor.name)
        self.name_entry.bind("<KeyRelease>", lambda e: self._refresh_preview())

        # 2. Type Menu
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
            width=560
        )
        self.type_menu.pack(anchor="w", padx=15)

        # 3. Metadata: Interval & Channel
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

        # 4. Tier 1: Priority Segmented Selector (Hidden dynamically for Multi-Tier monitors)
        self.prio_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.prio_frame.pack(fill="x", padx=15, pady=(4, 8))
        ctk.CTkLabel(self.prio_frame, text="Alert Priority (Urgency):", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 4))

        self.priority_map = {
            "Low (2)": 2,
            "Normal (3)": 3,
            "High (4)": 4,
            "Urgent (5)": 5
        }
        self.reverse_priority_map = {v: k for k, v in self.priority_map.items()}

        default_prio = 5 if (self.monitor and self.monitor.monitor_type == "ProcessStepDown") else 4
        current_prio = self.monitor.priority if self.monitor else default_prio
        self.prio_var = ctk.StringVar(value=self.reverse_priority_map.get(current_prio, "High (4)"))
        self.prio_seg = ctk.CTkSegmentedButton(
            self.prio_frame,
            values=list(self.priority_map.keys()),
            variable=self.prio_var,
            command=lambda v: self._refresh_preview()
        )
        self.prio_seg.pack(fill="x")

        self.prio_divider = ctk.CTkFrame(scroll, height=2, fg_color="gray30")
        self.prio_divider.pack(fill="x", padx=15, pady=8)

        # 5. Dynamic Frame (Condition & Threshold Settings)
        self.dynamic_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.dynamic_frame.pack(fill="both", expand=True, padx=15, pady=2)
        self._render_dynamic_fields()
        self._update_prio_visibility()

        # 6. Tier 2: Progressive Disclosure Collapsible Frame (Notification Styling)
        self.notif_accordion = CTkCollapsibleFrame(
            scroll,
            title="⚙ Notification Customization & Styling",
            is_expanded=False
        )
        self.notif_accordion.pack(fill="x", padx=15, pady=(10, 8))
        self._build_accordion_content()

        # 7. Bottom Dialog Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=10)
        ctk.CTkButton(btn_frame, text="Save Monitor", command=self._save, width=140).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, fg_color="gray", width=90).pack(side="right", padx=5)

    def _build_accordion_content(self):
        container = self.notif_accordion.content_frame

        # Title Template
        ctk.CTkLabel(container, text="Custom Alert Title Template:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        self.notif_title_entry = ctk.CTkEntry(container, width=530, placeholder_text="e.g. {name}: Alert (leave empty for smart default)")
        self.notif_title_entry.pack(anchor="w", padx=10)
        if self.monitor and self.monitor.title_template:
            self.notif_title_entry.insert(0, self.monitor.title_template)
        self.notif_title_entry.bind("<KeyRelease>", lambda e: self._refresh_preview())

        # Tags & Quick Emoji Palette
        ctk.CTkLabel(container, text="Notification Emojis & Tags (ntfy shortcodes):", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        
        # Emoji pill button bar
        emoji_bar = ctk.CTkFrame(container, fg_color="transparent")
        emoji_bar.pack(fill="x", padx=10, pady=2)

        emoji_presets = [
            ("🚨 Urgent", "rotating_light"),
            ("⚠️ Warn", "warning"),
            ("💀 Skull", "skull"),
            ("🔥 Fire", "fire"),
            ("💾 Disk", "floppy_disk"),
            ("⏱️ Stall", "hourglass_done"),
            ("🌐 Web", "globe_with_meridians"),
            ("✅ OK", "white_check_mark")
        ]

        def on_emoji_click(code: str):
            cur = [t.strip() for t in self.notif_tags_entry.get().split(",") if t.strip()]
            if code in cur:
                cur.remove(code)
            else:
                cur.append(code)
            self.notif_tags_entry.delete(0, tk.END)
            self.notif_tags_entry.insert(0, ", ".join(cur))
            self._refresh_preview()

        for label, code in emoji_presets:
            btn = ctk.CTkButton(
                emoji_bar,
                text=label,
                width=60,
                height=24,
                font=("Segoe UI", 10),
                fg_color="#333333",
                hover_color="#444444",
                command=lambda c=code: on_emoji_click(c)
            )
            btn.pack(side="left", padx=2)

        self.notif_tags_entry = ctk.CTkEntry(container, width=530, placeholder_text="e.g. warning, skull (comma-separated)")
        self.notif_tags_entry.pack(anchor="w", padx=10, pady=(4, 0))
        if self.monitor and self.monitor.tags:
            self.notif_tags_entry.insert(0, self.monitor.tags)
        self.notif_tags_entry.bind("<KeyRelease>", lambda e: self._refresh_preview())

        # Custom Message Template & Token Chips
        ctk.CTkLabel(container, text="Alert Message Template:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 2))

        # Token helper chips container
        self.token_chips_frame = ctk.CTkFrame(container, fg_color="transparent")
        self.token_chips_frame.pack(fill="x", padx=10, pady=2)
        self._render_token_chips()

        self.notif_msg_entry = ctk.CTkEntry(container, width=530, placeholder_text="Custom message text (supports variable tokens)")
        self.notif_msg_entry.pack(anchor="w", padx=10)
        
        # Initial message template based on monitor
        if self.monitor:
            msg_val = getattr(self.monitor, "message", None)
            if not msg_val and hasattr(self.monitor, "step_down_message"):
                msg_val = self.monitor.step_down_message
            if msg_val:
                self.notif_msg_entry.insert(0, msg_val)
        self.notif_msg_entry.bind("<KeyRelease>", lambda e: self._refresh_preview())

        # Click URL
        ctk.CTkLabel(container, text="Click Action URL (Opens when notification is tapped):", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        self.click_url_entry = ctk.CTkEntry(container, width=530, placeholder_text="e.g. https://grafana.internal or http://localhost:8080")
        self.click_url_entry.pack(anchor="w", padx=10)
        if self.monitor and self.monitor.click_url:
            self.click_url_entry.insert(0, self.monitor.click_url)

        # Markdown Switch
        self.markdown_var = ctk.BooleanVar(value=self.monitor.markdown_enabled if self.monitor else True)
        ctk.CTkSwitch(container, text="Enable Markdown formatting in notification body", variable=self.markdown_var, font=("Segoe UI", 11)).pack(anchor="w", padx=10, pady=(8, 4))

        # Recovery Notification Switch
        self.recovery_var = ctk.BooleanVar(value=getattr(self.monitor, "recovery_notification", False) if self.monitor else False)
        ctk.CTkSwitch(container, text="Send Recovery Notification when condition resolves / returns to normal", variable=self.recovery_var, font=("Segoe UI", 11)).pack(anchor="w", padx=10, pady=(4, 6))

        # Phone Simulation Preview Card
        ctk.CTkLabel(container, text="📱 Notification Preview (Mobile Banner Simulation):", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        self.preview_card = ctk.CTkFrame(container, fg_color="#121212", corner_radius=8, border_width=1, border_color="#333333")
        self.preview_card.pack(fill="x", padx=10, pady=(2, 8))

        p_header = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        p_header.pack(fill="x", padx=12, pady=(8, 2))

        self.preview_badge = ctk.CTkLabel(p_header, text="⚠️", font=("Segoe UI", 13))
        self.preview_badge.pack(side="left")

        self.preview_meta = ctk.CTkLabel(p_header, text="ProcessSentinel • just now", font=("Segoe UI", 10), text_color="gray60")
        self.preview_meta.pack(side="left", padx=6)

        self.preview_prio_lbl = ctk.CTkLabel(p_header, text="HIGH", font=("Segoe UI", 9, "bold"), fg_color="#f77f00", corner_radius=4, padx=5)
        self.preview_prio_lbl.pack(side="right")

        self.preview_title = ctk.CTkLabel(self.preview_card, text="Alert Title", font=("Segoe UI", 12, "bold"), anchor="w")
        self.preview_title.pack(fill="x", padx=12, pady=(2, 2))

        self.preview_body = ctk.CTkLabel(self.preview_card, text="Message snippet preview...", font=("Segoe UI", 11), text_color="#cfcfcf", anchor="w", wraplength=480, justify="left")
        self.preview_body.pack(fill="x", padx=12, pady=(0, 8))

        # Test Notification Button
        self.btn_test_preview = ctk.CTkButton(
            container,
            text="⚡ Send Test Preview Notification",
            command=self._send_test_preview,
            height=28,
            fg_color="#1f6aa5",
            hover_color="#144f7a"
        )
        self.btn_test_preview.pack(fill="x", padx=10, pady=(4, 10))

        self._refresh_preview()

    def _render_token_chips(self):
        for w in self.token_chips_frame.winfo_children():
            w.destroy()

        selected_code = self.type_options[self.type_var.get()]
        chips_by_type = {
            "ProcessStepDown": ["{target}", "{count}", "{name}"],
            "ProcessInstance": ["{target}", "{count}", "{threshold}", "{name}"],
            "IOMonitor": ["{stall_mins}", "{name}"],
            "StorageMultiTier": ["{drive}", "{free_gb}", "{name}"],
            "ResourceMonitor": ["{target}", "{metric}", "{val}", "{threshold}", "{condition}", "{name}"],
            "DirectorySize": ["{path}", "{max_size_gb}", "{current_gb}", "{name}"],
            "HTTPEndpoint": ["{url}", "{status}", "{error}", "{name}"],
            "LocalPort": ["{port}", "{host}", "{name}"]
        }
        tokens = chips_by_type.get(selected_code, ["{name}"])

        ctk.CTkLabel(self.token_chips_frame, text="Insert Variable Token:", font=("Segoe UI", 10), text_color="gray60").pack(side="left", padx=(0, 6))

        def insert_token(tok: str):
            entry = self.notif_msg_entry
            entry.insert(tk.INSERT, tok)
            self._refresh_preview()

        for tok in tokens:
            b = ctk.CTkButton(
                self.token_chips_frame,
                text=f"+ {tok}",
                width=50,
                height=22,
                font=("Consolas", 10),
                fg_color="#2b3b4c",
                hover_color="#36506c",
                command=lambda t=tok: insert_token(t)
            )
            b.pack(side="left", padx=2)

    def _update_prio_visibility(self):
        selected_code = self.type_options.get(self.type_var.get())
        if selected_code == "StorageMultiTier":
            self.prio_frame.pack_forget()
            self.prio_divider.pack_forget()
        else:
            self.prio_frame.pack(fill="x", padx=15, pady=(4, 8), before=self.dynamic_frame)
            self.prio_divider.pack(fill="x", padx=15, pady=8, before=self.dynamic_frame)

    def _refresh_preview(self):
        if not hasattr(self, "preview_title"):
            return

        name = self.name_entry.get().strip() or "Sample Monitor"
        selected_code = self.type_options.get(self.type_var.get())
        if selected_code == "StorageMultiTier" and hasattr(self, "tier2_prio_var"):
            prio_num = self.priority_map.get(self.tier2_prio_var.get(), 4)
        else:
            prio_label = self.prio_var.get()
            prio_num = self.priority_map.get(prio_label, 4)

        # Update priority pill
        prio_colors = {2: "#495057", 3: "#1f6aa5", 4: "#f77f00", 5: "#d90429"}
        prio_names = {2: "LOW", 3: "NORMAL", 4: "HIGH", 5: "URGENT"}
        self.preview_prio_lbl.configure(text=prio_names.get(prio_num, "HIGH"), fg_color=prio_colors.get(prio_num, "#f77f00"))

        # Tags / Emoji icon
        tags_str = self.notif_tags_entry.get().strip()
        tags_list = [t.strip() for t in tags_str.split(",") if t.strip()]
        emoji_icon = "🔔"
        emoji_map = {
            "rotating_light": "🚨", "warning": "⚠️", "skull": "💀", "fire": "🔥",
            "floppy_disk": "💾", "hourglass_done": "⏱️", "globe_with_meridians": "🌐",
            "white_check_mark": "✅", "gear": "⚙️", "electric_plug": "🔌",
            "chart_with_upwards_trend": "📈", "chart_with_downwards_trend": "📉",
            "file_folder": "📁"
        }
        for t in tags_list:
            if t in emoji_map:
                emoji_icon = emoji_map[t]
                break
        self.preview_badge.configure(text=emoji_icon)

        # Title
        custom_title = self.notif_title_entry.get().strip()
        if custom_title:
            try:
                disp_title = custom_title.format(name=name, target="worker.exe", count=2, threshold=1, val=12.5, free_gb=18.4)
            except Exception:
                disp_title = custom_title
        else:
            disp_title = f"{name}: Alert"
        self.preview_title.configure(text=disp_title)

        # Message
        custom_msg = self.notif_msg_entry.get().strip()
        if custom_msg:
            try:
                disp_body = custom_msg.format(name=name, target="worker.exe", count=2, threshold=1, val=12.5, free_gb=18.4, stall_mins=16.0, port=5432, host="127.0.0.1", url="http://localhost:8080", status=500, error="Timeout")
            except Exception:
                disp_body = custom_msg
        else:
            disp_body = f"Notification triggered for '{name}'."
        self.preview_body.configure(text=disp_body)

    def _send_test_preview(self):
        channel_id = self.channel_map.get(self.channel_var.get())
        channel = self.channel_registry.get_channel(channel_id)

        if not channel or not channel.url:
            messagebox.showerror("Error", "Selected channel does not have a valid URL.")
            return

        selected_code = self.type_options.get(self.type_var.get())
        if selected_code == "StorageMultiTier" and hasattr(self, "tier2_prio_var"):
            prio_num = self.priority_map.get(self.tier2_prio_var.get(), 4)
        else:
            prio_num = self.priority_map.get(self.prio_var.get(), 4)
        title = self.preview_title.cget("text")
        message = self.preview_body.cget("text")
        tags = self.notif_tags_entry.get().strip()
        click = self.click_url_entry.get().strip() or None
        markdown = self.markdown_var.get()

        self.btn_test_preview.configure(text="Sending preview...", state="disabled", fg_color="#d97706")

        def worker():
            ok = channel.send(
                message=message,
                title=title,
                tags=tags,
                priority=prio_num,
                click_url=click,
                markdown=markdown
            )
            def on_finish():
                self.btn_test_preview.configure(text="⚡ Send Test Preview Notification", state="normal", fg_color="#1f6aa5")
                if ok:
                    messagebox.showinfo("Preview Delivered", f"Test notification sent to '{channel.name}' (Priority {prio_num})!")
                else:
                    messagebox.showerror("Send Failed", f"Failed sending to {channel.url}.\nCheck channel URL or network.")
            self.after(0, on_finish)

        threading.Thread(target=worker, daemon=True).start()

    def _on_type_changed(self, choice):
        self._update_prio_visibility()
        self._render_dynamic_fields()
        self._render_token_chips()

        # Update smart default tags & priority when switching monitor type
        selected_code = self.type_options[self.type_var.get()]
        type_defaults = {
            "ProcessStepDown": ("Urgent (5)", "skull,rotating_light"),
            "ProcessInstance": ("High (4)", "warning,gear"),
            "IOMonitor": ("High (4)", "warning,hourglass_done"),
            "StorageMultiTier": ("High (4)", "floppy_disk"),
            "ResourceMonitor": ("High (4)", "chart_with_upwards_trend"),
            "DirectorySize": ("High (4)", "file_folder,warning"),
            "HTTPEndpoint": ("High (4)", "globe_with_meridians,warning"),
            "LocalPort": ("High (4)", "electric_plug,warning")
        }
        if selected_code in type_defaults:
            rec_prio, rec_tags = type_defaults[selected_code]
            if not self.monitor:
                self.prio_var.set(rec_prio)
                self.notif_tags_entry.delete(0, tk.END)
                self.notif_tags_entry.insert(0, rec_tags)

        self._refresh_preview()

    def _render_dynamic_fields(self):
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()

        selected_code = self.type_options[self.type_var.get()]
        m = self.monitor if (self.monitor and self.monitor.monitor_type == selected_code) else None

        if selected_code == "ProcessStepDown":
            ctk.CTkLabel(self.dynamic_frame, text="Target Window / Process String:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 2))
            self.target_entry = ctk.CTkEntry(self.dynamic_frame, width=540, placeholder_text="e.g. ArcGISPro.exe or Textron Systems")
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
            self.step_msg_entry = ctk.CTkEntry(self.dynamic_frame, width=540)
            self.step_msg_entry.pack(anchor="w")
            self.step_msg_entry.insert(0, m.step_down_message if m else "Tracked window count dropped to {count}.")

            ctk.CTkLabel(self.dynamic_frame, text="Critical (All Closed) Message Template:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            self.crit_msg_entry = ctk.CTkEntry(self.dynamic_frame, width=540)
            self.crit_msg_entry.pack(anchor="w")
            self.crit_msg_entry.insert(0, m.critical_message if m else "CRITICAL: All '{target}' windows have closed!")

        elif selected_code == "ProcessInstance":
            ctk.CTkLabel(self.dynamic_frame, text="Target Process Name:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 2))
            self.target_entry = ctk.CTkEntry(self.dynamic_frame, width=540, placeholder_text="e.g. worker.exe")
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

            self.match_mode_var = ctk.StringVar(value=m.match_mode if m else "process_name")

        elif selected_code == "IOMonitor":
            ctk.CTkLabel(self.dynamic_frame, text="Folders to Watch (Semicolon Separated):", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 2))
            path_frame = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            path_frame.pack(fill="x")
            self.paths_entry = ctk.CTkEntry(path_frame, width=440, placeholder_text="D:\\GIS\\Outputs; E:\\Temp")
            self.paths_entry.pack(side="left", fill="x", expand=True)
            if m: self.paths_entry.insert(0, "; ".join(m.paths))
            ctk.CTkButton(path_frame, text="Add Folder", width=90, command=self._browse_folder).pack(side="left", padx=(5, 0))

            ctk.CTkLabel(self.dynamic_frame, text="File Extension Filters (e.g. *.shp, *.gdb, *.csv):", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            self.filters_entry = ctk.CTkEntry(self.dynamic_frame, width=540, placeholder_text="*.shp, *.gdb, *.csv")
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

            ctk.CTkLabel(self.dynamic_frame, text="Escalating Storage Tiers (Threshold & Urgency):", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 4))

            tier_prio_options = list(self.priority_map.keys())

            t1_gb, t1_prio = "30.0", 3
            t2_gb, t2_prio = "20.0", 4
            t3_gb, t3_prio = "10.0", 5
            if m and m.tiers and len(m.tiers) >= 3:
                sorted_tiers = sorted(m.tiers, key=lambda t: float(t.get("gb", 0)), reverse=True)
                t1_gb = str(sorted_tiers[0].get("gb", 30.0))
                t1_prio = sorted_tiers[0].get("priority", 3)
                t2_gb = str(sorted_tiers[1].get("gb", 20.0))
                t2_prio = sorted_tiers[1].get("priority", 4)
                t3_gb = str(sorted_tiers[2].get("gb", 10.0))
                t3_prio = sorted_tiers[2].get("priority", 5)

            # Row 1: Warning Tier
            row1 = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            row1.pack(fill="x", pady=3)
            ctk.CTkLabel(row1, text="Warning Tier:", width=100, anchor="w", font=("Segoe UI", 11, "bold")).pack(side="left")
            self.tier1_entry = ctk.CTkEntry(row1, width=80)
            self.tier1_entry.pack(side="left")
            self.tier1_entry.insert(0, t1_gb)
            ctk.CTkLabel(row1, text=" GB  ➜ Urgency: ", font=("Segoe UI", 11)).pack(side="left")
            self.tier1_prio_var = ctk.StringVar(value=self.reverse_priority_map.get(t1_prio, "Normal (3)"))
            ctk.CTkOptionMenu(row1, values=tier_prio_options, variable=self.tier1_prio_var, width=130, command=lambda v: self._refresh_preview()).pack(side="left")

            # Row 2: Critical Tier
            row2 = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            row2.pack(fill="x", pady=3)
            ctk.CTkLabel(row2, text="Critical Tier:", width=100, anchor="w", font=("Segoe UI", 11, "bold")).pack(side="left")
            self.tier2_entry = ctk.CTkEntry(row2, width=80)
            self.tier2_entry.pack(side="left")
            self.tier2_entry.insert(0, t2_gb)
            ctk.CTkLabel(row2, text=" GB  ➜ Urgency: ", font=("Segoe UI", 11)).pack(side="left")
            self.tier2_prio_var = ctk.StringVar(value=self.reverse_priority_map.get(t2_prio, "High (4)"))
            ctk.CTkOptionMenu(row2, values=tier_prio_options, variable=self.tier2_prio_var, width=130, command=lambda v: self._refresh_preview()).pack(side="left")

            # Row 3: Fatal Tier
            row3 = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            row3.pack(fill="x", pady=3)
            ctk.CTkLabel(row3, text="Fatal Tier:", width=100, anchor="w", font=("Segoe UI", 11, "bold")).pack(side="left")
            self.tier3_entry = ctk.CTkEntry(row3, width=80)
            self.tier3_entry.pack(side="left")
            self.tier3_entry.insert(0, t3_gb)
            ctk.CTkLabel(row3, text=" GB  ➜ Urgency: ", font=("Segoe UI", 11)).pack(side="left")
            self.tier3_prio_var = ctk.StringVar(value=self.reverse_priority_map.get(t3_prio, "Urgent (5)"))
            ctk.CTkOptionMenu(row3, values=tier_prio_options, variable=self.tier3_prio_var, width=130, command=lambda v: self._refresh_preview()).pack(side="left")

            self.step_down_var = ctk.BooleanVar(value=getattr(m, "step_down_mode", True) if m else True)
            ctk.CTkCheckBox(
                self.dynamic_frame,
                text="Step-Down Latching (Alert once per threshold until manual reset or recovery)",
                variable=self.step_down_var,
                font=("Segoe UI", 11, "bold")
            ).pack(anchor="w", pady=(8, 2))

        elif selected_code == "ResourceMonitor":
            ctk.CTkLabel(self.dynamic_frame, text="Target Process Name:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 2))
            self.target_entry = ctk.CTkEntry(self.dynamic_frame, width=540, placeholder_text="e.g. ArcGISPro.exe")
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
            self.dir_path_entry = ctk.CTkEntry(d_frame, width=440)
            self.dir_path_entry.pack(side="left", fill="x", expand=True)
            if m: self.dir_path_entry.insert(0, m.path)
            ctk.CTkButton(d_frame, text="Browse", width=90, command=self._browse_single_dir).pack(side="left", padx=(5, 0))

            ctk.CTkLabel(self.dynamic_frame, text="Max Size Allowed (GB):", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            self.dir_size_entry = ctk.CTkEntry(self.dynamic_frame, width=120)
            self.dir_size_entry.pack(anchor="w")
            self.dir_size_entry.insert(0, str(m.max_size_gb if m else 50.0))

        elif selected_code == "HTTPEndpoint":
            ctk.CTkLabel(self.dynamic_frame, text="Target URL:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 2))
            self.url_entry = ctk.CTkEntry(self.dynamic_frame, width=540, placeholder_text="http://localhost:8080/health")
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

        # Notification Customization Values
        prio = self.priority_map[self.prio_var.get()]
        custom_tags = self.notif_tags_entry.get().strip()
        custom_title = self.notif_title_entry.get().strip() or None
        custom_click = self.click_url_entry.get().strip() or None
        markdown_enabled = self.markdown_var.get()
        recovery_notif = self.recovery_var.get()
        custom_msg = self.notif_msg_entry.get().strip()

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
                    monitor_id=mon_id,
                    priority=prio,
                    tags=custom_tags or "skull,rotating_light",
                    title_template=custom_title,
                    click_url=custom_click,
                    markdown_enabled=markdown_enabled,
                    recovery_notification=recovery_notif
                )

            elif selected_code == "ProcessInstance":
                target = self.target_entry.get().strip()
                if not target: raise ValueError("Target process name is required.")
                thresh = int(self.thresh_entry.get().strip())
                msg = custom_msg or f"Process '{target}' instance count is {{count}} (threshold: {{threshold}})."
                new_mon = ProcessInstanceMonitor(
                    name=name,
                    target=target,
                    condition=self.cond_var.get(),
                    threshold=thresh,
                    match_mode=self.match_mode_var.get(),
                    message=msg,
                    interval_seconds=interval,
                    channel_id=channel_id,
                    monitor_id=mon_id,
                    priority=prio,
                    tags=custom_tags or "warning,gear",
                    title_template=custom_title,
                    click_url=custom_click,
                    markdown_enabled=markdown_enabled,
                    recovery_notification=recovery_notif
                )

            elif selected_code == "IOMonitor":
                paths = [p.strip() for p in self.paths_entry.get().split(";") if p.strip()]
                if not paths: raise ValueError("At least one watch path is required.")
                filters = [f.strip() for f in self.filters_entry.get().split(",") if f.strip()]
                stall_m = float(self.stall_entry.get().strip())
                msg = custom_msg or "No matching files modified in {stall_mins:.1f} mins across monitored paths. Pipeline stalled!"
                new_mon = IOMonitor(
                    name=name,
                    paths=paths,
                    filters=filters,
                    stall_minutes=stall_m,
                    message=msg,
                    interval_seconds=interval,
                    channel_id=channel_id,
                    monitor_id=mon_id,
                    priority=prio,
                    tags=custom_tags or "warning,hourglass_done",
                    title_template=custom_title,
                    click_url=custom_click,
                    markdown_enabled=markdown_enabled,
                    recovery_notification=recovery_notif
                )

            elif selected_code == "StorageMultiTier":
                drive = self.drive_entry.get().strip()
                t1 = float(self.tier1_entry.get().strip())
                t2 = float(self.tier2_entry.get().strip())
                t3 = float(self.tier3_entry.get().strip())
                p1 = self.priority_map.get(self.tier1_prio_var.get(), 3)
                p2 = self.priority_map.get(self.tier2_prio_var.get(), 4)
                p3 = self.priority_map.get(self.tier3_prio_var.get(), 5)
                tiers = [
                    {"gb": t1, "priority": p1, "message": f"Storage Warning: Only {{free_gb:.1f}} GB remaining on {drive}", "tag": "warning", "level": "warning", "channel_id": None},
                    {"gb": t2, "priority": p2, "message": f"Critical Warning: Only {{free_gb:.1f}} GB remaining on {drive}!", "tag": "rotating_light", "level": "critical", "channel_id": None},
                    {"gb": t3, "priority": p3, "message": f"FATAL: Only {{free_gb:.1f}} GB remaining on {drive}!", "tag": "skull,fire", "level": "critical", "channel_id": None}
                ]
                new_mon = StorageMultiTierMonitor(
                    name=name,
                    drive=drive,
                    tiers=tiers,
                    interval_seconds=interval,
                    channel_id=channel_id,
                    monitor_id=mon_id,
                    priority=prio,
                    tags=custom_tags or "floppy_disk",
                    title_template=custom_title,
                    click_url=custom_click,
                    markdown_enabled=markdown_enabled,
                    step_down_mode=self.step_down_var.get(),
                    recovery_notification=recovery_notif
                )

            elif selected_code == "ResourceMonitor":
                target = self.target_entry.get().strip()
                if not target: raise ValueError("Target process name is required.")
                thresh = float(self.r_thresh_entry.get().strip())
                msg = custom_msg or "Process '{target}' {metric} is {val:.1f} ({condition} {threshold})."
                new_mon = ResourceMonitor(
                    name=name,
                    target=target,
                    metric=self.metric_var.get(),
                    condition=self.cond_var.get(),
                    threshold=thresh,
                    message=msg,
                    interval_seconds=interval,
                    channel_id=channel_id,
                    monitor_id=mon_id,
                    priority=prio,
                    tags=custom_tags,
                    title_template=custom_title,
                    click_url=custom_click,
                    markdown_enabled=markdown_enabled,
                    recovery_notification=recovery_notif
                )

            elif selected_code == "DirectorySize":
                path = self.dir_path_entry.get().strip()
                if not path: raise ValueError("Directory path is required.")
                max_gb = float(self.dir_size_entry.get().strip())
                msg = custom_msg or "Directory '{path}' has exceeded {max_size_gb:.1f} GB (Current: {current_gb:.1f} GB)!"
                new_mon = DirectorySizeMonitor(
                    name=name,
                    path=path,
                    max_size_gb=max_gb,
                    message=msg,
                    interval_seconds=interval,
                    channel_id=channel_id,
                    monitor_id=mon_id,
                    priority=prio,
                    tags=custom_tags or "file_folder,warning",
                    title_template=custom_title,
                    click_url=custom_click,
                    markdown_enabled=markdown_enabled,
                    recovery_notification=recovery_notif
                )

            elif selected_code == "HTTPEndpoint":
                url = self.url_entry.get().strip()
                if not url: raise ValueError("URL is required.")
                sc = int(self.status_code_entry.get().strip())
                msg = custom_msg or "HTTP Check failed for {url}! Status: {status}, Error: {error}"
                new_mon = HTTPEndpointMonitor(
                    name=name,
                    url=url,
                    expected_status=sc,
                    message=msg,
                    interval_seconds=interval,
                    channel_id=channel_id,
                    monitor_id=mon_id,
                    priority=prio,
                    tags=custom_tags or "globe_with_meridians,warning",
                    title_template=custom_title,
                    click_url=custom_click,
                    markdown_enabled=markdown_enabled,
                    recovery_notification=recovery_notif
                )

            elif selected_code == "LocalPort":
                port = int(self.port_entry.get().strip())
                host = self.host_entry.get().strip() or "127.0.0.1"
                msg = custom_msg or "Port {port} on {host} is unreachable!"
                new_mon = LocalPortMonitor(
                    name=name,
                    port=port,
                    host=host,
                    message=msg,
                    interval_seconds=interval,
                    channel_id=channel_id,
                    monitor_id=mon_id,
                    priority=prio,
                    tags=custom_tags or "electric_plug,warning",
                    title_template=custom_title,
                    click_url=custom_click,
                    markdown_enabled=markdown_enabled,
                    recovery_notification=recovery_notif
                )

            if self.on_save:
                self.on_save(new_mon)
            self.destroy()

        except Exception as e:
            messagebox.showerror("Validation Error", str(e))

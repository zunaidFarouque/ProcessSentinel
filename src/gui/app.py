import os
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
import webbrowser
import customtkinter as ctk

from channels import ChannelRegistry, NotificationChannel
from config_manager import ConfigManager, CONFIG_FILE
from engine import MonitorEngine
from monitors import create_monitor_from_dict
from monitors.base import BaseMonitor
from gui.dialogs import ChannelDialog, MonitorDialog
from gui.tray import Win32SystemTray

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SentinelGUI:
    """Modern CustomTkinter Dashboard for ProcessSentinel 2.0."""
    def __init__(self, root: ctk.CTk, engine: MonitorEngine, channel_registry: ChannelRegistry, save_callback):
        self.root = root
        self.engine = engine
        self.channel_registry = channel_registry
        self.save_callback = save_callback
        self.settings = ConfigManager.get_settings()

        self.root.title("ProcessSentinel 2.0 - Lab Watchdog Engine")
        self.root.geometry("960x760")
        self.root.minsize(880, 680)

        # Wire engine callbacks to UI
        self.engine.on_monitor_updated = self._on_engine_monitor_updated
        self.engine.on_log_message = self._on_engine_log_message

        # System Tray initialization
        self.tray = Win32SystemTray(
            tooltip="ProcessSentinel 2.0 • IDLE",
            on_show=self._show_from_tray,
            on_toggle_engine=lambda: self.root.after(0, self._toggle_engine),
            on_check_all=lambda: self.root.after(0, self._check_all_now),
            on_quit=lambda: self.root.after(0, self._quit_app),
        )
        self.tray.start()

        # Intercept window close to minimize to tray if enabled
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

        self._build_main_ui()
        self._refresh_monitors_list()
        self._refresh_channels_list()

        # Auto-start engine if configured
        if self.settings.get("auto_start_engine", False):
            self.root.after(400, self._toggle_engine)

    def _build_main_ui(self):
        # Top Header Bar
        header = ctk.CTkFrame(self.root, height=70, corner_radius=0)
        header.pack(fill="x", side="top")

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=20, pady=10)
        ctk.CTkLabel(title_frame, text="PROCESS SENTINEL", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="v2.0 Modular Rule-Based Monitoring Engine", font=("Segoe UI", 11), text_color="gray60").pack(anchor="w")

        # Engine Status & Controls
        ctrl_frame = ctk.CTkFrame(header, fg_color="transparent")
        ctrl_frame.pack(side="right", padx=15, pady=10)

        self.engine_status_lbl = ctk.CTkLabel(ctrl_frame, text="● IDLE", font=("Segoe UI", 13, "bold"), text_color="gray60")
        self.engine_status_lbl.pack(side="left", padx=10)

        self.btn_toggle_engine = ctk.CTkButton(ctrl_frame, text="▶ START ENGINE", command=self._toggle_engine, width=130, fg_color="#1f6aa5")
        self.btn_toggle_engine.pack(side="left", padx=4)

        ctk.CTkButton(ctrl_frame, text="📥 Import", command=self._import_config, width=80, fg_color="#495057", hover_color="#5a6268").pack(side="left", padx=3)
        ctk.CTkButton(ctrl_frame, text="📤 Export", command=self._export_config, width=80, fg_color="#364fc7", hover_color="#4263eb").pack(side="left", padx=3)
        ctk.CTkButton(ctrl_frame, text="💾 Save", command=self._save_config, width=75, fg_color="#2b8a3e", hover_color="#2f9e44").pack(side="left", padx=3)
        ctk.CTkButton(ctrl_frame, text="⚙ Settings", command=self._open_settings_dialog, width=85, fg_color="#495057", hover_color="#5a6268").pack(side="left", padx=3)
        ctk.CTkButton(ctrl_frame, text="❓ Help", command=self._open_help, width=75, fg_color="#099268", hover_color="#0ca678").pack(side="left", padx=3)

        # Main Tabview
        self.tabview = ctk.CTkTabview(self.root, corner_radius=8)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=15)

        self.tab_monitors = self.tabview.add("Active Monitors")
        self.tab_channels = self.tabview.add("Notification Channels")
        self.tab_logs = self.tabview.add("Live Activity Log")

        self._build_monitors_tab()
        self._build_channels_tab()
        self._build_logs_tab()

    # -------------------------------------------------------------
    # TAB 1: MONITORS
    # -------------------------------------------------------------
    def _build_monitors_tab(self):
        top_bar = ctk.CTkFrame(self.tab_monitors, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=(5, 10))

        self.mon_count_lbl = ctk.CTkLabel(top_bar, text="Monitors: 0", font=("Segoe UI", 13, "bold"))
        self.mon_count_lbl.pack(side="left")

        self.search_entry = ctk.CTkEntry(top_bar, placeholder_text="🔍 Filter monitors by name, tag, or type...", width=270)
        self.search_entry.pack(side="left", padx=(15, 0))
        self.search_entry.bind("<KeyRelease>", lambda e: self._refresh_monitors_list())

        ctk.CTkButton(top_bar, text="+ Add New Monitor", command=self._open_add_monitor_dialog, width=150, fg_color="#1f6aa5").pack(side="right", padx=5)
        ctk.CTkButton(top_bar, text="⚡ Check All Now", command=self._check_all_now, width=120, fg_color="gray40").pack(side="right", padx=5)

        self.monitors_scroll = ctk.CTkScrollableFrame(self.tab_monitors)
        self.monitors_scroll.pack(fill="both", expand=True, padx=10, pady=5)

    def _refresh_monitors_list(self):
        for w in self.monitors_scroll.winfo_children():
            w.destroy()

        search_query = self.search_entry.get().strip().lower() if hasattr(self, "search_entry") else ""

        matching_monitors = []
        for mon in self.engine.monitors:
            if search_query:
                in_name = search_query in mon.name.lower()
                in_tags = search_query in (mon.tags or "").lower()
                in_type = search_query in mon.display_name.lower()
                if not (in_name or in_tags or in_type):
                    continue
            matching_monitors.append(mon)

        count_text = f"Active Monitors ({len(self.engine.monitors)} configured)"
        if search_query:
            count_text += f" • {len(matching_monitors)} matching"
        self.mon_count_lbl.configure(text=count_text)

        if not matching_monitors:
            msg = f"No monitors match '{search_query}'." if search_query else "No monitors configured yet. Click '+ Add New Monitor' above."
            empty_lbl = ctk.CTkLabel(self.monitors_scroll, text=msg, text_color="gray60")
            empty_lbl.pack(pady=40)
        else:
            for mon in matching_monitors:
                self._create_monitor_card(mon)

        if hasattr(self, "tray"):
            self.tray.update_status(self.engine.is_running(), len(self.engine.monitors))

    def _create_monitor_card(self, mon: BaseMonitor):
        card = ctk.CTkFrame(self.monitors_scroll, corner_radius=8, fg_color="#242424")
        card.pack(fill="x", padx=5, pady=6)

        # Header Row
        h_row = ctk.CTkFrame(card, fg_color="transparent")
        h_row.pack(fill="x", padx=12, pady=(10, 4))

        badge = ctk.CTkLabel(h_row, text=f" {mon.display_name} ", fg_color="#184e77", corner_radius=5, font=("Segoe UI", 10, "bold"))
        badge.pack(side="left")

        if mon.monitor_type == "StorageMultiTier":
            prio_badge = ctk.CTkLabel(h_row, text=" MULTI-TIER ", fg_color="#6f42c1", corner_radius=5, font=("Segoe UI", 9, "bold"))
            prio_badge.pack(side="left", padx=5)
        else:
            prio_color = "#d90429" if mon.priority == 5 else "#f77f00" if mon.priority == 4 else "#1f6aa5" if mon.priority == 3 else "#495057"
            prio_name = "URGENT (5)" if mon.priority == 5 else "HIGH (4)" if mon.priority == 4 else "NORMAL (3)" if mon.priority == 3 else "LOW (2)"
            prio_badge = ctk.CTkLabel(h_row, text=f" {prio_name} ", fg_color=prio_color, corner_radius=5, font=("Segoe UI", 9, "bold"))
            prio_badge.pack(side="left", padx=5)

        name_lbl = ctk.CTkLabel(h_row, text=f"  {mon.name}", font=("Segoe UI", 14, "bold"))
        name_lbl.pack(side="left")

        switch_var = ctk.BooleanVar(value=mon.enabled)
        def on_toggle():
            mon.enabled = switch_var.get()
            self.engine.log(f"Monitor '{mon.name}' {'enabled' if mon.enabled else 'disabled'}.")
        sw = ctk.CTkSwitch(h_row, text="Enabled", variable=switch_var, command=on_toggle, width=80)
        sw.pack(side="right")

        # Metadata Row
        m_row = ctk.CTkFrame(card, fg_color="transparent")
        m_row.pack(fill="x", padx=12, pady=2)

        ctk.CTkLabel(m_row, text=f"⏱ {mon.interval_seconds}s interval", font=("Segoe UI", 11), text_color="gray60").pack(side="left", padx=(0, 15))

        target_chan = self.channel_registry.get_channel(mon.channel_id)
        is_default = (mon.channel_id is None or mon.channel_id == self.channel_registry.default_channel_id)
        chan_text = f"📡 {target_chan.name}" + (" [Default]" if is_default else "")
        ctk.CTkLabel(m_row, text=chan_text, font=("Segoe UI", 11), text_color="gray60").pack(side="left", padx=(0, 15))

        if mon.tags:
            ctk.CTkLabel(m_row, text=f"🏷 {mon.tags}", font=("Segoe UI", 11), text_color="gray60").pack(side="left")

        # Status Row
        s_row = ctk.CTkFrame(card, fg_color="transparent")
        s_row.pack(fill="x", padx=12, pady=(4, 8))

        status_color = "#38b000" if mon.status_level == "ok" else "#f77f00" if mon.status_level == "warning" else "#d90429" if mon.status_level == "critical" else "gray60"
        status_symbol = "●"
        status_lbl = ctk.CTkLabel(s_row, text=f"{status_symbol} {mon.status_text}", font=("Segoe UI", 12, "bold"), text_color=status_color)
        status_lbl.pack(side="left")

        # Actions Row
        act_row = ctk.CTkFrame(card, fg_color="transparent")
        act_row.pack(fill="x", padx=12, pady=(0, 10))

        btn_reset = ctk.CTkButton(act_row, text="↺ Reset State", width=100, height=26, fg_color="#3d3d3d", hover_color="#505050")
        def on_reset(button=btn_reset):
            self.engine.reset_monitor(mon.id)
            button.configure(text="Reset!", fg_color="#2b8a3e")
            self.root.after(800, lambda: button.configure(text="↺ Reset State", fg_color="#3d3d3d"))
            self._refresh_monitors_list()
        btn_reset.configure(command=on_reset)
        btn_reset.pack(side="left", padx=(0, 6))

        btn_check = ctk.CTkButton(act_row, text="⚡ Check", width=75, height=26, fg_color="#3d3d3d", hover_color="#505050")
        def on_check(button=btn_check):
            button.configure(text="Checking...", state="disabled")
            self.engine.check_monitor_now(mon.id)
            self.root.after(1200, lambda: button.configure(text="⚡ Check", state="normal"))
        btn_check.configure(command=on_check)
        btn_check.pack(side="left", padx=4)

        def on_edit():
            self._open_edit_monitor_dialog(mon)
        btn_edit = ctk.CTkButton(act_row, text="✏ Edit", width=70, height=26, fg_color="#3d3d3d", hover_color="#505050", command=on_edit)
        btn_edit.pack(side="left", padx=4)

        def on_clone():
            self._open_clone_monitor_dialog(mon)
        btn_clone = ctk.CTkButton(act_row, text="📋 Clone", width=70, height=26, fg_color="#3d3d3d", hover_color="#505050", command=on_clone)
        btn_clone.pack(side="left", padx=4)

        def on_del():
            if messagebox.askyesno("Confirm Delete", f"Delete monitor '{mon.name}'?"):
                self.engine.remove_monitor(mon.id)
                self._refresh_monitors_list()
        btn_del = ctk.CTkButton(act_row, text="🗑 Delete", width=75, height=26, fg_color="#8b1e1e", hover_color="#ad2323", command=on_del)
        btn_del.pack(side="right")

    # -------------------------------------------------------------
    # TAB 2: CHANNELS
    # -------------------------------------------------------------
    def _build_channels_tab(self):
        top_bar = ctk.CTkFrame(self.tab_channels, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(top_bar, text="Notification Channels (Topic Aliases):", font=("Segoe UI", 13, "bold")).pack(side="left")
        ctk.CTkButton(top_bar, text="+ Add Channel", command=self._open_add_channel_dialog, width=130, fg_color="#1f6aa5").pack(side="right")

        self.channels_scroll = ctk.CTkScrollableFrame(self.tab_channels)
        self.channels_scroll.pack(fill="both", expand=True, padx=10, pady=5)

    def _refresh_channels_list(self):
        for w in self.channels_scroll.winfo_children():
            w.destroy()

        for ch in self.channel_registry.channels:
            card = ctk.CTkFrame(self.channels_scroll, corner_radius=8, fg_color="#242424")
            card.pack(fill="x", padx=5, pady=6)

            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", padx=15, pady=12, fill="x", expand=True)

            is_default = (ch.id == self.channel_registry.default_channel_id)
            type_labels = {
                "ntfy": "ntfy.sh",
                "telegram": "Telegram",
                "discord": "Discord",
                "slack": "Slack"
            }
            type_badge = f"[{type_labels.get(ch.channel_type, ch.channel_type.upper())}] "
            title_text = type_badge + ch.name + ("  [PRIMARY DEFAULT]" if is_default else "")
            if ch.auth_token and ch.channel_type == "ntfy":
                title_text += "  [🔒 Token Protected]"
            title_color = "#38b000" if is_default else "white"
            ctk.CTkLabel(info_frame, text=title_text, font=("Segoe UI", 13, "bold"), text_color=title_color).pack(anchor="w")

            if ch.channel_type == "telegram":
                subtitle = f"Chat ID: {ch.chat_id or 'Not configured'}"
                if ch.url and "api.telegram.org" not in ch.url:
                    subtitle += f" ({ch.url})"
            else:
                subtitle = ch.url or "No URL configured"
            ctk.CTkLabel(info_frame, text=subtitle, font=("Segoe UI", 11), text_color="gray60").pack(anchor="w")

            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.pack(side="right", padx=15, pady=12)

            if not is_default:
                def make_def(cid=ch.id):
                    self.channel_registry.set_default(cid)
                    self._refresh_channels_list()
                    self._refresh_monitors_list()
                ctk.CTkButton(btn_frame, text="Set Default", width=95, height=28, fg_color="#3d3d3d", command=make_def).pack(side="left", padx=4)

            btn_test = ctk.CTkButton(btn_frame, text="⚡ Test Alert", width=95, height=28, fg_color="#1f6aa5")
            def on_test_click(channel=ch, button=btn_test):
                button.configure(text="Sending...", state="disabled", fg_color="#d97706")
                def worker():
                    ok = channel.send("Test notification from ProcessSentinel 2.0!", "Channel Test", "white_check_mark", 3)
                    def on_finish():
                        button.configure(text="⚡ Test Alert", state="normal", fg_color="#1f6aa5")
                        if ok:
                            messagebox.showinfo("Success", f"Test notification delivered to '{channel.name}' ({channel.channel_type})!")
                        else:
                            messagebox.showerror("Error", f"Failed sending to '{channel.name}'.\nCheck channel credentials or network connection.")
                    self.root.after(0, on_finish)
                threading.Thread(target=worker, daemon=True).start()

            btn_test.configure(command=on_test_click)
            btn_test.pack(side="left", padx=4)

            def edit_ch(channel=ch):
                self._open_edit_channel_dialog(channel)
            ctk.CTkButton(btn_frame, text="✏ Edit", width=65, height=28, fg_color="#3d3d3d", command=edit_ch).pack(side="left", padx=4)

            if len(self.channel_registry.channels) > 1:
                def del_ch(cid=ch.id, cname=ch.name):
                    if messagebox.askyesno("Confirm Delete", f"Delete channel '{cname}'?"):
                        self.channel_registry.remove_channel(cid)
                        self._refresh_channels_list()
                        self._refresh_monitors_list()
                ctk.CTkButton(btn_frame, text="🗑 Delete", width=65, height=28, fg_color="#8b1e1e", hover_color="#ad2323", command=del_ch).pack(side="left", padx=4)

    # -------------------------------------------------------------
    # TAB 3: LOGS
    # -------------------------------------------------------------
    def _build_logs_tab(self):
        top_bar = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(top_bar, text="Live Monitoring Event Stream:", font=("Segoe UI", 13, "bold")).pack(side="left")
        ctk.CTkButton(top_bar, text="Clear Log", command=self._clear_logs, width=90, fg_color="gray40").pack(side="right")

        self.log_textbox = ctk.CTkTextbox(self.tab_logs, font=("Consolas", 11), wrap="none")
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=5)

    def _clear_logs(self):
        self.log_textbox.delete("1.0", tk.END)

    # -------------------------------------------------------------
    # CONTROLS & DIALOGS
    # -------------------------------------------------------------
    def _toggle_engine(self):
        if self.engine.is_running():
            self.engine.stop()
            self.engine_status_lbl.configure(text="● STOPPED", text_color="gray60")
            self.btn_toggle_engine.configure(text="▶ START ENGINE", fg_color="#1f6aa5")
        else:
            self.engine.start()
            self.engine_status_lbl.configure(text="● RUNNING", text_color="#38b000")
            self.btn_toggle_engine.configure(text="⏹ STOP ENGINE", fg_color="#d90429")
        if hasattr(self, "tray"):
            self.tray.update_status(self.engine.is_running(), len(self.engine.monitors))

    def _check_all_now(self):
        for m in self.engine.monitors:
            self.engine.check_monitor_now(m.id)

    def _save_config(self):
        ok = self.save_callback()
        if ok:
            messagebox.showinfo("Config Saved", "Configuration successfully saved to config.json!")
        else:
            messagebox.showerror("Save Error", "Failed to write config.json.")

    def _export_config(self):
        filepath = filedialog.asksaveasfilename(
            title="Export Configuration",
            defaultextension=".json",
            filetypes=[("JSON Configuration Files", "*.json"), ("All Files", "*.*")],
            initialfile="process_sentinel_backup.json"
        )
        if not filepath:
            return
        ok = ConfigManager.save_config(self.channel_registry, self.engine.monitors, filepath=filepath)
        if ok:
            messagebox.showinfo("Export Successful", f"Configuration exported to:\n{filepath}")
            self.engine.log(f"Exported configuration to {filepath}")
        else:
            messagebox.showerror("Export Failed", "Could not write configuration to destination file.")

    def _import_config(self):
        filepath = filedialog.askopenfilename(
            title="Import Configuration",
            filetypes=[("JSON Configuration Files", "*.json"), ("All Files", "*.*")]
        )
        if not filepath:
            return

        if not messagebox.askyesno("Confirm Import", "Importing will replace currently loaded channels and monitors with the imported file.\n\nDo you want to continue?"):
            return

        try:
            new_registry, new_monitors = ConfigManager.load_config(filepath=filepath)
            self.channel_registry = new_registry
            self.engine.channel_registry = new_registry
            with self.engine._lock:
                self.engine.monitors = new_monitors

            # Auto-save to active default config.json
            self.save_callback()

            self._refresh_channels_list()
            self._refresh_monitors_list()
            self.engine.log(f"Imported configuration from {filepath}")
            messagebox.showinfo("Import Successful", f"Imported {len(new_monitors)} monitor(s) and {len(new_registry.channels)} channel(s) successfully!")
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed importing configuration:\n{e}")

    def _open_help(self):
        """Open the ProcessSentinel documentation in the default web browser."""
        url = "https://github.com/zunaidFarouque/ProcessSentinel/blob/main/docs/index.md"
        try:
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror("Help Error", f"Unable to open help in browser:\n{e}")

    def _open_add_monitor_dialog(self):
        def on_save(new_mon):
            self.engine.add_monitor(new_mon)
            self._refresh_monitors_list()
        MonitorDialog(self.root, self.channel_registry, monitor=None, on_save=on_save)

    def _open_edit_monitor_dialog(self, mon: BaseMonitor):
        def on_save(updated_mon):
            for i, m in enumerate(self.engine.monitors):
                if m.id == updated_mon.id:
                    self.engine.monitors[i] = updated_mon
                    break
            self._refresh_monitors_list()
        MonitorDialog(self.root, self.channel_registry, monitor=mon, on_save=on_save)

    def _open_add_channel_dialog(self):
        def on_save(name, url, token, channel_type="ntfy", chat_id=None, _=None):
            self.channel_registry.add_channel(name, url, auth_token=token, channel_type=channel_type, chat_id=chat_id)
            self._refresh_channels_list()
            self._refresh_monitors_list()
        ChannelDialog(self.root, channel=None, on_save=on_save)

    def _open_edit_channel_dialog(self, channel: NotificationChannel):
        def on_save(name, url, token, channel_type="ntfy", chat_id=None, cid=None):
            channel.name = name
            channel.url = url
            channel.auth_token = token
            channel.channel_type = channel_type
            channel.chat_id = chat_id
            self._refresh_channels_list()
            self._refresh_monitors_list()
        ChannelDialog(self.root, channel=channel, on_save=on_save)

    def _open_clone_monitor_dialog(self, mon: BaseMonitor):
        data = mon.to_dict()
        data["id"] = None
        data["name"] = f"{mon.name} (Copy)"
        cloned = create_monitor_from_dict(data)

        def on_save(new_mon):
            self.engine.add_monitor(new_mon)
            self._refresh_monitors_list()

        MonitorDialog(self.root, self.channel_registry, monitor=cloned, on_save=on_save)

    def _open_settings_dialog(self):
        dlg = ctk.CTkToplevel(self.root)
        dlg.title("Application Settings")
        dlg.geometry("450x260")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="General Watchdog Settings", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=20, pady=(15, 10))

        min_tray_var = ctk.BooleanVar(value=self.settings.get("minimize_to_tray", True))
        ctk.CTkCheckBox(dlg, text="Minimize to Windows System Tray on close", variable=min_tray_var, font=("Segoe UI", 12)).pack(anchor="w", padx=20, pady=8)

        auto_start_var = ctk.BooleanVar(value=self.settings.get("auto_start_engine", False))
        ctk.CTkCheckBox(dlg, text="Automatically start monitoring engine on launch", variable=auto_start_var, font=("Segoe UI", 12)).pack(anchor="w", padx=20, pady=8)

        btn_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(25, 10))

        def save_settings():
            self.settings["minimize_to_tray"] = min_tray_var.get()
            self.settings["auto_start_engine"] = auto_start_var.get()
            ConfigManager.set_settings(self.settings)
            self.save_callback()
            dlg.destroy()
            messagebox.showinfo("Settings Saved", "Settings saved successfully!")

        ctk.CTkButton(btn_frame, text="Save Settings", command=save_settings, width=120, fg_color="#1f6aa5").pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=dlg.destroy, width=80, fg_color="gray").pack(side="right", padx=5)

    def _on_window_close(self):
        if self.settings.get("minimize_to_tray", True):
            self.root.withdraw()
            self.engine.log("Dashboard minimized to system tray. Use tray icon to restore.", level="info")
        else:
            self._quit_app()

    def _show_from_tray(self):
        self.root.after(0, self._do_show_from_tray)

    def _do_show_from_tray(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _quit_app(self):
        if hasattr(self, "tray"):
            self.tray.stop()
        self.engine.stop()
        self.save_callback()
        self.root.destroy()

    def _on_engine_monitor_updated(self, monitor: BaseMonitor):
        self.root.after(0, self._refresh_monitors_list)

    def _on_engine_log_message(self, line: str):
        def append():
            self.log_textbox.insert(tk.END, line + "\n")
            self.log_textbox.see(tk.END)
        self.root.after(0, append)

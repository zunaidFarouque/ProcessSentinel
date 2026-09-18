import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from channels import ChannelRegistry, NotificationChannel
from engine import MonitorEngine
from monitors.base import BaseMonitor
from gui.dialogs import ChannelDialog, MonitorDialog

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SentinelGUI:
    """Modern CustomTkinter Dashboard for ProcessSentinel v2.0."""
    def __init__(self, root: ctk.CTk, engine: MonitorEngine, channel_registry: ChannelRegistry, save_callback):
        self.root = root
        self.engine = engine
        self.channel_registry = channel_registry
        self.save_callback = save_callback

        self.root.title("ProcessSentinel 2.0 - Lab Watchdog Engine")
        self.root.geometry("960x760")
        self.root.minsize(880, 680)

        # Wire engine callbacks to UI
        self.engine.on_monitor_updated = self._on_engine_monitor_updated
        self.engine.on_log_message = self._on_engine_log_message

        self._build_main_ui()
        self._refresh_monitors_list()
        self._refresh_channels_list()

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
        ctrl_frame.pack(side="right", padx=20, pady=10)

        self.engine_status_lbl = ctk.CTkLabel(ctrl_frame, text="● IDLE", font=("Segoe UI", 13, "bold"), text_color="gray60")
        self.engine_status_lbl.pack(side="left", padx=15)

        self.btn_toggle_engine = ctk.CTkButton(ctrl_frame, text="▶ START ENGINE", command=self._toggle_engine, width=140, fg_color="#1f6aa5")
        self.btn_toggle_engine.pack(side="left", padx=5)

        ctk.CTkButton(ctrl_frame, text="💾 Save Config", command=self._save_config, width=100, fg_color="#2b8a3e").pack(side="left", padx=5)

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

        ctk.CTkButton(top_bar, text="+ Add New Monitor", command=self._open_add_monitor_dialog, width=150, fg_color="#1f6aa5").pack(side="right", padx=5)
        ctk.CTkButton(top_bar, text="⚡ Check All Now", command=self._check_all_now, width=120, fg_color="gray40").pack(side="right", padx=5)

        self.monitors_scroll = ctk.CTkScrollableFrame(self.tab_monitors)
        self.monitors_scroll.pack(fill="both", expand=True, padx=10, pady=5)

    def _refresh_monitors_list(self):
        for w in self.monitors_scroll.winfo_children():
            w.destroy()

        self.mon_count_lbl.configure(text=f"Active Monitors ({len(self.engine.monitors)} configured)")

        if not self.engine.monitors:
            empty_lbl = ctk.CTkLabel(self.monitors_scroll, text="No monitors configured yet. Click '+ Add New Monitor' above.", text_color="gray60")
            empty_lbl.pack(pady=40)
            return

        for mon in self.engine.monitors:
            self._create_monitor_card(mon)

    def _create_monitor_card(self, mon: BaseMonitor):
        card = ctk.CTkFrame(self.monitors_scroll, corner_radius=8, fg_color="#242424")
        card.pack(fill="x", padx=5, pady=6)

        # Header Row
        h_row = ctk.CTkFrame(card, fg_color="transparent")
        h_row.pack(fill="x", padx=12, pady=(10, 4))

        badge = ctk.CTkLabel(h_row, text=f" {mon.display_name} ", fg_color="#184e77", corner_radius=5, font=("Segoe UI", 10, "bold"))
        badge.pack(side="left")

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
        ctk.CTkLabel(m_row, text=chan_text, font=("Segoe UI", 11), text_color="gray60").pack(side="left")

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

        def on_reset():
            self.engine.reset_monitor(mon.id)
            self._refresh_monitors_list()
        btn_reset = ctk.CTkButton(act_row, text="↺ Reset State", width=100, height=26, fg_color="#3d3d3d", hover_color="#505050", command=on_reset)
        btn_reset.pack(side="left", padx=(0, 6))

        def on_check():
            self.engine.check_monitor_now(mon.id)
        btn_check = ctk.CTkButton(act_row, text="⚡ Check", width=75, height=26, fg_color="#3d3d3d", hover_color="#505050", command=on_check)
        btn_check.pack(side="left", padx=4)

        def on_edit():
            self._open_edit_monitor_dialog(mon)
        btn_edit = ctk.CTkButton(act_row, text="✏ Edit", width=70, height=26, fg_color="#3d3d3d", hover_color="#505050", command=on_edit)
        btn_edit.pack(side="left", padx=4)

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
            title_text = ch.name + ("  [PRIMARY DEFAULT]" if is_default else "")
            title_color = "#38b000" if is_default else "white"
            ctk.CTkLabel(info_frame, text=title_text, font=("Segoe UI", 13, "bold"), text_color=title_color).pack(anchor="w")
            ctk.CTkLabel(info_frame, text=ch.url, font=("Segoe UI", 11), text_color="gray60").pack(anchor="w")

            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.pack(side="right", padx=15, pady=12)

            if not is_default:
                def make_def(cid=ch.id):
                    self.channel_registry.set_default(cid)
                    self._refresh_channels_list()
                    self._refresh_monitors_list()
                ctk.CTkButton(btn_frame, text="Set Default", width=95, height=28, fg_color="#3d3d3d", command=make_def).pack(side="left", padx=4)

            def test_ch(channel=ch):
                ok = channel.send("Test notification from ProcessSentinel 2.0!", "Channel Test", "white_check_mark", 3)
                if ok:
                    messagebox.showinfo("Success", f"Test notification delivered to '{channel.name}'!")
                else:
                    messagebox.showerror("Error", f"Failed sending to {channel.url}. Check URL or network.")
            ctk.CTkButton(btn_frame, text="⚡ Test Alert", width=95, height=28, fg_color="#1f6aa5", command=test_ch).pack(side="left", padx=4)

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

    def _check_all_now(self):
        for m in self.engine.monitors:
            self.engine.check_monitor_now(m.id)

    def _save_config(self):
        ok = self.save_callback()
        if ok:
            messagebox.showinfo("Config Saved", "Configuration successfully saved to config.json!")
        else:
            messagebox.showerror("Save Error", "Failed to write config.json.")

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
        def on_save(name, url, _):
            self.channel_registry.add_channel(name, url)
            self._refresh_channels_list()
            self._refresh_monitors_list()
        ChannelDialog(self.root, channel=None, on_save=on_save)

    def _open_edit_channel_dialog(self, channel: NotificationChannel):
        def on_save(name, url, cid):
            channel.name = name
            channel.url = url
            self._refresh_channels_list()
            self._refresh_monitors_list()
        ChannelDialog(self.root, channel=channel, on_save=on_save)

    def _on_engine_monitor_updated(self, monitor: BaseMonitor):
        self.root.after(0, self._refresh_monitors_list)

    def _on_engine_log_message(self, line: str):
        def append():
            self.log_textbox.insert(tk.END, line + "\n")
            self.log_textbox.see(tk.END)
        self.root.after(0, append)

import sys
import os

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
if os.path.exists(src_dir) and src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import customtkinter as ctk
from config_manager import ConfigManager, CONFIG_FILE
from engine import MonitorEngine
from gui import SentinelGUI

def main():
    channel_registry, monitors = ConfigManager.load_config(CONFIG_FILE)
    engine = MonitorEngine(channel_registry=channel_registry, monitors=monitors)

    root = ctk.CTk()

    def on_save():
        return ConfigManager.save_config(channel_registry, engine.monitors, CONFIG_FILE)

    def on_closing():
        engine.stop()
        ConfigManager.save_config(channel_registry, engine.monitors, CONFIG_FILE)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    app = SentinelGUI(
        root=root,
        engine=engine,
        channel_registry=channel_registry,
        save_callback=on_save
    )

    root.mainloop()

if __name__ == "__main__":
    main()

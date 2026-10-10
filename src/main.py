import os
import sys
import customtkinter as ctk

# Ensure src/ is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_manager import ConfigManager, CONFIG_FILE
from engine import MonitorEngine
from gui import SentinelGUI
from single_instance import SingleInstanceChecker

def main():
    # 0. Single-instance activation check
    single_checker = SingleInstanceChecker()
    if not single_checker.check_and_activate():
        # An existing instance is already running and was brought to the foreground
        sys.exit(0)

    try:
        # 1. Load configuration in an object-oriented manner (auto-migrating legacy if needed)
        channel_registry, monitors = ConfigManager.load_config(CONFIG_FILE)

        # 2. Initialize the master monitoring engine
        engine = MonitorEngine(channel_registry=channel_registry, monitors=monitors)

        # 3. Create CustomTkinter Root Window
        root = ctk.CTk()

        def on_save():
            return ConfigManager.save_config(channel_registry, engine.monitors, CONFIG_FILE)

        def on_closing():
            engine.stop()
            # Auto-save configuration on close
            ConfigManager.save_config(channel_registry, engine.monitors, CONFIG_FILE)
            single_checker.release()
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_closing)

        # 4. Initialize Modern Dashboard
        app = SentinelGUI(
            root=root,
            engine=engine,
            channel_registry=channel_registry,
            save_callback=on_save
        )

        # 5. Boot UI event loop
        root.mainloop()
    finally:
        single_checker.release()

if __name__ == "__main__":
    main()

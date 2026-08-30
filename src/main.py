import json
import os
import tkinter as tk

from notifier import Notifier
from monitor import MonitoringDaemon
from gui import SentinelGUI

CONFIG_FILE = "config.json"

def load_config():
    """Loads saved settings from config.json if it exists."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config file: {e}")
    # Return an empty dictionary if the file doesn't exist yet or is corrupted
    return {}

def save_config(data):
    """Saves current GUI settings to config.json."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving config file: {e}")

def main():
    # 1. Load any previous configuration to pre-fill the GUI
    default_config = load_config()
    
    # 2. Initialize the backend engine
    initial_url = default_config.get("ntfy_url", "")
    notifier = Notifier(topic_url=initial_url)
    daemon = MonitoringDaemon(notifier=notifier)
    
    # 3. Initialize the visual dashboard and pass the engine components to it
    root = tk.Tk()
    
    # Intercept the window close event to ensure the daemon shuts down safely
    def on_closing():
        daemon.stop()
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    app = SentinelGUI(
        root=root,
        daemon=daemon,
        notifier=notifier,
        default_config=default_config,
        save_callback=save_config
    )
    
    # 4. Boot the application
    root.mainloop()

if __name__ == "__main__":
    main()
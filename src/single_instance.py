import sys
import os

try:
    import win32event
    import win32api
    import win32gui
    import win32con
    import winerror
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

MUTEX_NAME = "Global\\ProcessSentinel_SingleInstance_Mutex_v2"
TRAY_HELPER_TITLE = "ProcessSentinelTrayHelper"
MAIN_WINDOW_TITLE_KEY = "ProcessSentinel 2.0"

class SingleInstanceChecker:
    """
    Ensures only a single instance of ProcessSentinel runs at a time.
    If an existing instance is already running (e.g. minimized to the system tray),
    this activator finds it, restores its window to the foreground, and signals
    the new instance to exit cleanly.
    """
    def __init__(self, mutex_name: str = MUTEX_NAME):
        self.mutex_name = mutex_name
        self.mutex = None
        self.is_single = True

    def check_and_activate(self) -> bool:
        """
        Returns True if this is the primary instance and should continue running.
        Returns False if another instance already exists (and was brought to front).
        """
        if not HAS_WIN32:
            return True

        try:
            self.mutex = win32event.CreateMutex(None, False, self.mutex_name)
            last_error = win32api.GetLastError()
            if last_error == winerror.ERROR_ALREADY_EXISTS:
                self.is_single = False
                self._activate_existing_instance()
                return False
        except Exception:
            # Fallback gracefully if permissions or terminal prevents mutex
            pass

        return True

    def _activate_existing_instance(self):
        """Signals the running instance to restore from system tray and brings its window to front."""
        try:
            # 1. First notify the tray helper window to deiconify the Tkinter root
            tray_hwnd = win32gui.FindWindow(None, TRAY_HELPER_TITLE)
            if tray_hwnd:
                win32gui.PostMessage(tray_hwnd, win32con.WM_USER + 20, 0, win32con.WM_LBUTTONDBLCLK)

            # 2. Also look for the main window to ensure it is restored and brought to foreground
            target_hwnd = None
            def enum_cb(hwnd, _):
                nonlocal target_hwnd
                if win32gui.IsWindow(hwnd):
                    text = win32gui.GetWindowText(hwnd)
                    if MAIN_WINDOW_TITLE_KEY in text:
                        target_hwnd = hwnd
            win32gui.EnumWindows(enum_cb, None)

            if target_hwnd:
                win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                win32gui.ShowWindow(target_hwnd, win32con.SW_SHOW)
                win32gui.SetForegroundWindow(target_hwnd)
        except Exception:
            pass

    def release(self):
        """Releases the mutex handle on app shutdown."""
        if self.mutex and HAS_WIN32:
            try:
                win32api.CloseHandle(self.mutex)
            except Exception:
                pass
            self.mutex = None

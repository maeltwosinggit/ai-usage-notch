"""
Codenotch Local for Antigravity - Main Entry Point.

Starts the floating notch UI and manages the background polling thread.
Zero 3rd-party dependencies. Runs on pure Python 3.11 standard library.
"""

import sys
import time
import threading
import tkinter as tk
from typing import Optional

from provider_antigravity import AntigravityProvider
from notch_ui import CodenotchWindow


class CodenotchApp:
    def __init__(self):
        self.root = tk.Tk()
        self.provider = AntigravityProvider()
        self.notch = CodenotchWindow(
            self.root,
            on_refresh_requested=self.trigger_immediate_refresh,
        )

        self._refresh_event = threading.Event()
        self._running = True
        self._poll_interval = 60  # seconds

        # Start background polling thread
        self._worker_thread = threading.Thread(target=self._background_poll_loop, daemon=True)
        self._worker_thread.start()

        # Handle window close cleanup
        self.root.protocol("WM_DELETE_WINDOW", self.stop)

    def trigger_immediate_refresh(self):
        """Signals the background thread to immediately fetch latest quotas."""
        self._refresh_event.set()

    def _background_poll_loop(self):
        """Worker thread that periodically queries Antigravity loopback RPC."""
        while self._running:
            try:
                data = self.provider.fetch_quotas()
                # Schedule update safely on the Tkinter GUI thread
                self.root.after(0, self.notch.update_data, data)
            except Exception as e:
                err_data = {
                    "status": "stale",
                    "message": f"Fetch error: {e}",
                    "groups": [],
                }
                self.root.after(0, self.notch.update_data, err_data)

            # Wait for either interval timeout or an explicit refresh trigger
            self._refresh_event.wait(timeout=self._poll_interval)
            self._refresh_event.clear()

    def stop(self):
        """Cleans up and exits the application."""
        self._running = False
        self._refresh_event.set()
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    def run(self):
        """Starts the Tkinter event loop."""
        self.root.mainloop()


if __name__ == "__main__":
    app = CodenotchApp()
    app.run()

import json
import time
import threading
import requests
from typing import Optional, Dict, Any, Union

class RemoteCommandListener:
    """
    Listens for remote action commands from a subscribed topic or webhook endpoint.
    Executes trigger actions or manual resets on monitors with authorization verification.
    """
    def __init__(
        self,
        engine: Any,
        topic_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        poll_interval: float = 2.0
    ):
        self.engine = engine
        self.topic_url = topic_url.strip() if topic_url else None
        self.auth_token = auth_token.strip() if auth_token else None
        self.poll_interval = poll_interval
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._last_event_id: Optional[str] = None

    def start(self):
        """Starts the background listening loop."""
        if not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()
            if hasattr(self.engine, "log"):
                self.engine.log(f"Remote command listener started on topic: {self.topic_url or '[Manual Dispatch]'}")

    def stop(self):
        """Stops the background listening loop."""
        self.running = False
        if hasattr(self.engine, "log"):
            self.engine.log("Remote command listener stopped.")

    def handle_command(self, payload: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parses, authenticates, and executes a remote command payload.
        
        Example payloads:
          {"action": "reset", "monitor_id": "mon-123", "token": "secret_key"}
          {"action": "run_action", "monitor_id": "mon-123", "token": "secret_key"}
          {"action": "check_now", "monitor_id": "mon-123", "token": "secret_key"}
        """
        # 1. Parse JSON if string
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except Exception as e:
                if hasattr(self.engine, "log"):
                    self.engine.log(f"Remote command rejected: invalid JSON payload ({e})", level="warning")
                return {"success": False, "error": f"Invalid JSON: {e}"}
        elif isinstance(payload, dict):
            data = payload
        else:
            return {"success": False, "error": "Payload must be a JSON string or dict"}

        # 2. Authorization validation
        if self.auth_token:
            incoming_token = data.get("token") or data.get("auth_token") or data.get("secret")
            if incoming_token != self.auth_token:
                if hasattr(self.engine, "log"):
                    self.engine.log("Unauthorized remote command rejected (token mismatch)", level="warning")
                return {"success": False, "error": "Unauthorized"}

        # 3. Command Dispatch
        action = data.get("action")
        monitor_id = data.get("monitor_id")

        if not action:
            return {"success": False, "error": "Missing 'action' in command payload"}

        if action == "reset":
            if not monitor_id:
                return {"success": False, "error": "Missing 'monitor_id' for reset action"}
            if hasattr(self.engine, "reset_monitor"):
                self.engine.reset_monitor(monitor_id)
            if hasattr(self.engine, "log"):
                self.engine.log(f"Remote command reset monitor ID '{monitor_id}'")
            return {"success": True, "action": "reset", "monitor_id": monitor_id}

        elif action == "run_action":
            if not monitor_id:
                return {"success": False, "error": "Missing 'monitor_id' for run_action"}
            monitor = self.engine.get_monitor(monitor_id) if hasattr(self.engine, "get_monitor") else None
            if not monitor:
                return {"success": False, "error": f"Monitor '{monitor_id}' not found"}

            if hasattr(monitor, "execute_action"):
                res = monitor.execute_action()
                if hasattr(self.engine, "log"):
                    self.engine.log(f"Remote command executed trigger action for monitor '{monitor.name}'")
                return {"success": True, "action": "run_action", "monitor_id": monitor_id, "result": res}
            else:
                return {"success": False, "error": f"Monitor '{monitor_id}' does not support actions"}

        elif action == "check_now":
            if not monitor_id:
                return {"success": False, "error": "Missing 'monitor_id' for check_now"}
            if hasattr(self.engine, "check_monitor_now"):
                self.engine.check_monitor_now(monitor_id)
            if hasattr(self.engine, "log"):
                self.engine.log(f"Remote command requested check_now for monitor ID '{monitor_id}'")
            return {"success": True, "action": "check_now", "monitor_id": monitor_id}

        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    def _listen_loop(self):
        """Polls or streams commands from self.topic_url while running."""
        while self.running:
            if not self.topic_url:
                time.sleep(self.poll_interval)
                continue

            try:
                # Poll ntfy or remote JSON endpoint
                poll_url = f"{self.topic_url}/json?poll=1"
                if self._last_event_id:
                    poll_url += f"&since={self._last_event_id}"
                else:
                    poll_url += "&since=latest"

                headers = {}
                if self.auth_token:
                    headers["Authorization"] = f"Bearer {self.auth_token}"

                resp = requests.get(poll_url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    for line in resp.iter_lines():
                        if not line or not self.running:
                            continue
                        try:
                            event = json.loads(line.decode("utf-8"))
                            if event.get("event") == "message":
                                self._last_event_id = event.get("id")
                                msg_text = event.get("message", "")
                                self.handle_command(msg_text)
                        except Exception:
                            pass
            except requests.RequestException:
                pass
            except Exception as e:
                if hasattr(self.engine, "log"):
                    self.engine.log(f"Remote listener error: {e}", level="warning")

            time.sleep(self.poll_interval)

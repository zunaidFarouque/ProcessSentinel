import os
import re
from typing import Optional, List, Dict, Any
from monitors.base import BaseMonitor

class LogScannerMonitor(BaseMonitor):
    """
    Scans an active or rotating log file for specific error strings or regular expressions:
      - Remembers byte position between checks to scan only newly appended lines.
      - Automatically detects log rotation/truncation and scans from beginning if file shrinks.
      - Triggers an instant notification and optional self-healing command on pattern match.
    """
    monitor_type = "LogScanner"
    display_name = "Active Log File Scanner"

    def __init__(
        self,
        name: str,
        file_path: str,
        patterns: List[str],
        is_regex: bool = False,
        case_sensitive: bool = False,
        message: str = "Log pattern matched in '{file_path}': {line}",
        interval_seconds: int = 60,
        channel_id: Optional[str] = None,
        enabled: bool = True,
        monitor_id: Optional[str] = None,
        priority: int = 4,
        tags: str = "page_facing_up,warning",
        title_template: Optional[str] = None,
        click_url: Optional[str] = None,
        markdown_enabled: bool = True,
        recovery_notification: bool = False,
        recovery_message: Optional[str] = None,
        action_command: Optional[str] = None,
        action_timeout: int = 30
    ):
        super().__init__(
            name=name,
            interval_seconds=interval_seconds,
            channel_id=channel_id,
            enabled=enabled,
            monitor_id=monitor_id,
            priority=priority,
            tags=tags,
            title_template=title_template,
            click_url=click_url,
            markdown_enabled=markdown_enabled,
            recovery_notification=recovery_notification,
            recovery_message=recovery_message,
            action_command=action_command,
            action_timeout=action_timeout
        )
        self.file_path = os.path.abspath(file_path.strip()) if file_path else ""
        self.patterns = [p.strip() for p in patterns if p.strip()] if patterns else []
        self.is_regex = bool(is_regex)
        self.case_sensitive = bool(case_sensitive)
        self.message = message

        self.last_file_pos: int = 0
        self.last_file_size: int = 0
        self._initialized: bool = False
        self.alerted: bool = False

    def check(self, engine, channel_registry) -> None:
        if not self.file_path or not os.path.exists(self.file_path):
            self.status_text = f"Error: File not found ({self.file_path})"
            self.status_level = "warning"
            return

        try:
            current_size = os.path.getsize(self.file_path)
        except Exception as e:
            self.status_text = f"Error accessing file: {e}"
            self.status_level = "warning"
            return

        if not self._initialized:
            self._initialized = True
            self.last_file_pos = current_size
            self.last_file_size = current_size
            self.status_text = f"OK: Monitoring {os.path.basename(self.file_path)}"
            self.status_level = "ok"
            return

        # Check for log rotation or truncation
        if current_size < self.last_file_pos:
            # File rotated or truncated. If small (< 256KB), scan from start to catch immediate errors
            self.last_file_pos = 0

        if current_size == self.last_file_pos:
            self.status_text = f"OK: No new entries in {os.path.basename(self.file_path)}"
            self.status_level = "ok"
            return

        # Compile regexes if needed
        compiled_regexes = {}
        if self.is_regex:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            for pat in self.patterns:
                try:
                    compiled_regexes[pat] = re.compile(pat, flags)
                except re.error as e:
                    self.status_text = f"Error: Invalid regex '{pat}': {e}"
                    self.status_level = "warning"
                    return

        # Read new bytes/lines
        matched_lines = []
        matched_pattern = None

        try:
            with open(self.file_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self.last_file_pos)
                new_lines = f.readlines()
                self.last_file_pos = f.tell()
                self.last_file_size = current_size
        except Exception as e:
            self.status_text = f"Error reading file: {e}"
            self.status_level = "warning"
            return

        for line in new_lines:
            line_str = line.rstrip("\r\n")
            if not line_str:
                continue

            for pat in self.patterns:
                matched = False
                if self.is_regex:
                    if compiled_regexes[pat].search(line_str):
                        matched = True
                else:
                    if self.case_sensitive:
                        if pat in line_str:
                            matched = True
                    else:
                        if pat.lower() in line_str.lower():
                            matched = True

                if matched:
                    matched_lines.append(line_str)
                    if not matched_pattern:
                        matched_pattern = pat
                    break

        if matched_lines:
            first_line = matched_lines[0]
            msg = self.message.format(
                name=self.name,
                file_path=self.file_path,
                line=first_line,
                pattern=matched_pattern,
                count=len(matched_lines)
            )
            title = self.format_title(
                f"{self.name}: Log Match",
                file_path=self.file_path,
                line=first_line,
                pattern=matched_pattern,
                count=len(matched_lines)
            )
            if channel_registry:
                channel_registry.send_alert(
                    channel_id=self.channel_id,
                    message=msg,
                    title=title,
                    tags=self.tags or "page_facing_up,warning",
                    priority=self.priority,
                    click_url=self.click_url,
                    markdown=self.markdown_enabled
                )
            self.execute_trigger_action(engine)
            self.alerted = True
            self.status_text = f"Triggered: Matched '{matched_pattern}' in {os.path.basename(self.file_path)}"
            self.status_level = "warning"
        else:
            self.status_text = f"OK: No match in new lines ({os.path.basename(self.file_path)})"
            self.status_level = "ok"

    def reset_state(self) -> None:
        self.alerted = False
        try:
            if os.path.exists(self.file_path):
                self.last_file_pos = os.path.getsize(self.file_path)
                self.last_file_size = self.last_file_pos
        except Exception:
            pass
        self.status_text = "State Reset"
        self.status_level = "idle"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "file_path": self.file_path,
            "patterns": self.patterns,
            "is_regex": self.is_regex,
            "case_sensitive": self.case_sensitive,
            "message": self.message
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogScannerMonitor":
        return cls(
            name=data.get("name", "Log Scanner"),
            file_path=data.get("file_path", ""),
            patterns=data.get("patterns", []),
            is_regex=data.get("is_regex", False),
            case_sensitive=data.get("case_sensitive", False),
            message=data.get("message", "Log pattern matched in '{file_path}': {line}"),
            interval_seconds=data.get("interval_seconds", 60),
            channel_id=data.get("channel_id"),
            enabled=data.get("enabled", True),
            monitor_id=data.get("id"),
            priority=data.get("priority", 4),
            tags=data.get("tags", "page_facing_up,warning"),
            title_template=data.get("title_template"),
            click_url=data.get("click_url"),
            markdown_enabled=data.get("markdown_enabled", True),
            recovery_notification=data.get("recovery_notification", False),
            recovery_message=data.get("recovery_message"),
            action_command=data.get("action_command"),
            action_timeout=data.get("action_timeout", 30)
        )

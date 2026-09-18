import customtkinter as ctk
from typing import Optional, Callable

class CTkCollapsibleFrame(ctk.CTkFrame):
    """
    A modern CustomTkinter accordion frame that can be toggled open/closed.
    Used for progressive disclosure of advanced settings without cluttering the UI.
    """
    def __init__(
        self,
        parent,
        title: str = "Advanced Options",
        is_expanded: bool = False,
        on_toggle: Optional[Callable[[bool], None]] = None,
        **kwargs
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.title = title
        self.is_expanded = is_expanded
        self.on_toggle = on_toggle

        # Header Toggle Bar
        self.header_btn = ctk.CTkButton(
            self,
            text=self._get_header_text(),
            command=self.toggle,
            anchor="w",
            fg_color="#2b2b2b",
            hover_color="#3a3a3a",
            text_color="#e0e0e0",
            font=("Segoe UI", 12, "bold"),
            height=32,
            corner_radius=6
        )
        self.header_btn.pack(fill="x", pady=(8, 2))

        # Content Container
        self.content_frame = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=6)
        if self.is_expanded:
            self.content_frame.pack(fill="both", expand=True, padx=2, pady=(2, 6))

    def _get_header_text(self) -> str:
        arrow = "▼" if self.is_expanded else "▶"
        return f"  {arrow}  {self.title}"

    def toggle(self):
        self.is_expanded = not self.is_expanded
        self.header_btn.configure(text=self._get_header_text())

        if self.is_expanded:
            self.content_frame.pack(fill="both", expand=True, padx=2, pady=(2, 6))
        else:
            self.content_frame.pack_forget()

        if self.on_toggle:
            self.on_toggle(self.is_expanded)

    def set_expanded(self, expanded: bool):
        if self.is_expanded != expanded:
            self.toggle()

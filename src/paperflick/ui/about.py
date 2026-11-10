"""About dialog. Version text comes from ``paperflick.__version__``."""

from __future__ import annotations

import webbrowser

import customtkinter as ctk

from paperflick import __version__
from paperflick.ui.about_info import REPO_URL, about_lines
from paperflick.ui.branding import about_logo_image, apply_window_icon


class AboutWindow(ctk.CTkToplevel):
    """Product name, version, one-line description, and the GitHub link."""

    def __init__(self, master: ctk.CTk) -> None:
        super().__init__(master)
        self.title("关于")
        self.geometry("440x320")
        self.resizable(False, False)
        self.transient(master)
        apply_window_icon(self)
        name, version_line, tagline, url = about_lines(__version__)
        self._logo = about_logo_image()
        if self._logo is not None:
            ctk.CTkLabel(self, text="", image=self._logo).pack(anchor="w", padx=20, pady=(16, 8))
        else:
            ctk.CTkLabel(
                self, text=name, font=ctk.CTkFont(size=18, weight="bold"), anchor="w"
            ).pack(fill="x", padx=20, pady=(20, 6))
        ctk.CTkLabel(self, text=version_line, anchor="w").pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(self, text=tagline, anchor="w").pack(fill="x", padx=20, pady=2)
        self._link = ctk.CTkButton(
            self,
            text=url,
            fg_color="transparent",
            hover_color=("gray90", "gray20"),
            text_color=("#1a73e8", "#8ab4f8"),
            anchor="w",
            command=self.open_repository,
        )
        self._link.pack(fill="x", padx=20, pady=(8, 12))
        ctk.CTkButton(self, text="关闭", width=80, command=self.destroy).pack(pady=(4, 16))
        self.bind("<Escape>", self._close_from_key)
        self.lift()
        self.focus_force()

    def open_repository(self, _event: object | None = None) -> None:
        """Open the project repository in the system browser."""
        webbrowser.open(REPO_URL)

    def _close_from_key(self, _event: object | None = None) -> None:
        """Close the dialog from the keyboard."""
        self.destroy()

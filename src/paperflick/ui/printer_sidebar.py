"""Sidebar that lists installed printers and reports the user's choice."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from paperflick.core.printers import resolve_sidebar_printer, system_default_printer


class PrinterSidebar(ctk.CTkFrame):
    """Radio list of printer names; empty catalog shows a quiet placeholder."""

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkFrame,
        printers: list[str],
        selected: str | None,
        on_select: Callable[[str], None],
        *,
        default_printer: Callable[[], str | None] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(master, **kwargs)  # type: ignore[arg-type]
        self._on_select = on_select
        self._printers = list(printers)

        ctk.CTkLabel(self, text="打印机", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=8, pady=(8, 4)
        )

        probe = default_printer if default_printer is not None else system_default_printer
        matched = resolve_sidebar_printer(
            selected,
            self._printers,
            system_default=probe(),
        )
        self._printer_var = ctk.StringVar(value=matched or "")

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        if not self._printers:
            ctk.CTkLabel(scroll, text="未检测到打印机", text_color="gray").pack(
                anchor="w", padx=4, pady=4
            )
            return

        for name in self._printers:
            ctk.CTkRadioButton(
                scroll,
                text=name,
                variable=self._printer_var,
                value=name,
                command=self._emit_selection,
            ).pack(anchor="w", padx=4, pady=2)

    def _emit_selection(self) -> None:
        choice = self._printer_var.get().strip()
        if choice:
            self._on_select(choice)

    def apply_selection(self, name: str) -> None:
        """Set the radio to ``name`` when it is in the listed printers."""
        if name in self._printers:
            self._printer_var.set(name)

    def selected_name(self) -> str | None:
        """Return the radio selection, or None when nothing is matched in the list."""
        choice = self._printer_var.get().strip()
        return choice or None

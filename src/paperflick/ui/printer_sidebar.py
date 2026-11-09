"""Sidebar that lists installed printers and reports the user's choice."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import customtkinter as ctk

from paperflick.core.printers import resolve_sidebar_printer, system_default_printer

_DEFAULT_SUFFIX = "（默认）"
_HOVER_HIDE_MS = 80


def printer_display_label(name: str, *, is_system_default: bool) -> str:
    """Return the visible radio text.

    The system default keeps its real name and appends 「（默认）」.
    """
    if is_system_default:
        return f"{name}{_DEFAULT_SUFFIX}"
    return name


@dataclass(frozen=True, slots=True)
class SidebarEntry:
    """One installed printer as the sidebar shows it.

    ``real_name`` is what selection and settings persist.
    ``hover_text`` is that same name, without the display suffix.
    """

    real_name: str
    display_label: str
    hover_text: str


def sidebar_entries(
    printers: Sequence[str],
    system_default: str | None,
) -> tuple[SidebarEntry, ...]:
    """Pair each installed printer with its label and hover text."""
    entries: list[SidebarEntry] = []
    for name in printers:
        is_default = system_default is not None and name == system_default
        entries.append(
            SidebarEntry(
                real_name=name,
                display_label=printer_display_label(name, is_system_default=is_default),
                hover_text=name,
            )
        )
    return tuple(entries)


class _PrinterNameTooltip:
    """Small hover popup. The text is the real printer name."""

    def __init__(self, master: tk.Misc) -> None:
        self._master = master
        self._window: tk.Toplevel | None = None
        self._label: tk.Label | None = None
        self.text: str | None = None

    def show(self, text: str, *, x_root: int, y_root: int) -> None:
        """Show ``text`` near the pointer."""
        self.text = text
        if self._window is None or self._label is None:
            window = tk.Toplevel(self._master)
            window.overrideredirect(True)
            window.attributes("-topmost", True)
            label = tk.Label(
                window,
                text=text,
                justify="left",
                background="#fff8dc",
                foreground="#1a1a1a",
                relief="solid",
                borderwidth=1,
                padx=8,
                pady=4,
            )
            label.pack()
            self._window = window
            self._label = label
        else:
            self._label.configure(text=text)
        self._window.geometry(f"+{x_root + 14}+{y_root + 18}")

    def hide(self) -> None:
        """Remove the popup."""
        if self._window is not None:
            self._window.destroy()
            self._window = None
            self._label = None
        self.text = None


class PrinterSidebar(ctk.CTkFrame):
    """Radio list of printer names; empty catalog shows a quiet placeholder."""

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkFrame | tk.Misc,
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
        self._by_name: dict[str, SidebarEntry] = {}
        self._radios: dict[str, ctk.CTkRadioButton] = {}
        self._tooltip = _PrinterNameTooltip(self)
        self._hover_hide_job: str | None = None

        ctk.CTkLabel(self, text="打印机", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=8, pady=(8, 4)
        )

        probe = default_printer if default_printer is not None else system_default_printer
        system_default = probe()
        matched = resolve_sidebar_printer(
            selected,
            self._printers,
            system_default=system_default,
        )
        self._printer_var = ctk.StringVar(value=matched or "")

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        if not self._printers:
            ctk.CTkLabel(scroll, text="未检测到打印机", text_color="gray").pack(
                anchor="w", padx=4, pady=4
            )
            return

        entries = sidebar_entries(self._printers, system_default)
        self._by_name = {entry.real_name: entry for entry in entries}
        for entry in entries:
            radio = ctk.CTkRadioButton(
                scroll,
                text=entry.display_label,
                variable=self._printer_var,
                value=entry.real_name,
                command=self._emit_selection,
            )
            radio.pack(anchor="w", fill="x", padx=4, pady=2)
            self._radios[entry.real_name] = radio
            self._bind_hover(radio, entry.real_name)

    def _bind_hover(self, radio: ctk.CTkRadioButton, name: str) -> None:
        """Show the real printer name while the pointer is on this radio."""

        def _enter(event: tk.Event) -> None:
            self.show_hover(name, x_root=int(event.x_root), y_root=int(event.y_root))

        def _leave(_event: tk.Event) -> None:
            self._schedule_hover_hide()

        radio.bind("<Enter>", _enter)
        radio.bind("<Leave>", _leave)

    def _cancel_hover_hide(self) -> None:
        if self._hover_hide_job is None:
            return
        self.after_cancel(self._hover_hide_job)
        self._hover_hide_job = None

    def _schedule_hover_hide(self) -> None:
        """Hide after a short pause so moving across the radio does not flicker."""
        self._cancel_hover_hide()
        self._hover_hide_job = self.after(_HOVER_HIDE_MS, self.hide_hover)

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

    def radio_text(self, name: str) -> str | None:
        """Return the visible label for ``name``, or None when it is not listed."""
        radio = self._radios.get(name)
        if radio is None:
            return None
        return str(radio.cget("text"))

    def radio_value(self, name: str) -> str | None:
        """Return the persisted radio value for ``name``, or None when it is not listed."""
        radio = self._radios.get(name)
        if radio is None:
            return None
        return str(radio.cget("value"))

    def hover_text(self, name: str) -> str | None:
        """Return the full real printer name used as the hover tooltip."""
        entry = self._by_name.get(name)
        if entry is None:
            return None
        return entry.hover_text

    def hover_popup_text(self) -> str | None:
        """Return the visible tooltip text, or None when the popup is hidden."""
        return self._tooltip.text

    def show_hover(self, name: str, *, x_root: int = 0, y_root: int = 0) -> str | None:
        """Show the full printer name and return that name."""
        self._cancel_hover_hide()
        text = self.hover_text(name)
        if text is None:
            return None
        self._tooltip.show(text, x_root=x_root, y_root=y_root)
        return text

    def hide_hover(self) -> None:
        """Hide the printer name tooltip."""
        self._cancel_hover_hide()
        self._tooltip.hide()

    def destroy(self) -> None:
        """Hide the hover popup, then destroy the sidebar."""
        self.hide_hover()
        super().destroy()

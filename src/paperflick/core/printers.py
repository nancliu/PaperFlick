"""Installed printers: Windows enum at the boundary, plain names outward."""

from __future__ import annotations

from collections.abc import Sequence


def brand_printer_name(raw: object) -> str | None:
    """Parse an external or persisted value into a printer name, or None."""
    if not isinstance(raw, str):
        return None
    name = raw.strip()
    return name or None


def resolve_selected_printer(
    selected: str | None,
    installed: Sequence[str],
) -> str | None:
    """Return ``selected`` when it appears in ``installed``; otherwise None."""
    branded = brand_printer_name(selected)
    if branded is None:
        return None
    return branded if branded in installed else None


def selected_printer_for_persist(
    ui_choice: str | None,
    stored: str | None,
) -> str | None:
    """Prefer the sidebar choice; keep ``stored`` when the UI has no match (stale)."""
    if ui_choice is not None:
        return ui_choice
    return brand_printer_name(stored)


def list_installed_printers() -> list[str]:
    """Return local and network printer names from Windows, branded as plain str.

    Returns an empty list when pywin32 is missing or enumeration fails.
    """
    try:
        import win32print
    except ImportError:
        return []

    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    try:
        rows = win32print.EnumPrinters(flags, None, 1)
    except Exception:
        return []

    names: list[str] = []
    seen: set[str] = set()
    for row in rows:
        # EnumPrinters level 1: (flags, description, name, comment)
        name = brand_printer_name(row[2] if len(row) > 2 else None)
        if name is None or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names

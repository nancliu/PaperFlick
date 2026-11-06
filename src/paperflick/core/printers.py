"""Installed printers and spooler job counts."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass


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


_UNREADABLE = "无法读取打印队列"


@dataclass(frozen=True, slots=True)
class SpoolerCount:
    """How many jobs are queued for one printer.

    The number includes every job on that printer, including jobs other
    applications submitted.
    """

    jobs: int

    def __post_init__(self) -> None:
        if self.jobs < 0:
            raise ValueError("job count must be non-negative")


@dataclass(frozen=True, slots=True)
class ProbeFailed:
    """The spooler job count could not be read."""

    reason: str

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("ProbeFailed requires a reason")


def count_spooler_jobs(
    printer: str | None,
    *,
    read_jobs: Callable[[str], int] | None = None,
    default_printer: Callable[[], str] | None = None,
) -> SpoolerCount | ProbeFailed:
    """Return the job count for ``printer``. A blank name uses the default printer.

    A hook exception, a missing name, or a negative count becomes ``ProbeFailed``.
    This function does not raise.
    """
    reader = read_jobs if read_jobs is not None else _win32_read_jobs
    default = default_printer if default_printer is not None else _win32_default_printer
    try:
        name = brand_printer_name(printer)
        if name is None:
            name = brand_printer_name(default())
        if name is None:
            return ProbeFailed(_UNREADABLE)
        jobs = reader(name)
    except Exception:
        return ProbeFailed(_UNREADABLE)
    if isinstance(jobs, bool) or not isinstance(jobs, int) or jobs < 0:
        return ProbeFailed(_UNREADABLE)
    return SpoolerCount(jobs)


def _win32_default_printer() -> str:
    import win32print

    return str(win32print.GetDefaultPrinter())


def _win32_read_jobs(name: str) -> int:
    import win32print

    handle = win32print.OpenPrinter(name)
    try:
        info = win32print.GetPrinter(handle, 2)
        jobs = info["cJobs"]
    finally:
        win32print.ClosePrinter(handle)
    if isinstance(jobs, bool) or not isinstance(jobs, int):
        raise TypeError("cJobs is not an int")
    return jobs

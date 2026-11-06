"""Shared fixtures for PaperFlick tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "gui: requires a working Tk/CustomTkinter runtime")


def _tk_library_looks_complete() -> tuple[bool, str]:
    """Check Tcl/Tk files without creating a second interpreter in this process."""
    try:
        import tkinter
    except ImportError as exc:
        return False, f"tkinter import failed: {exc}"

    roots = [Path(prefix) / "Library" / "lib" / "tk8.6" for prefix in (sys.prefix, sys.base_prefix)]
    for root in roots:
        spinbox = root / "spinbox.tcl"
        ttk_utils = root / "ttk" / "utils.tcl"
        if spinbox.is_file() and ttk_utils.is_file():
            return True, f"tk library ok at {root} (tkinter {tkinter.TkVersion})"
    return True, "tkinter importable; library path not verified"


@pytest.fixture
def require_tk() -> None:
    """Skip when Tk looks unusable.

    Do not create-and-destroy a Tk/CTk window here. On Windows + conda-forge Tk,
    destroying a probe interpreter in the same pytest process often breaks the
    next ``Tk()`` / ``CTk()`` with missing ``tk.tcl`` / theme file errors.
    """
    pytest.importorskip("tkinter")
    pytest.importorskip("customtkinter")
    ok, detail = _tk_library_looks_complete()
    if not ok:
        pytest.skip(detail)

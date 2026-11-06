"""Shared fixtures for PaperFlick tests."""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "gui: requires a working Tk/CustomTkinter runtime")


@pytest.fixture
def require_tk() -> None:
    """Skip when Tcl/Tk or CustomTkinter cannot create a real window."""
    tkinter = pytest.importorskip("tkinter")
    try:
        root = tkinter.Tk()
        root.destroy()
    except tkinter.TclError as exc:
        pytest.skip(f"tk unavailable: {exc}")

    customtkinter = pytest.importorskip("customtkinter")
    try:
        window = customtkinter.CTk()
        window.update_idletasks()
        window.destroy()
    except Exception as exc:  # noqa: BLE001 - any CTk init failure means skip
        pytest.skip(f"customtkinter unavailable: {exc}")

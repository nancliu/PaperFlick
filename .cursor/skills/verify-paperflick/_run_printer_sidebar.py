"""Headless verify for the printer sidebar sash, hover name, and default suffix."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import paperflick.ui.main_window as main_window_module
import paperflick.ui.printer_sidebar as printer_sidebar_module
from paperflick.core.settings import load, settings_path
from paperflick.ui.main_window import MainWindow
from paperflick.ui.sidebar_split import (
    reset_sidebar_split_session,
    session_sidebar_preferred_px,
)

_LONG = "North Building Color LaserJet Enterprise That Does Not Fit"
_DEFAULT = "Front Desk"
_OTHER = "Back Office"


class _Pointer:
    """Minimal event for the sash handlers."""

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
        self.x_root = x
        self.y_root = y


def _install_fake_printers() -> None:
    """List two short names and one long name, with a known system default."""

    def _names() -> list[str]:
        return [_LONG, _DEFAULT, _OTHER]

    main_window_module.list_installed_printers = _names
    printer_sidebar_module.system_default_printer = lambda: _DEFAULT


def _sash_y(app: MainWindow, x: int) -> int:
    """Return a y on the sash, or raise when the handle cannot be identified."""
    for y in range(0, 40):
        identified = str(app._split.identify(x, y))
        if "sash" in identified:
            return y
    raise AssertionError(f"sash not identified at x={x}")


def _prove_labels(app: MainWindow, lines: list[str]) -> None:
    """Default printer shows the suffix; values and hover text stay the real name."""
    sidebar = app._printer_sidebar
    assert sidebar.radio_text(_DEFAULT) == f"{_DEFAULT}（默认）"
    assert sidebar.radio_value(_DEFAULT) == _DEFAULT
    assert sidebar.hover_text(_DEFAULT) == _DEFAULT
    assert sidebar.radio_text(_OTHER) == _OTHER
    assert sidebar.radio_value(_OTHER) == _OTHER
    assert sidebar.radio_text(_LONG) == _LONG
    assert sidebar.hover_text(_LONG) == _LONG
    assert sidebar.selected_name() == _DEFAULT
    lines.append("label=suffix-on-default hover=real-name value=real-name")


def _prove_hover(app: MainWindow, lines: list[str]) -> None:
    """The popup shows the full real name and not the display suffix."""
    sidebar = app._printer_sidebar
    assert sidebar.show_hover(_DEFAULT, x_root=40, y_root=40) == _DEFAULT
    assert sidebar.hover_popup_text() == _DEFAULT
    assert "（默认）" not in (sidebar.hover_popup_text() or "")
    sidebar.hide_hover()
    assert sidebar.hover_popup_text() is None
    shown = sidebar.show_hover(_LONG, x_root=48, y_root=64)
    assert shown == _LONG
    sidebar.hide_hover()
    lines.append("hover-popup=real-name")


def _prove_sash(app: MainWindow, lines: list[str]) -> None:
    """Default sash is about 280px; drag stays in 200px .. half the window."""
    sash = int(app._split.sash_coord(0)[0])
    assert abs(sash - app._physical_px(280)) <= 8, sash
    assert session_sidebar_preferred_px() is None
    y = _sash_y(app, sash)
    assert app._on_sidebar_sash_press(_Pointer(sash, y)) == "break"
    app._on_sidebar_sash_drag(_Pointer(1, y))
    app.update_idletasks()
    assert abs(int(app._split.sash_coord(0)[0]) - app._physical_px(200)) <= 8
    assert session_sidebar_preferred_px() is None
    app._on_sidebar_sash_release(_Pointer(int(app.winfo_width()), y))
    app.update_idletasks()
    half = app._layout_window_width() // 2
    assert session_sidebar_preferred_px() == half
    assert abs(int(app._split.sash_coord(0)[0]) - app._physical_px(half)) <= 8
    sidebar_width = int(app._printer_sidebar.winfo_width())
    assert abs(sidebar_width - app._physical_px(half)) <= 12, sidebar_width
    lines.append(
        f"sash default~280 drag-min=200 drag-max={half} "
        f"logical-window={app._layout_window_width()} scale={app._window_scaling()}"
    )


def _prove_persist(app: MainWindow, lines: list[str], artifact: Path) -> None:
    """Selecting a printer writes the real name and does not store the sash."""
    app._printer_sidebar._radios[_OTHER].invoke()
    assert load().selected_printer == _OTHER
    raw = json.loads(settings_path().read_text(encoding="utf-8"))
    assert set(raw) == {
        "interval_seconds",
        "wait_for_empty_queue",
        "dry_run",
        "selected_printer",
    }
    assert raw["selected_printer"] == _OTHER
    assert "（默认）" not in raw["selected_printer"]
    target = artifact / "settings.json"
    target.write_text(settings_path().read_text(encoding="utf-8"), encoding="utf-8")
    lines.append("persist=real-name sash-not-in-settings")


def main() -> None:
    """Open MainWindow, prove the sidebar, and leave a settings copy."""
    appdata = Path(tempfile.mkdtemp(prefix="paperflick-sidebar-"))
    os.environ["PAPERFLICK_APPDATA"] = str(appdata)
    artifact = Path(__file__).resolve().parent / "artifacts" / "issue-39-printer-sidebar"
    artifact.mkdir(parents=True, exist_ok=True)
    lines = ["headless MainWindow"]
    _install_fake_printers()
    reset_sidebar_split_session()
    app = MainWindow()
    try:
        app.update_idletasks()
        app.update()
        _prove_labels(app, lines)
        _prove_hover(app, lines)
        _prove_sash(app, lines)
        _prove_persist(app, lines, artifact)
        lines.append("PASS printer-sidebar")
        (artifact / "log.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("PASS printer-sidebar")
    finally:
        app.destroy()
        shutil.rmtree(appdata, ignore_errors=True)


if __name__ == "__main__":
    main()

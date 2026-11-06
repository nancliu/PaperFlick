"""GUI smoke tests.

One MainWindow per process. Windows+conda Tk is flaky after destroy+recreate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from paperflick.core.settings import Settings, load, save
from paperflick.ui.main_window import MainWindow


@pytest.mark.gui
def test_main_window_boot_printer_and_interval_persist(
    tmp_path: Path, monkeypatch, require_tk
) -> None:
    monkeypatch.setenv("PAPERFLICK_APPDATA", str(tmp_path))
    monkeypatch.setattr(
        "paperflick.ui.main_window.list_installed_printers",
        lambda: ["Mock Printer A", "Mock Printer B"],
    )
    save(Settings(interval_seconds=2.0, selected_printer="Mock Printer B"))

    app = MainWindow()
    app.update_idletasks()
    assert app.title() == "PaperFlick"
    assert app._settings.interval_seconds == 2.0
    assert app._printer_sidebar.selected_name() == "Mock Printer B"

    app._interval_var.set("7.5")
    app._on_interval_typed()
    assert load().interval_seconds == 7.5
    assert load().selected_printer == "Mock Printer B"

    app._on_printer_selected("Mock Printer A")
    assert load().selected_printer == "Mock Printer A"

    app.destroy()

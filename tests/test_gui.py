"""GUI smoke tests.

One MainWindow per process. Windows+conda Tk is flaky after destroy+recreate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from paperflick.core.settings import Settings, load, save
from paperflick.ui.main_window import MainWindow


@pytest.mark.gui
def test_main_window_boot_and_interval_persist(tmp_path: Path, monkeypatch, require_tk) -> None:
    monkeypatch.setenv("PAPERFLICK_APPDATA", str(tmp_path))
    save(Settings(interval_seconds=2.0))

    app = MainWindow()
    app.update_idletasks()
    assert app.title() == "PaperFlick"
    assert app._settings.interval_seconds == 2.0

    app._interval_var.set("7.5")
    app._on_interval_typed()
    assert load().interval_seconds == 7.5

    app.destroy()

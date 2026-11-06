"""Smoke: main window constructs with default Settings."""

from __future__ import annotations

from pathlib import Path

import pytest

from paperflick.core.settings import Settings, save
from paperflick.ui.main_window import MainWindow


@pytest.mark.gui
def test_main_window_boots(tmp_path: Path, monkeypatch, require_tk) -> None:
    monkeypatch.setenv("PAPERFLICK_APPDATA", str(tmp_path))
    save(Settings())
    app = MainWindow()
    app.update_idletasks()
    assert app.title() == "PaperFlick"
    assert app._settings == Settings()
    app.destroy()

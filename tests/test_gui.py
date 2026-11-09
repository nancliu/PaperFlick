"""GUI smoke tests.

One MainWindow per process. Windows+conda Tk is flaky after destroy+recreate.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import customtkinter as ctk
import pytest

from paperflick.core.batch import AddPaths, BatchPhase
from paperflick.core.settings import Settings, load, save, settings_path
from paperflick.core.submit import SubmitFailed, SubmitScript
from paperflick.ui.main_window import MainWindow
from paperflick.ui.sidebar_split import (
    reset_sidebar_split_session,
    session_sidebar_preferred_px,
)


def _wait_batch_finished(app: MainWindow) -> None:
    """Pump Tk until the Batch is idle and no row is waiting or printing."""
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        app.update()
        snap = app._session.snapshot()
        if snap.phase is BatchPhase.IDLE and snap.waiting_count == 0 and snap.printing_count == 0:
            return
        time.sleep(0.02)
    snap = app._session.snapshot()
    pytest.fail(
        f"batch still {snap.phase.value} "
        f"success={snap.success_count} failed={snap.failed_count} waiting={snap.waiting_count}"
    )


def _row_labels(app: MainWindow) -> list[str]:
    """Visible row labels."""
    labels: list[str] = []
    for row in app._item_list._scroll.winfo_children():
        for child in row.winfo_children():
            if not isinstance(child, ctk.CTkLabel):
                continue
            text = str(child.cget("text"))
            if text:
                labels.append(text)
    return labels


def _collect_button_texts(widget: object) -> list[str]:
    """Button captions under ``widget``, including row actions."""
    texts: list[str] = []
    if isinstance(widget, ctk.CTkButton):
        texts.append(str(widget.cget("text")))
    children = getattr(widget, "winfo_children", None)
    if children is None:
        return texts
    for child in children():
        texts.extend(_collect_button_texts(child))
    return texts


def _contains_checkbox(widget: object) -> bool:
    """True when ``widget`` or a descendant is a checkbox."""
    if isinstance(widget, ctk.CTkCheckBox):
        return True
    children = getattr(widget, "winfo_children", None)
    if children is None:
        return False
    return any(_contains_checkbox(child) for child in children())


def _row_remove_count(app: MainWindow) -> int:
    """How many inline 移除 buttons the list is showing."""
    count = 0
    for row in app._item_list._scroll.winfo_children():
        for child in row.winfo_children():
            if isinstance(child, ctk.CTkButton) and str(child.cget("text")) == "移除":
                count += 1
    return count


@pytest.mark.gui
def test_main_window_boot_printer_and_interval_persist(
    tmp_path: Path, monkeypatch, require_tk
) -> None:
    monkeypatch.setenv("PAPERFLICK_APPDATA", str(tmp_path))
    long_name = "Mock Printer With An Unreasonably Long Name For Clipping"
    monkeypatch.setattr(
        "paperflick.ui.main_window.list_installed_printers",
        lambda: [long_name, "Mock Printer A", "Mock Printer B"],
    )
    monkeypatch.setattr(
        "paperflick.ui.printer_sidebar.system_default_printer",
        lambda: "Mock Printer A",
    )
    reset_sidebar_split_session()
    save(Settings(interval_seconds=2.0, selected_printer="Mock Printer B"))

    app = MainWindow(submit_script=SubmitScript((SubmitFailed("卡纸"),)))
    app.update_idletasks()
    # CTk on Windows only settles geometry after the first update()/map.
    app.update()
    assert app.title() == "PaperFlick"
    width, height = (int(part) for part in app.geometry().split("+", 1)[0].split("x"))
    assert width >= 780
    assert height >= 640
    # CTk.minsize is setter-only; logical floors live on the scaling attrs.
    assert app._min_width >= 640
    assert app._min_height >= 500
    assert app._settings.interval_seconds == 2.0
    assert app._printer_sidebar.selected_name() == "Mock Printer B"
    assert session_sidebar_preferred_px() is None
    assert app._split.sash_coord(0)[0] == pytest.approx(app._physical_px(280), abs=8)
    assert app._printer_sidebar.radio_text("Mock Printer A") == "Mock Printer A（默认）"
    assert app._printer_sidebar.radio_value("Mock Printer A") == "Mock Printer A"
    assert app._printer_sidebar.hover_text("Mock Printer A") == "Mock Printer A"
    assert app._printer_sidebar.radio_text("Mock Printer B") == "Mock Printer B"
    assert app._printer_sidebar.radio_value(long_name) == long_name
    assert app._printer_sidebar.hover_text(long_name) == long_name
    assert app._printer_sidebar.show_hover(long_name, x_root=30, y_root=40) == long_name
    assert app._printer_sidebar.hover_popup_text() == long_name
    app._printer_sidebar.hide_hover()
    assert app._printer_sidebar.hover_popup_text() is None

    app._interval_var.set("7.5")
    app._on_interval_typed()
    assert load().interval_seconds == 7.5
    assert load().selected_printer == "Mock Printer B"

    app._on_printer_selected("Mock Printer A")
    assert load().selected_printer == "Mock Printer A"
    assert "（默认）" not in (load().selected_printer or "")

    logical_width = app._layout_window_width()
    assert app._apply_sidebar_sash(50, remember=True) == 200
    assert session_sidebar_preferred_px() == 200
    app.update_idletasks()
    assert app._split.sash_coord(0)[0] == pytest.approx(app._physical_px(200), abs=8)
    assert app._printer_sidebar.winfo_width() == pytest.approx(app._physical_px(200), abs=12)
    half = logical_width // 2
    assert app._apply_sidebar_sash(logical_width, remember=True) == half
    assert session_sidebar_preferred_px() == half
    app.update_idletasks()
    assert app._split.sash_coord(0)[0] == pytest.approx(app._physical_px(half), abs=8)
    app._sync_sidebar_sash()
    assert session_sidebar_preferred_px() == half
    raw = json.loads(settings_path().read_text(encoding="utf-8"))
    assert set(raw) == {
        "interval_seconds",
        "wait_for_empty_queue",
        "dry_run",
        "selected_printer",
    }
    assert raw["selected_printer"] == "Mock Printer A"
    app._apply_sidebar_sash(280, remember=True)

    bad = tmp_path / "bad.pdf"
    good = tmp_path / "good.pdf"
    bad.write_bytes(b"bad")
    good.write_bytes(b"good")
    app._dry_var.set(True)
    app._interval_var.set("0.05")
    app._persist()
    app._session.apply(AddPaths([bad, good]))
    app._on_start()
    _wait_batch_finished(app)
    snap = app._session.snapshot()
    assert snap.failed_count == 1
    assert snap.success_count == 1
    assert app._status_label.cget("text") == "本批完成：成功 1、失败 1"
    assert snap.items[0].failure_reason == "卡纸"
    assert any("卡纸" in text for text in _row_labels(app))
    button_texts = _collect_button_texts(app)
    assert "移除全部失败" in button_texts
    assert "移除所选" not in button_texts
    assert "预览" not in button_texts
    assert "只勾选失败项" not in button_texts
    assert _row_remove_count(app) == len(snap.items)
    assert not _contains_checkbox(app._item_list)

    app._on_clear_succeeded()
    cleared = app._session.snapshot()
    assert cleared.success_count == 0
    assert cleared.failed_count == 1
    assert [item.path.name for item in cleared.items] == ["bad.pdf"]

    app._on_reprint_failed()
    _wait_batch_finished(app)
    reprinted = app._session.snapshot()
    assert reprinted.failed_count == 0
    assert reprinted.success_count == 1
    assert app._status_label.cget("text") == "本批完成：成功 1、失败 0"
    assert reprinted.items[0].failure_reason is None

    app._status_label.configure(text="keep")
    app._on_reprint_failed()
    assert app._status_label.cget("text") == "keep"

    app.destroy()

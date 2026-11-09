"""Headless verify: row click previews, inline remove, preview opens before raster."""

from __future__ import annotations

import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk
from PIL import Image
from pypdf import PageObject, PdfWriter

import paperflick.ui.main_window as main_module
import paperflick.ui.preview_window as preview_module
from paperflick.core.batch import AddPaths, BatchPhase, ItemStatus
from paperflick.core.batch.types import PrintItem
from paperflick.ui.main_window import MainWindow
from paperflick.ui.preview_window import PAGE_FALLBACK_TEXT, PreviewWindow


class _PageLoads:
    """Stand-in for thumbnail decode. Records whether the window was mapped."""

    def __init__(self, app: MainWindow) -> None:
        self._app = app
        self.names: list[str] = []
        self.mapped: list[bool] = []
        self.mode = "image"

    def __call__(self, item: PrintItem, **_kwargs: object) -> Image.Image | None:
        preview = self._app._preview
        mapped = bool(
            preview is not None and preview.winfo_exists() and preview.winfo_ismapped()
        )
        self.names.append(item.path.name)
        self.mapped.append(mapped)
        if self.mode == "boom":
            raise RuntimeError("decode")
        if self.mode == "none":
            return None
        return Image.new("RGB", (24, 16), (200, 0, 0))

    def reset(self) -> None:
        """Forget calls from the previous open."""
        self.names.clear()
        self.mapped.clear()


def _walk(widget: object) -> list[object]:
    """Return ``widget`` and every descendant."""
    found = [widget]
    children = getattr(widget, "winfo_children", None)
    if children is None:
        return found
    for child in children():
        found.extend(_walk(child))
    return found


def _button_texts(widget: object) -> list[str]:
    """Captions of every button under ``widget``."""
    texts: list[str] = []
    for node in _walk(widget):
        if isinstance(node, ctk.CTkButton):
            texts.append(str(node.cget("text")))
    return texts


def _texts(widget: object) -> list[str]:
    """Visible captions on labels, radios, and buttons."""
    texts: list[str] = []
    for node in _walk(widget):
        if isinstance(node, (ctk.CTkLabel, ctk.CTkButton, ctk.CTkRadioButton)):
            text = str(node.cget("text"))
            if text:
                texts.append(text)
    return texts


def _rows(app: MainWindow) -> list[ctk.CTkFrame]:
    """Item rows currently packed in the list."""
    rows: list[ctk.CTkFrame] = []
    for child in app._item_list._scroll.winfo_children():
        if isinstance(child, ctk.CTkFrame):
            rows.append(child)
    return rows


def _row_named(app: MainWindow, name: str) -> ctk.CTkFrame:
    """Return the row whose identity label starts with ``name``."""
    for row in _rows(app):
        for child in row.winfo_children():
            if isinstance(child, ctk.CTkLabel) and str(child.cget("text")).startswith(name):
                return row
    raise AssertionError(name)


def _identity_label(row: ctk.CTkFrame, name: str) -> ctk.CTkLabel:
    """Return the identity label for ``name``."""
    for child in row.winfo_children():
        if isinstance(child, ctk.CTkLabel) and str(child.cget("text")).startswith(name):
            return child
    raise AssertionError(name)


def _remove_button(row: ctk.CTkFrame) -> ctk.CTkButton:
    """Return the inline 移除 button."""
    for child in row.winfo_children():
        if isinstance(child, ctk.CTkButton) and str(child.cget("text")) == "移除":
            return child
    raise AssertionError("移除")


def _toolbar_button(app: MainWindow, caption: str) -> ctk.CTkButton:
    """Return the single button whose caption is ``caption``."""
    matches = [
        node
        for node in _walk(app)
        if isinstance(node, ctk.CTkButton) and str(node.cget("text")) == caption
    ]
    if len(matches) != 1:
        raise AssertionError(f"{caption}: {len(matches)}")
    return matches[0]


def _click_body(widget: ctk.CTkBaseClass) -> None:
    """Click the drawn canvas, which is what a row label hit-tests."""
    canvas = getattr(widget, "_canvas", None)
    if canvas is None:
        raise AssertionError(type(widget))
    canvas.event_generate("<Button-1>", x=4, y=4)


def _click_button(button: ctk.CTkButton) -> None:
    """Release on the button canvas the way a real click does."""
    button._canvas.event_generate("<Enter>")
    button._canvas.event_generate("<ButtonRelease-1>", x=4, y=4)


def _names(app: MainWindow) -> list[str]:
    """File names in list order."""
    return [item.path.name for item in app._session.snapshot().items]


def _pump_until(app: MainWindow, ready: Callable[[], bool], timeout: float = 2.0) -> None:
    """Pump Tk until ``ready`` or ``timeout`` seconds."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.update()
        if ready():
            return
        time.sleep(0.02)
    raise AssertionError("timed out")


def _wait_idle(app: MainWindow) -> None:
    """Pump until the Batch is idle and nothing is still queued."""
    def _ready() -> bool:
        snap = app._session.snapshot()
        return (
            snap.phase is BatchPhase.IDLE
            and snap.waiting_count == 0
            and snap.printing_count == 0
        )

    _pump_until(app, _ready, timeout=5.0)


def _png(path: Path, size: tuple[int, int]) -> None:
    """Write a tiny RGB PNG."""
    Image.new("RGB", size, (20, 20, 20)).save(path)


def _write_pdf(path: Path) -> None:
    """Write a one-page PDF so intake can read a real page."""
    writer = PdfWriter()
    writer.add_page(PageObject.create_blank_page(width=595, height=842))
    with path.open("wb") as handle:
        writer.write(handle)


def main() -> None:
    """Prove list click, inline remove, and preview-before-raster."""
    appdata = Path(tempfile.mkdtemp(prefix="paperflick-list-preview-"))
    os.environ["PAPERFLICK_APPDATA"] = str(appdata)
    root = Path(tempfile.mkdtemp(prefix="paperflick-list-preview-files-"))
    alpha = root / "a.png"
    beta = root / "b.png"
    gamma = root / "c.png"
    keep = root / "keep.png"
    doomed = root / "gone.pdf"
    running_names = ("d.png", "e.png", "f.png")
    _png(alpha, (80, 40))
    _png(beta, (40, 80))
    _png(gamma, (90, 40))
    _png(keep, (40, 40))
    _write_pdf(doomed)
    for name in running_names:
        _png(root / name, (30, 30))

    asks: list[str] = []
    decisions: list[bool] = []

    def _ask(title: str, _message: str, **_kwargs: object) -> bool:
        asks.append(title)
        if not decisions:
            raise AssertionError(f"unexpected confirm: {title}")
        return decisions.pop(0)

    main_module.messagebox.askyesno = _ask

    lifts: list[str] = []
    focuses: list[str] = []
    orig_lift = PreviewWindow.lift
    orig_focus = PreviewWindow.focus_force

    def _track_lift(self: PreviewWindow, aboveThis: object = None) -> object:
        lifts.append("lift")
        return orig_lift(self, aboveThis)

    def _track_focus(self: PreviewWindow) -> object:
        focuses.append("focus")
        return orig_focus(self)

    PreviewWindow.lift = _track_lift  # type: ignore[method-assign]
    PreviewWindow.focus_force = _track_focus  # type: ignore[method-assign]

    artifact = Path(__file__).resolve().parent / "artifacts" / "list-preview"
    artifact.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    app = MainWindow()
    loads = _PageLoads(app)
    preview_module._page_image = loads  # type: ignore[assignment]
    try:
        app.update_idletasks()
        app._dry_var.set(True)
        app._persist()

        button_texts = _button_texts(app)
        assert "添加文件" in button_texts
        assert "移除全部失败" in button_texts
        assert "移除所选" not in button_texts
        assert "预览" not in button_texts
        assert "只勾选失败项" not in button_texts
        assert not any(isinstance(node, ctk.CTkCheckBox) for node in _walk(app._item_list))

        app._session.apply(AddPaths([alpha, beta]))
        app.update_idletasks()
        assert len(_rows(app)) == 2
        assert all(_remove_button(row) for row in _rows(app))

        loads.mode = "image"
        loads.reset()
        _click_body(_identity_label(_row_named(app, "a.png"), "a.png"))
        assert loads.names == []
        first = app._preview
        assert isinstance(first, PreviewWindow)
        assert first.winfo_exists()
        chrome = _texts(first)
        assert any("a.png" in text for text in chrome)
        assert "横向" in chrome
        assert "纵向" in chrome
        assert "打印机" in chrome
        assert "应用到此项" in chrome
        assert PAGE_FALLBACK_TEXT not in chrome
        assert lifts
        assert focuses
        lifts_before = len(lifts)
        focuses_before = len(focuses)
        _pump_until(app, lambda: bool(loads.names))
        assert loads.names == ["a.png"]
        assert loads.mapped == [True]
        assert first._photo is not None
        assert len(lifts) > lifts_before
        assert len(focuses) > focuses_before
        lines.append("preview chrome before raster; image after map")

        loads.mode = "none"
        loads.reset()
        _click_body(_identity_label(_row_named(app, "b.png"), "b.png"))
        assert not first.winfo_exists()
        second = app._preview
        assert isinstance(second, PreviewWindow)
        assert second is not first
        assert loads.names == []
        _pump_until(app, lambda: "b.png" in loads.names)
        assert loads.mapped[-1] is True
        assert PAGE_FALLBACK_TEXT in _texts(second)
        lines.append("one preview; none falls back to text")

        loads.mode = "boom"
        loads.reset()
        app._close_preview()
        _click_body(_identity_label(_row_named(app, "a.png"), "a.png"))
        _pump_until(app, lambda: "a.png" in loads.names)
        boom = app._preview
        assert isinstance(boom, PreviewWindow)
        assert PAGE_FALLBACK_TEXT in _texts(boom)
        assert lifts
        assert focuses
        lines.append("decode error falls back to text and still lifts")

        app._close_preview()
        asks.clear()
        _click_button(_remove_button(_row_named(app, "b.png")))
        app.update_idletasks()
        assert "b.png" not in _names(app)
        assert "a.png" in _names(app)
        assert app._preview is None
        assert asks == []
        lines.append("inline 移除 has no confirm and does not preview")

        _png(gamma, (90, 40))
        app._interval_var.set("0.05")
        app._persist()
        app._session.apply(AddPaths([gamma]))
        app.update_idletasks()
        assert _names(app) == ["a.png", "c.png"]
        app._on_start()
        _wait_idle(app)
        started = app._session.snapshot()
        assert started.success_count == 2
        assert started.failed_count == 0
        assert all(item.status is ItemStatus.SUCCESS for item in started.items)
        lines.append("start prints every waiting item")

        app._session.apply(AddPaths([doomed, keep]))
        doomed.unlink()
        app.update_idletasks()
        app._on_start()
        _wait_idle(app)
        failed = [
            item
            for item in app._session.snapshot().items
            if item.path.name == "gone.pdf" and item.status is ItemStatus.FAILED
        ]
        assert failed
        decisions.append(False)
        _click_button(_toolbar_button(app, "移除全部失败"))
        app.update_idletasks()
        assert asks == ["移除全部失败"]
        assert "gone.pdf" in _names(app)
        decisions.append(True)
        _click_button(_toolbar_button(app, "移除全部失败"))
        app.update_idletasks()
        assert "gone.pdf" not in _names(app)
        assert "keep.png" in _names(app)
        assert "a.png" in _names(app)
        asks_before = len(asks)
        _click_button(_toolbar_button(app, "移除全部失败"))
        assert len(asks) == asks_before
        lines.append("移除全部失败 confirms; empty failure list does not")

        for name in list(_names(app)):
            app.update_idletasks()
            _remove_button(_row_named(app, name)).invoke()
        app.update_idletasks()
        assert _names(app) == [], _names(app)

        app._interval_var.set("30")
        app._persist()
        app._session.apply(AddPaths([root / name for name in running_names]))
        app.update_idletasks()
        app._on_start()
        app.update_idletasks()
        running = app._session.snapshot()
        assert running.phase is BatchPhase.RUNNING
        assert running.success_count == 1
        assert running.waiting_count == 2
        asks.clear()
        _remove_button(_row_named(app, "e.png")).invoke()
        app.update_idletasks()
        assert app._session.snapshot().phase is BatchPhase.RUNNING
        assert "e.png" not in _names(app)
        assert asks == []
        app._on_pause()
        assert app._session.snapshot().phase is BatchPhase.PAUSED
        _remove_button(_row_named(app, "f.png")).invoke()
        app.update_idletasks()
        paused = app._session.snapshot()
        assert paused.phase is BatchPhase.PAUSED
        assert "f.png" not in _names(app)
        assert asks == []
        lines.append("remove while running and paused, no confirm")

        lines.append("headless MainWindow")
        lines.append("PASS list-preview")
        (artifact / "log.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("PASS list-preview")
    finally:
        app.destroy()


if __name__ == "__main__":
    main()

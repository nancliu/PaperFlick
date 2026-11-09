"""Headless verify for preview orientation apply scopes."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import customtkinter as ctk
from PIL import Image
from pypdf import PageObject, PdfWriter

import paperflick.ui.preview_window as preview_module
from paperflick.core.batch import AddPaths, ApplyScope, BatchPhase, Orientation, PrintItem
from paperflick.ui.item_list import orientation_label
from paperflick.ui.main_window import MainWindow
from paperflick.ui.preview_window import PreviewWindow


def _write_pdf(path: Path, width: float, height: float) -> None:
    """Write a one-page PDF with the given mediabox."""
    writer = PdfWriter()
    writer.add_page(PageObject.create_blank_page(width=width, height=height))
    with path.open("wb") as handle:
        writer.write(handle)


def _click_body(widget: ctk.CTkBaseClass) -> None:
    """Click the widget canvas the way a row label hit-tests."""
    canvas = getattr(widget, "_canvas", None)
    assert canvas is not None
    canvas.event_generate("<Button-1>", x=4, y=4)


def _row_named(app: MainWindow, name: str) -> ctk.CTkFrame:
    """Return the row whose identity label starts with ``name``."""
    for row in app._item_list._scroll.winfo_children():
        if not isinstance(row, ctk.CTkFrame):
            continue
        for child in row.winfo_children():
            if isinstance(child, ctk.CTkLabel) and str(child.cget("text")).startswith(name):
                return row
    raise AssertionError(name)


def _labels(app: MainWindow) -> list[str]:
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


def _wait_idle(app: MainWindow) -> None:
    """Pump Tk until the Dry Run batch is idle."""
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        app.update()
        snap = app._session.snapshot()
        if snap.phase is BatchPhase.IDLE and snap.waiting_count == 0 and snap.printing_count == 0:
            return
        time.sleep(0.02)
    snap = app._session.snapshot()
    raise AssertionError(
        f"batch still {snap.phase.value} "
        f"waiting={snap.waiting_count} printing={snap.printing_count}"
    )


def _item(app: MainWindow, name: str) -> PrintItem:
    """Return the snapshot row with this file name."""
    return next(item for item in app._session.snapshot().items if item.path.name == name)


def _open_preview(app: MainWindow, name: str) -> PreviewWindow:
    """Click the row identity and return the one open preview."""
    row = _row_named(app, name)
    label = next(
        child
        for child in row.winfo_children()
        if isinstance(child, ctk.CTkLabel) and str(child.cget("text")).startswith(name)
    )
    _click_body(label)
    preview = app._preview
    assert isinstance(preview, PreviewWindow)
    assert preview.winfo_exists()
    return preview


def main() -> None:
    """Apply preview scopes, then Dry Run the same list."""
    appdata = Path(tempfile.mkdtemp(prefix="paperflick-preview-"))
    os.environ["PAPERFLICK_APPDATA"] = str(appdata)
    root = Path(tempfile.mkdtemp(prefix="paperflick-preview-files-"))
    tall = root / "tall.png"
    wide = root / "wide.png"
    later = root / "later.png"
    pdf = root / "page.pdf"
    Image.new("RGB", (100, 200), color=(20, 20, 20)).save(tall)
    Image.new("RGB", (200, 100), color=(20, 20, 20)).save(wide)
    Image.new("RGB", (180, 90), color=(20, 20, 20)).save(later)
    _write_pdf(pdf, 595, 842)

    artifact = Path(__file__).resolve().parent / "artifacts" / "preview-orientation"
    artifact.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    app = MainWindow()
    try:
        app.update_idletasks()
        app._session.apply(AddPaths([tall, wide, pdf]))
        app.update_idletasks()
        assert all(item.orientation is Orientation.AUTO for item in app._session.snapshot().items)
        assert orientation_label(_item(app, "tall.png")) == "纵向"
        assert orientation_label(_item(app, "wide.png")) == "横向"

        first = _open_preview(app, "tall.png")
        second = _open_preview(app, "wide.png")
        assert not first.winfo_exists()
        assert app._preview is second
        second.destroy()
        app._preview = None

        preview = _open_preview(app, "tall.png")
        preview._choice.set("")
        preview._commit(ApplyScope.THIS)
        assert preview.winfo_exists()
        assert _item(app, "tall.png").orientation is Orientation.AUTO
        preview._choice.set(Orientation.LANDSCAPE.value)
        preview._commit(ApplyScope.THIS)
        app.update_idletasks()
        assert not preview.winfo_exists()
        assert _item(app, "tall.png").orientation is Orientation.LANDSCAPE
        assert _item(app, "wide.png").orientation is Orientation.AUTO
        assert _item(app, "page.pdf").orientation is Orientation.AUTO
        assert any("tall.png  横向" in text for text in _labels(app))

        preview = _open_preview(app, "tall.png")
        app._status_label.configure(text="keep")
        preview._choice.set(Orientation.LANDSCAPE.value)
        preview._commit(ApplyScope.THIS)
        assert preview.winfo_exists()
        assert app._status_label.cget("text") == "keep"
        preview.destroy()

        preview = _open_preview(app, "wide.png")
        preview._choice.set(Orientation.PRINTER_DEFAULT.value)
        preview._commit(ApplyScope.SAME_KIND)
        app.update_idletasks()
        assert _item(app, "tall.png").orientation is Orientation.PRINTER_DEFAULT
        assert _item(app, "wide.png").orientation is Orientation.PRINTER_DEFAULT
        assert orientation_label(_item(app, "wide.png")) == "打印机"
        assert _item(app, "page.pdf").orientation is Orientation.AUTO

        answers = iter((False, True))

        def _ask(*_args: object, **_kwargs: object) -> bool:
            return next(answers)

        preview_module.messagebox.askyesno = _ask

        preview = _open_preview(app, "page.pdf")
        preview._choice.set(Orientation.PORTRAIT.value)
        before = [item.orientation for item in app._session.snapshot().items]
        preview._commit(ApplyScope.ALL)
        assert preview.winfo_exists()
        assert [item.orientation for item in app._session.snapshot().items] == before
        preview._commit(ApplyScope.ALL)
        app.update_idletasks()
        assert not preview.winfo_exists()
        assert all(
            item.orientation is Orientation.PORTRAIT for item in app._session.snapshot().items
        )
        assert any("wide.png  纵向" in text for text in _labels(app))

        app._session.apply(AddPaths([later]))
        app.update_idletasks()
        assert _item(app, "later.png").orientation is Orientation.AUTO
        assert all(
            item.orientation is Orientation.PORTRAIT
            for item in app._session.snapshot().items
            if item.path.name != "later.png"
        )

        app._dry_var.set(True)
        app._interval_var.set("0.05")
        app._persist()
        app._on_start()
        _wait_idle(app)
        snap = app._session.snapshot()
        assert snap.success_count == 4
        assert snap.failed_count == 0
        assert _item(app, "later.png").orientation is Orientation.AUTO
        assert all(
            item.orientation is Orientation.PORTRAIT
            for item in snap.items
            if item.path.name != "later.png"
        )
        lines.append("headless MainWindow")
        lines.append("scopes=this,same_kind,all-cancel,all-accept")
        lines.append("dry_run success=4 orientations held")
        lines.append("PASS preview-orientation")
        (artifact / "log.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("PASS preview-orientation")
    finally:
        app.destroy()


if __name__ == "__main__":
    main()

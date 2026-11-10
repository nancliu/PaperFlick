"""Headless verify for Preview Paper Facing overlay."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_REPO_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_REPO_SRC) not in sys.path:
    sys.path.insert(0, str(_REPO_SRC))

from PIL import Image

from paperflick.core.batch import AddPaths, ApplyScope, Facing, Orientation
from paperflick.ui.main_window import MainWindow
from paperflick.ui.preview_window import UNFORCED_COPY, PreviewWindow


def _click_body(widget: object) -> None:
    """Click the widget canvas the way a row label hit-tests."""
    canvas = getattr(widget, "_canvas", None)
    assert canvas is not None
    canvas.event_generate("<Button-1>", x=4, y=4)


def _row_named(app: MainWindow, name: str):
    """Return the row whose identity label starts with ``name``."""
    import customtkinter as ctk

    for row in app._item_list._scroll.winfo_children():
        if not isinstance(row, ctk.CTkFrame):
            continue
        for child in row.winfo_children():
            if isinstance(child, ctk.CTkLabel) and str(child.cget("text")).startswith(name):
                return row
    raise AssertionError(name)


def _open_preview(app: MainWindow, name: str) -> PreviewWindow:
    """Click the row identity and return the one open preview."""
    import customtkinter as ctk

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
    app.update_idletasks()
    return preview


def _pump(app: MainWindow, preview: PreviewWindow) -> None:
    """Let choice traces and idle refresh run."""
    app.update()
    preview.update_idletasks()
    app.update_idletasks()


def main() -> None:
    """Switch radios and prove Preview Paper aspect + reopen."""
    appdata = Path(tempfile.mkdtemp(prefix="paperflick-preview-paper-"))
    os.environ["PAPERFLICK_APPDATA"] = str(appdata)
    root = Path(tempfile.mkdtemp(prefix="paperflick-preview-paper-files-"))
    tall = root / "tall.png"
    wide = root / "wide.png"
    Image.new("RGB", (100, 200), color=(20, 20, 20)).save(tall)
    Image.new("RGB", (200, 100), color=(20, 20, 20)).save(wide)

    artifact = Path(__file__).resolve().parent / "artifacts" / "preview-paper"
    artifact.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    app = MainWindow()
    try:
        app.update_idletasks()
        app._session.apply(AddPaths([tall, wide]))
        app.update_idletasks()

        preview = _open_preview(app, "tall.png")
        assert preview._choice.get() == ""
        assert preview.paper_facing() is Facing.PORTRAIT
        pw, ph = preview.paper_pixel_size_now()
        assert ph > pw
        assert "纵向" in preview.draft_summary_text()

        preview._choice.set(Orientation.LANDSCAPE.value)
        _pump(app, preview)
        assert preview.paper_facing() is Facing.LANDSCAPE
        pw, ph = preview.paper_pixel_size_now()
        assert pw > ph
        assert "横向" in preview.draft_summary_text()

        preview._choice.set(Orientation.PRINTER_DEFAULT.value)
        _pump(app, preview)
        assert preview.paper_facing() is None
        pw, ph = preview.paper_pixel_size_now()
        assert pw == ph
        assert UNFORCED_COPY in preview.draft_summary_text()

        preview._choice.set(Orientation.LANDSCAPE.value)
        _pump(app, preview)
        preview._commit(ApplyScope.THIS)
        app.update_idletasks()
        assert not preview.winfo_exists()

        preview = _open_preview(app, "tall.png")
        assert preview._choice.get() == Orientation.LANDSCAPE.value
        assert preview.paper_facing() is Facing.LANDSCAPE
        pw, ph = preview.paper_pixel_size_now()
        assert pw > ph
        preview.destroy()
        app._preview = None

        preview = _open_preview(app, "wide.png")
        assert preview._choice.get() == ""
        assert preview.paper_facing() is Facing.LANDSCAPE
        pw, ph = preview.paper_pixel_size_now()
        assert pw > ph
        preview._choice.set(Orientation.PORTRAIT.value)
        _pump(app, preview)
        assert preview.paper_facing() is Facing.PORTRAIT
        pw, ph = preview.paper_pixel_size_now()
        assert ph > pw
        preview._commit(ApplyScope.THIS)
        app.update_idletasks()

        preview = _open_preview(app, "wide.png")
        assert preview._choice.get() == Orientation.PORTRAIT.value
        assert preview.paper_facing() is Facing.PORTRAIT
        pw, ph = preview.paper_pixel_size_now()
        assert ph > pw

        lines.append("headless MainWindow")
        lines.append("auto-empty portrait; landscape swap; printer unforced")
        lines.append("apply+reopen landscape; wide auto then portrait")
        lines.append("PASS preview-paper")
        (artifact / "log.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("PASS preview-paper")
    finally:
        app.destroy()


if __name__ == "__main__":
    main()

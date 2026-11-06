"""Headless proof for image print with Dry Run off and an injected page device."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from paperflick.core.batch import AddPaths, BatchPhase, ClearItems
from paperflick.core.batch.types import Facing
from paperflick.core.settings import load
from paperflick.core.submit import SubmitFailed, SubmitRequest
from paperflick.core.submit.image_win import PageDevice
from paperflick.ui.main_window import MainWindow


class _DocxStub:
    """DOCX port that fails without launching Word or OnlyOffice."""

    def submit(self, _request: SubmitRequest) -> SubmitFailed:
        """Return a dual-engine failure reason for the row label."""
        return SubmitFailed("Word：stub；OnlyOffice：stub")


class _RecordingPage:
    """Page device that records the job and draws nothing."""

    def __init__(self, printer: str, calls: list[tuple[float, str, Facing | None]]) -> None:
        self._printer = printer
        self._calls = calls

    def begin(self, title: str, facing: Facing | None) -> tuple[int, int, int, int]:
        """Record one page open. The printable area is a stand-in square."""
        self._calls.append((time.monotonic(), self._printer, facing))
        return (0, 0, 1000, 1000)

    def blit(self, image: Image.Image, box: tuple[int, int, int, int]) -> None:
        """Accept the fitted bitmap. Nothing is sent to a printer."""

    def finish(self) -> None:
        """Commit is a no-op for the stand-in page."""

    def abort(self) -> None:
        """Abort is a no-op for the stand-in page."""


def _write_png(path: Path, width: int, height: int) -> None:
    """Write a solid RGB image of ``width`` by ``height`` pixels."""
    Image.new("RGB", (width, height), (20, 40, 60)).save(path)


def _wait_idle(app: MainWindow) -> None:
    """Pump Tk until the Batch is idle and no row is still queued."""
    deadline = time.monotonic() + 8.0
    while time.monotonic() < deadline:
        app.update()
        snap = app._session.snapshot()
        if snap.phase is BatchPhase.IDLE and snap.waiting_count == 0 and snap.printing_count == 0:
            return
        time.sleep(0.02)
    snap = app._session.snapshot()
    raise AssertionError(
        f"batch still {snap.phase.value} success={snap.success_count} "
        f"failed={snap.failed_count} waiting={snap.waiting_count}"
    )


def _row_labels(app: MainWindow) -> list[str]:
    """Visible row labels, skipping empty checkbox text."""
    labels: list[str] = []
    for row in app._item_list._scroll.winfo_children():
        for child in row.winfo_children():
            if not isinstance(child, ctk.CTkLabel):
                continue
            text = str(child.cget("text"))
            if text:
                labels.append(text)
    return labels


def _prove_dry_run_skips_the_spooler(
    app: MainWindow,
    root: Path,
    calls: list[tuple[float, str, Facing | None]],
) -> None:
    """Dry Run on must finish an image without opening a page device."""
    _write_png(root / "only.png", 20, 10)
    app._dry_var.set(True)
    app._interval_var.set("0.4")
    app._on_interval_commit()
    app._persist()
    app._session.apply(AddPaths([root / "only.png"]))
    app._on_start()
    _wait_idle(app)
    snap = app._session.snapshot()
    assert snap.success_count == 1, snap
    assert calls == [], calls
    app._session.apply(ClearItems())
    assert app._session.snapshot().items == ()


def _prove_real_image_print(
    app: MainWindow,
    root: Path,
    calls: list[tuple[float, str, Facing | None]],
) -> None:
    """Dry Run off prints a wide image then a tall one and keeps going after failures."""
    _write_png(root / "wide.png", 20, 10)
    _write_png(root / "tall.png", 10, 20)
    bad = root / "bad.png"
    bad.write_bytes(b"not-a-png")
    docx = root / "note.docx"
    docx.write_bytes(b"not-a-docx")
    app._dry_var.set(False)
    app._interval_var.set("0.4")
    app._on_interval_commit()
    app._persist()
    saved = load()
    assert saved.dry_run is False
    assert saved.interval_seconds == 0.4
    app._session.apply(AddPaths([root / "wide.png", bad, docx, root / "tall.png"]))
    app._on_start()
    _wait_idle(app)
    snap = app._session.snapshot()
    assert snap.phase is BatchPhase.IDLE
    assert snap.success_count == 2
    assert snap.failed_count == 2
    assert snap.items[1].failure_reason is not None
    assert snap.items[1].failure_reason.startswith("图片无法打开")
    assert snap.items[2].failure_reason is not None
    assert "Word" in snap.items[2].failure_reason
    assert "OnlyOffice" in snap.items[2].failure_reason
    assert [call[2] for call in calls] == [Facing.LANDSCAPE, Facing.PORTRAIT]
    assert calls[1][0] - calls[0][0] >= 0.3
    labels = _row_labels(app)
    assert any("图片无法打开" in text for text in labels)
    assert any("Word" in text and "OnlyOffice" in text for text in labels)


def _write_log(calls: list[tuple[float, str, Facing | None]]) -> None:
    """Leave a rerunnable trace under the verify artifacts folder."""
    folder = Path(__file__).resolve().parent / "artifacts" / "image-real-print"
    folder.mkdir(parents=True, exist_ok=True)
    lines = ["image-real-print"]
    for stamp, printer, facing in calls:
        label = "default" if facing is None else facing.value
        lines.append(f"{stamp:.3f} {printer} {label}")
    (folder / "log.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Run the Dry Run skip and the real image submit against one window."""
    appdata = Path(tempfile.mkdtemp(prefix="paperflick-image-appdata-"))
    os.environ["PAPERFLICK_APPDATA"] = str(appdata)
    root = Path(tempfile.mkdtemp(prefix="paperflick-image-files-"))
    missing_sumatra = root / "missing-sumatra.exe"
    calls: list[tuple[float, str, Facing | None]] = []

    def devices(printer: str) -> PageDevice:
        return _RecordingPage(printer, calls)

    app = MainWindow(
        sumatra_executable=missing_sumatra,
        image_devices=devices,
        docx_submit=_DocxStub(),
    )
    try:
        app.update_idletasks()
        _prove_dry_run_skips_the_spooler(app, root, calls)
        _prove_real_image_print(app, root, calls)
    finally:
        app.destroy()
    _write_log(calls)
    print("PASS image-real-print")


if __name__ == "__main__":
    main()

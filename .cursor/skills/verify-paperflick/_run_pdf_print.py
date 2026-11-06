"""Headless proof for PDF print with Dry Run off and an injected Sumatra."""

from __future__ import annotations

import os
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path
from subprocess import CompletedProcess

import customtkinter as ctk
from pypdf import PdfWriter

from paperflick.core.batch import AddPaths, BatchPhase, ClearItems
from paperflick.core.settings import load
from paperflick.ui.main_window import MainWindow


def _write_pdf(path: Path, width: float, height: float) -> None:
    """Write a one-page PDF whose mediabox is ``width`` by ``height``."""
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=height)
    with path.open("wb") as handle:
        writer.write(handle)


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


def _prove_dry_run_skips_sumatra(
    app: MainWindow,
    root: Path,
    calls: list[tuple[float, list[str]]],
) -> None:
    """Dry Run on must finish a PDF without calling the injected Sumatra."""
    _write_pdf(root / "only.pdf", 100, 200)
    app._dry_var.set(True)
    app._interval_var.set("0.4")
    app._on_interval_commit()
    app._persist()
    app._session.apply(AddPaths([root / "only.pdf"]))
    app._on_start()
    _wait_idle(app)
    snap = app._session.snapshot()
    assert snap.success_count == 1, snap
    assert calls == [], calls
    app._session.apply(ClearItems())
    assert app._session.snapshot().items == ()


def _prove_real_pdf_print(
    app: MainWindow,
    root: Path,
    calls: list[tuple[float, list[str]]],
) -> None:
    """Dry Run off sends landscape then portrait and keeps going after a DOCX."""
    _write_pdf(root / "wide.pdf", 200, 100)
    _write_pdf(root / "tall.pdf", 100, 200)
    docx = root / "note.docx"
    docx.write_bytes(b"not-a-docx")
    app._dry_var.set(False)
    app._interval_var.set("0.4")
    app._on_interval_commit()
    app._persist()
    saved = load()
    assert saved.dry_run is False
    assert saved.interval_seconds == 0.4
    app._session.apply(AddPaths([root / "wide.pdf", docx, root / "tall.pdf"]))
    app._on_start()
    _wait_idle(app)
    snap = app._session.snapshot()
    assert snap.phase is BatchPhase.IDLE
    assert snap.success_count == 2
    assert snap.failed_count == 1
    assert snap.items[1].failure_reason == "该格式暂不支持打印"
    assert [call[1][call[1].index("-print-settings") + 1] for call in calls] == [
        "landscape",
        "portrait",
    ]
    assert all("-print-to-default" in call[1] for call in calls)
    assert all("-silent" in call[1] for call in calls)
    assert calls[1][0] - calls[0][0] >= 0.3
    assert any("该格式暂不支持打印" in text for text in _row_labels(app))


def _write_log(calls: list[tuple[float, list[str]]]) -> None:
    """Leave a rerunnable trace under the verify artifacts folder."""
    folder = Path(__file__).resolve().parent / "artifacts" / "pdf-real-print"
    folder.mkdir(parents=True, exist_ok=True)
    lines = ["pdf-real-print"]
    for stamp, argv in calls:
        lines.append(f"{stamp:.3f} {' '.join(argv)}")
    (folder / "log.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Run the Dry Run skip and the real PDF submit against one window."""
    appdata = Path(tempfile.mkdtemp(prefix="paperflick-pdf-appdata-"))
    os.environ["PAPERFLICK_APPDATA"] = str(appdata)
    root = Path(tempfile.mkdtemp(prefix="paperflick-pdf-files-"))
    exe = root / "SumatraPDF.exe"
    exe.write_bytes(b"MZ")
    calls: list[tuple[float, list[str]]] = []

    def run(argv: Sequence[str]) -> CompletedProcess[str]:
        calls.append((time.monotonic(), list(argv)))
        return CompletedProcess(list(argv), 0)

    app = MainWindow(sumatra_executable=exe, sumatra_run=run)
    try:
        app.update_idletasks()
        _prove_dry_run_skips_sumatra(app, root, calls)
        _prove_real_pdf_print(app, root, calls)
    finally:
        app.destroy()
    _write_log(calls)
    print("PASS pdf-real-print")


if __name__ == "__main__":
    main()

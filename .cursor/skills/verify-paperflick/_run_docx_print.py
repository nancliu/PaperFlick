"""Headless proof for DOCX print with Dry Run off and injected engines."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import time
from pathlib import Path

import customtkinter as ctk
from docx import Document
from docx.shared import Mm

from paperflick.core.batch import AddPaths, BatchPhase, ClearItems
from paperflick.core.batch.types import Facing
from paperflick.core.settings import load
from paperflick.core.submit import DocxSubmit, SubmitFailed, SubmitOk, SubmitResult
from paperflick.core.submit.docx_print import DocxJob
from paperflick.ui.main_window import MainWindow


def _write_docx(path: Path, width_mm: float, height_mm: float) -> None:
    """Write a one-section DOCX whose first page is ``width_mm`` by ``height_mm``."""
    document = Document()
    section = document.sections[0]
    section.page_width = Mm(width_mm)
    section.page_height = Mm(height_mm)
    document.save(path)


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


class _Engines:
    """Word then OnlyOffice stand-ins. Call order decides success and failure."""

    def __init__(self) -> None:
        self.word_jobs: list[tuple[float, DocxJob]] = []
        self.oo_jobs: list[tuple[float, DocxJob]] = []

    def word(self, job: DocxJob) -> SubmitResult:
        """First Word call succeeds. Later Word calls fail so OnlyOffice can run."""
        self.word_jobs.append((time.monotonic(), job))
        if len(self.word_jobs) == 1:
            return SubmitOk()
        return SubmitFailed("未找到 Word")

    def onlyoffice(self, job: DocxJob) -> SubmitResult:
        """First OnlyOffice call succeeds. The next call fails the item."""
        self.oo_jobs.append((time.monotonic(), job))
        if len(self.oo_jobs) == 1:
            return SubmitOk()
        return SubmitFailed("未找到 OnlyOffice")


class _LogCapture(logging.Handler):
    """Keep DOCX engine log lines for the artifact."""

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


def _prove_dry_run_skips_engines(app: MainWindow, root: Path, engines: _Engines) -> None:
    """Dry Run on must finish a DOCX without calling Word or OnlyOffice."""
    _write_docx(root / "only.docx", 210, 297)
    app._dry_var.set(True)
    app._interval_var.set("0.4")
    app._on_interval_commit()
    app._persist()
    app._session.apply(AddPaths([root / "only.docx"]))
    app._on_start()
    _wait_idle(app)
    snap = app._session.snapshot()
    assert snap.success_count == 1, snap
    assert engines.word_jobs == []
    assert engines.oo_jobs == []
    app._session.apply(ClearItems())
    assert app._session.snapshot().items == ()


def _prove_real_docx_print(
    app: MainWindow,
    root: Path,
    engines: _Engines,
    logs: _LogCapture,
) -> None:
    """Dry Run off uses Word, falls back once, and continues after both fail."""
    _write_docx(root / "wide.docx", 297, 210)
    _write_docx(root / "tall.docx", 210, 297)
    _write_docx(root / "last.docx", 210, 297)
    app._dry_var.set(False)
    app._interval_var.set("0.4")
    app._on_interval_commit()
    app._persist()
    saved = load()
    assert saved.dry_run is False
    assert saved.interval_seconds == 0.4
    app._session.apply(AddPaths([root / "wide.docx", root / "tall.docx", root / "last.docx"]))
    app._on_start()
    _wait_idle(app)
    snap = app._session.snapshot()
    assert snap.phase is BatchPhase.IDLE
    assert snap.success_count == 2
    assert snap.failed_count == 1
    assert snap.items[0].status.value == "success"
    assert snap.items[1].status.value == "success"
    assert snap.items[2].failure_reason is not None
    assert "Word" in snap.items[2].failure_reason
    assert "OnlyOffice" in snap.items[2].failure_reason
    assert [job.facing for _stamp, job in engines.word_jobs] == [
        Facing.LANDSCAPE,
        Facing.PORTRAIT,
        Facing.PORTRAIT,
    ]
    assert [job.document.name for _stamp, job in engines.oo_jobs] == ["tall.docx", "last.docx"]
    assert engines.word_jobs[1][0] - engines.word_jobs[0][0] >= 0.3
    assert any("engine=Word" in line for line in logs.lines)
    assert any("engine=OnlyOffice" in line for line in logs.lines)
    assert any("OnlyOffice" in text for text in _row_labels(app))


def _write_log(engines: _Engines, logs: _LogCapture) -> None:
    """Leave a rerunnable trace under the verify artifacts folder."""
    folder = Path(__file__).resolve().parent / "artifacts" / "docx-real-print"
    folder.mkdir(parents=True, exist_ok=True)
    lines = ["docx-real-print"]
    for stamp, job in engines.word_jobs:
        lines.append(f"{stamp:.3f} Word {job.facing} {job.document.name}")
    for stamp, job in engines.oo_jobs:
        lines.append(f"{stamp:.3f} OnlyOffice {job.facing} {job.document.name}")
    lines.extend(logs.lines)
    (folder / "log.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Run the Dry Run skip and the real DOCX submit against one window."""
    appdata = Path(tempfile.mkdtemp(prefix="paperflick-docx-appdata-"))
    os.environ["PAPERFLICK_APPDATA"] = str(appdata)
    root = Path(tempfile.mkdtemp(prefix="paperflick-docx-files-"))
    engines = _Engines()
    logs = _LogCapture()
    logger = logging.getLogger("paperflick.submit.docx")
    logger.setLevel(logging.INFO)
    logger.addHandler(logs)
    port = DocxSubmit((("Word", engines.word), ("OnlyOffice", engines.onlyoffice)))
    app = MainWindow(docx_submit=port)
    try:
        app.update_idletasks()
        _prove_dry_run_skips_engines(app, root, engines)
        _prove_real_docx_print(app, root, engines, logs)
    finally:
        app.destroy()
        logger.removeHandler(logs)
        shutil.rmtree(appdata, ignore_errors=True)
        shutil.rmtree(root, ignore_errors=True)
    _write_log(engines, logs)
    print("PASS docx-real-print")


if __name__ == "__main__":
    main()

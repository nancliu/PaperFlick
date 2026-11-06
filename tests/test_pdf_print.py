"""PDF Print Items submit through SumatraPDF when Dry Run is off."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pytest
from pypdf import PdfWriter

from paperflick.core.batch import (
    AddPaths,
    BatchPhase,
    BatchPrefs,
    BatchSession,
    ItemStatus,
    Orientation,
    StartBatch,
)
from paperflick.core.batch.formats import DocKind, Probe
from paperflick.core.batch.types import Measured, PrintItem, Unread
from paperflick.core.submit import (
    DryRunSubmit,
    SubmitFailed,
    SubmitOk,
    SubmitRequest,
    choose_submit_port,
    find_sumatra,
    run_sumatra_process,
)
from paperflick.core.submit.pdf_sumatra import PdfSumatraSubmit


def _prefs(
    *,
    dry_run: bool = False,
    interval: float = 1.0,
    printer: str | None = None,
) -> BatchPrefs:
    return BatchPrefs(
        interval_seconds=interval,
        wait_for_empty_queue=False,
        dry_run=dry_run,
        selected_printer=printer,
    )


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")
    return path


def _write_pdf(path: Path, width: float, height: float) -> Path:
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=height)
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def _pdf_item(
    path: Path,
    *,
    orientation: Orientation = Orientation.AUTO,
    shape: Measured | Unread | None = None,
) -> PrintItem:
    item = PrintItem.added(path, Probe(DocKind.PDF, shape or Measured(100, 200)))
    if orientation is Orientation.AUTO:
        return item
    return replace(item, orientation=orientation)


def _capture_submit(
    tmp_path: Path,
    item: PrintItem,
    *,
    printer: str | None,
    exe_exists: bool = True,
) -> tuple[SubmitOk | SubmitFailed, list[str] | None]:
    exe = tmp_path / "SumatraPDF.exe"
    if exe_exists:
        exe.write_bytes(b"MZ")
    seen: list[list[str]] = []

    def run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        seen.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 0)

    result = PdfSumatraSubmit(exe if exe_exists else None, run=run).submit(
        SubmitRequest(item=item, printer=printer)
    )
    return result, seen[0] if seen else None


@pytest.mark.parametrize(
    ("orientation", "shape", "token"),
    [
        (Orientation.AUTO, Measured(200, 100), "landscape"),
        (Orientation.AUTO, Measured(100, 200), "portrait"),
        (Orientation.AUTO, Measured(100, 100), "portrait"),
        (Orientation.AUTO, Unread("unread"), "portrait"),
        (Orientation.LANDSCAPE, Measured(100, 200), "landscape"),
        (Orientation.PORTRAIT, Measured(200, 100), "portrait"),
        (Orientation.PRINTER_DEFAULT, Measured(200, 100), None),
    ],
)
def test_orientation_is_a_sumatra_print_setting(
    tmp_path: Path,
    orientation: Orientation,
    shape: Measured | Unread,
    token: str | None,
) -> None:
    path = _touch(tmp_path / "page.pdf")
    item = _pdf_item(path, orientation=orientation, shape=shape)
    result, argv = _capture_submit(tmp_path, item, printer="HP Laser")
    assert isinstance(result, SubmitOk)
    assert argv is not None
    assert argv[0].endswith("SumatraPDF.exe")
    assert argv[argv.index("-print-to") + 1] == "HP Laser"
    assert "-silent" in argv
    assert argv[-1] == str(path)
    if token is None:
        assert "-print-settings" not in argv
    else:
        assert argv[argv.index("-print-settings") + 1] == token


def test_blank_printer_uses_the_windows_default(tmp_path: Path) -> None:
    path = _touch(tmp_path / "page.pdf")
    item = _pdf_item(path, orientation=Orientation.PRINTER_DEFAULT)
    _result, argv = _capture_submit(tmp_path, item, printer="  ")
    assert argv is not None
    assert "-print-to-default" in argv
    assert "-print-to" not in argv
    assert "-print-settings" not in argv


def test_missing_sumatra_records_a_reason_and_does_not_spawn(tmp_path: Path) -> None:
    path = _touch(tmp_path / "page.pdf")
    item = _pdf_item(path)
    result, argv = _capture_submit(tmp_path, item, printer=None, exe_exists=False)
    assert isinstance(result, SubmitFailed)
    assert result.reason == "未找到 SumatraPDF"
    assert argv is None

    missing = tmp_path / "gone.exe"
    called = False

    def run(_argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        nonlocal called
        called = True
        return subprocess.CompletedProcess([], 0)

    again = PdfSumatraSubmit(missing, run=run).submit(SubmitRequest(item=item, printer=None))
    assert isinstance(again, SubmitFailed)
    assert again.reason == "未找到 SumatraPDF"
    assert called is False


def test_missing_file_fails_before_sumatra(tmp_path: Path) -> None:
    item = _pdf_item(tmp_path / "gone.pdf")
    result, argv = _capture_submit(tmp_path, item, printer=None)
    assert isinstance(result, SubmitFailed)
    assert result.reason == "文件不存在"
    assert argv is None


def test_non_pdf_fails_without_sumatra(tmp_path: Path) -> None:
    path = _touch(tmp_path / "note.docx")
    item = PrintItem.added(path, Probe(DocKind.DOCX, Measured(100, 200)))
    result, argv = _capture_submit(tmp_path, item, printer=None)
    assert isinstance(result, SubmitFailed)
    assert result.reason == "该格式暂不支持打印"
    assert argv is None


def test_sumatra_nonzero_exit_keeps_the_detail(tmp_path: Path) -> None:
    path = _touch(tmp_path / "page.pdf")
    exe = _touch(tmp_path / "SumatraPDF.exe")

    def run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(list(argv), 2, stderr="paper jam\ntray")

    result = PdfSumatraSubmit(exe, run=run).submit(
        SubmitRequest(item=_pdf_item(path), printer=None)
    )
    assert isinstance(result, SubmitFailed)
    assert result.reason == "SumatraPDF 打印失败：paper jam tray"


def test_sumatra_timeout_and_launch_error_fail_the_item(tmp_path: Path) -> None:
    path = _touch(tmp_path / "page.pdf")
    exe = _touch(tmp_path / "SumatraPDF.exe")
    item = _pdf_item(path)

    def time_out(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(list(argv), 120)

    timed = PdfSumatraSubmit(exe, run=time_out).submit(SubmitRequest(item=item, printer=None))
    assert isinstance(timed, SubmitFailed)
    assert timed.reason == "SumatraPDF 打印超时"

    def missing_exe(_argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        raise OSError(2, "The system cannot find the file specified")

    launched = PdfSumatraSubmit(exe, run=missing_exe).submit(SubmitRequest(item=item, printer=None))
    assert isinstance(launched, SubmitFailed)
    assert launched.reason.startswith("无法启动 SumatraPDF：")


def test_run_sumatra_process_returns_the_exit_code() -> None:
    completed = run_sumatra_process([sys.executable, "-c", "import sys; sys.exit(3)"])
    assert completed.returncode == 3


def test_find_sumatra_env_file_wins(tmp_path: Path) -> None:
    exe = _touch(tmp_path / "portable.exe")
    found = find_sumatra(environ={"PAPERFLICK_SUMATRA": str(exe)})
    assert found == exe


def test_find_sumatra_missing_env_does_not_fall_through(tmp_path: Path) -> None:
    real = _touch(tmp_path / "SumatraPDF" / "SumatraPDF.exe")
    missing = tmp_path / "missing.exe"
    found = find_sumatra(
        environ={
            "PAPERFLICK_SUMATRA": str(missing),
            "LOCALAPPDATA": str(tmp_path),
        },
        which=lambda _name: str(real),
    )
    assert found is None


def test_find_sumatra_localappdata_then_path(tmp_path: Path) -> None:
    exe = _touch(tmp_path / "SumatraPDF" / "SumatraPDF.exe")
    found = find_sumatra(
        environ={"LOCALAPPDATA": str(tmp_path)},
        which=lambda _name: None,
    )
    assert found == exe

    on_path = _touch(tmp_path / "from-path.exe")
    from_path = find_sumatra(
        environ={},
        candidates=(),
        which=lambda name: str(on_path) if name == "SumatraPDF" else None,
    )
    assert from_path == on_path


def test_dry_run_choice_does_not_call_the_runner(tmp_path: Path) -> None:
    exe = _touch(tmp_path / "SumatraPDF.exe")

    def run(_argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        raise AssertionError("Dry Run must not start SumatraPDF")

    port = choose_submit_port(_prefs(dry_run=True), executable=exe, run=run)
    assert isinstance(port, DryRunSubmit)
    path = _touch(tmp_path / "page.pdf")
    result = port.submit(SubmitRequest(item=_pdf_item(path), printer="HP Laser"))
    assert isinstance(result, SubmitOk)


def test_pdf_batch_respects_interval_orientation_and_continues(tmp_path: Path) -> None:
    wide = _write_pdf(tmp_path / "wide.pdf", 200, 100)
    tall = _write_pdf(tmp_path / "tall.pdf", 100, 200)
    docx = _touch(tmp_path / "note.docx")
    exe = _touch(tmp_path / "SumatraPDF.exe")
    argv_log: list[list[str]] = []

    def run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        argv_log.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 0)

    session = BatchSession(submit_factory=lambda _prefs: PdfSumatraSubmit(exe, run=run))
    session.apply(AddPaths([wide, docx, tall]))
    session.apply(StartBatch(_prefs(interval=1.0, printer="HP Laser")))
    clock = session.manual_clock
    assert clock is not None

    snap = session.snapshot()
    assert snap.success_count == 1
    assert snap.items[1].status is ItemStatus.WAITING
    assert len(argv_log) == 1
    assert argv_log[0][argv_log[0].index("-print-settings") + 1] == "landscape"
    assert argv_log[0][argv_log[0].index("-print-to") + 1] == "HP Laser"
    assert "-silent" in argv_log[0]

    assert clock.advance()
    snap = session.snapshot()
    assert snap.items[1].status is ItemStatus.FAILED
    assert snap.items[1].failure_reason == "该格式暂不支持打印"
    assert len(argv_log) == 1

    assert clock.advance()
    snap = session.snapshot()
    assert snap.phase is BatchPhase.IDLE
    assert snap.success_count == 2
    assert snap.failed_count == 1
    assert argv_log[1][argv_log[1].index("-print-settings") + 1] == "portrait"
    assert argv_log[1][-1] == str(tall)


def test_missing_sumatra_fails_each_pdf_without_stopping(tmp_path: Path) -> None:
    calls: list[Sequence[str]] = []

    def run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(list(argv), 0)

    session = BatchSession(submit_factory=lambda _prefs: PdfSumatraSubmit(None, run=run))
    session.apply(AddPaths([_touch(tmp_path / "a.pdf"), _touch(tmp_path / "b.pdf")]))
    session.apply(StartBatch(_prefs()))
    clock = session.manual_clock
    assert clock is not None
    assert session.snapshot().items[0].failure_reason == "未找到 SumatraPDF"
    assert session.snapshot().items[1].status is ItemStatus.WAITING
    assert clock.advance()
    snap = session.snapshot()
    assert snap.phase is BatchPhase.IDLE
    assert snap.failed_count == 2
    assert snap.success_count == 0
    assert snap.items[1].failure_reason == "未找到 SumatraPDF"
    assert calls == []


def test_sumatra_failure_does_not_stop_the_next_pdf(tmp_path: Path) -> None:
    codes = iter((1, 0))

    def run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        code = next(codes)
        stderr = "paper jam" if code else ""
        return subprocess.CompletedProcess(list(argv), code, stderr=stderr)

    exe = _touch(tmp_path / "SumatraPDF.exe")
    session = BatchSession(submit_factory=lambda _prefs: PdfSumatraSubmit(exe, run=run))
    session.apply(AddPaths([_touch(tmp_path / "a.pdf"), _touch(tmp_path / "b.pdf")]))
    session.apply(StartBatch(_prefs()))
    clock = session.manual_clock
    assert clock is not None
    assert session.snapshot().items[0].failure_reason == "SumatraPDF 打印失败：paper jam"
    assert clock.advance()
    snap = session.snapshot()
    assert snap.phase is BatchPhase.IDLE
    assert snap.items[0].status is ItemStatus.FAILED
    assert snap.items[1].status is ItemStatus.SUCCESS
    assert snap.items[1].failure_reason is None

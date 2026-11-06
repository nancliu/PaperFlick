"""DOCX Print Items use Word, then OnlyOffice, when Dry Run is off."""

from __future__ import annotations

import logging
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pytest

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
from paperflick.core.batch.types import Facing, Measured, PrintItem, Unread
from paperflick.core.submit import (
    DocxSubmit,
    DryRunSubmit,
    PrintSubmitPort,
    SubmitFailed,
    SubmitOk,
    SubmitRequest,
    SubmitResult,
    choose_submit_port,
)
from paperflick.core.submit.docx_print import (
    DOCX_ENGINE_ORDER,
    DocxJob,
    WordComPrinter,
    build_docx_submit,
    find_x2t,
    onlyoffice_engine,
    run_x2t_process,
    word_engine,
    x2t_params_xml,
)


def _prefs(
    *,
    dry_run: bool = False,
    interval: float = 1.0,
    printer: str | None = None,
) -> BatchPrefs:
    """One Batch preference snapshot."""
    return BatchPrefs(
        interval_seconds=interval,
        wait_for_empty_queue=False,
        dry_run=dry_run,
        selected_printer=printer,
    )


def _touch(path: Path) -> Path:
    """Create a readable file. Contents are not a real document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")
    return path


def _docx_item(
    path: Path,
    *,
    orientation: Orientation = Orientation.AUTO,
    shape: Measured | Unread | None = None,
) -> PrintItem:
    """A DOCX row with an explicit page fact."""
    item = PrintItem.added(path, Probe(DocKind.DOCX, shape or Measured(100, 200)))
    if orientation is Orientation.AUTO:
        return item
    return replace(item, orientation=orientation)


def _submit(port: DocxSubmit, item: PrintItem, printer: str | None) -> SubmitOk | SubmitFailed:
    """Submit one item through a DOCX port."""
    result = port.submit(SubmitRequest(item=item, printer=printer))
    assert isinstance(result, (SubmitOk, SubmitFailed))
    return result


class _Page:
    """Stand-in for Word's PageSetup."""

    def __init__(self) -> None:
        self.Orientation: int | None = None


class _Doc:
    """Stand-in for one open Word document."""

    def __init__(self) -> None:
        self.PageSetup = _Page()
        self.Saved = False
        self.events: list[tuple[str, object]] = []

    def PrintOut(self, Background: bool | None = None) -> None:
        self.events.append(("PrintOut", Background))

    def Close(self, save: int) -> None:
        self.events.append(("Close", save))


class _Docs:
    """Stand-in for Documents.Open."""

    def __init__(self, document: _Doc) -> None:
        self._document = document
        self.opened: tuple[object, ...] | None = None

    def Open(
        self,
        path: str,
        ConfirmConversions: bool | None = None,
        ReadOnly: bool | None = None,
        AddToRecentFiles: bool | None = None,
    ) -> _Doc:
        self.opened = (path, ConfirmConversions, ReadOnly, AddToRecentFiles)
        return self._document


class _WordBasic:
    """Stand-in for WordBasic.FilePrintSetup."""

    def __init__(self) -> None:
        self.setup: tuple[object, object] | None = None

    def FilePrintSetup(
        self,
        Printer: str | None = None,
        DoNotSetAsSysDefault: int | None = None,
    ) -> None:
        self.setup = (Printer, DoNotSetAsSysDefault)


class _App:
    """Stand-in for Word.Application."""

    def __init__(self, document: _Doc) -> None:
        self.Visible = True
        self.DisplayAlerts = 1
        self.Documents = _Docs(document)
        self.WordBasic = _WordBasic()
        self.quit = False

    def Quit(self) -> None:
        self.quit = True


class _BoomPrinter:
    """Word printer whose print raises and whose close must still run."""

    def __init__(self) -> None:
        self.closed = False

    def print_job(self, job: DocxJob) -> None:
        raise OSError(5, "access denied")

    def close(self) -> None:
        self.closed = True


def test_engine_order_constant_is_word_then_onlyoffice() -> None:
    """The product order is one tuple, not two booleans."""
    assert DOCX_ENGINE_ORDER == ("Word", "OnlyOffice")


def test_build_tries_word_before_onlyoffice(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The port builder attempts Word, then OnlyOffice, and stops on success."""
    seen: list[str] = []

    def word() -> object:
        def run(_job: DocxJob) -> SubmitResult:
            seen.append("Word")
            return SubmitFailed("未找到 Word")

        return run

    def onlyoffice(_x2t: object, *, sumatra: object, run_sumatra: object) -> object:
        def run(_job: DocxJob) -> SubmitResult:
            seen.append("OnlyOffice")
            return SubmitOk()

        return run

    monkeypatch.setattr("paperflick.core.submit.docx_print.word_engine", word)
    monkeypatch.setattr("paperflick.core.submit.docx_print.onlyoffice_engine", onlyoffice)
    monkeypatch.setattr("paperflick.core.submit.docx_print.find_x2t", lambda: None)
    path = _touch(tmp_path / "note.docx")
    result = build_docx_submit(None).submit(SubmitRequest(item=_docx_item(path), printer=None))
    assert isinstance(result, SubmitOk)
    assert seen == ["Word", "OnlyOffice"]


@pytest.mark.parametrize(
    ("orientation", "shape", "facing"),
    [
        (Orientation.AUTO, Measured(200, 100), Facing.LANDSCAPE),
        (Orientation.AUTO, Measured(100, 200), Facing.PORTRAIT),
        (Orientation.AUTO, Unread("unread"), Facing.PORTRAIT),
        (Orientation.LANDSCAPE, Measured(100, 200), Facing.LANDSCAPE),
        (Orientation.PORTRAIT, Measured(200, 100), Facing.PORTRAIT),
        (Orientation.PRINTER_DEFAULT, Measured(200, 100), None),
    ],
)
def test_docx_job_carries_the_resolved_facing(
    tmp_path: Path,
    orientation: Orientation,
    shape: Measured | Unread,
    facing: Facing | None,
) -> None:
    """The engine sees one facing. PrinterDefault arrives as None."""
    path = _touch(tmp_path / "note.docx")
    seen: list[DocxJob] = []

    def engine(job: DocxJob) -> SubmitResult:
        seen.append(job)
        return SubmitOk()

    result = _submit(
        DocxSubmit((("Word", engine),)),
        _docx_item(path, orientation=orientation, shape=shape),
        "HP Laser",
    )
    assert isinstance(result, SubmitOk)
    assert seen[0].facing is facing
    assert seen[0].printer == "HP Laser"
    assert seen[0].document == path


def test_word_success_does_not_call_onlyoffice(
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """A Word acceptance is the Print Job. The log names Word."""
    path = _touch(tmp_path / "note.docx")
    calls: list[str] = []

    def word(job: DocxJob) -> SubmitResult:
        calls.append("Word")
        return SubmitOk()

    def onlyoffice(_job: DocxJob) -> SubmitResult:
        calls.append("OnlyOffice")
        return SubmitOk()

    caplog.set_level(logging.INFO, logger="paperflick.submit.docx")
    result = _submit(
        DocxSubmit((("Word", word), ("OnlyOffice", onlyoffice))),
        _docx_item(path),
        None,
    )
    assert isinstance(result, SubmitOk)
    assert calls == ["Word"]
    assert any("engine=Word" in record.message for record in caplog.records)
    assert not any("engine=OnlyOffice" in record.message for record in caplog.records)


def test_word_failure_falls_back_and_names_onlyoffice(
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """Word's failure is logged, then OnlyOffice success is logged."""
    path = _touch(tmp_path / "note.docx")

    def word(_job: DocxJob) -> SubmitResult:
        return SubmitFailed("未找到 Word")

    def onlyoffice(_job: DocxJob) -> SubmitResult:
        return SubmitOk()

    caplog.set_level(logging.INFO, logger="paperflick.submit.docx")
    result = _submit(
        DocxSubmit((("Word", word), ("OnlyOffice", onlyoffice))),
        _docx_item(path),
        None,
    )
    assert isinstance(result, SubmitOk)
    warnings = [record.message for record in caplog.records if record.levelno >= logging.WARNING]
    infos = [record.message for record in caplog.records if record.levelno == logging.INFO]
    assert any("engine=Word" in message for message in warnings)
    assert any("engine=OnlyOffice" in message for message in infos)


def test_both_engines_fail_the_item(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    """Both names stay on the row when neither engine can print."""
    path = _touch(tmp_path / "note.docx")

    def word(_job: DocxJob) -> SubmitResult:
        return SubmitFailed("未找到 Word")

    def onlyoffice(_job: DocxJob) -> SubmitResult:
        return SubmitFailed("未找到 OnlyOffice")

    caplog.set_level(logging.INFO, logger="paperflick.submit.docx")
    result = _submit(
        DocxSubmit((("Word", word), ("OnlyOffice", onlyoffice))),
        _docx_item(path),
        None,
    )
    assert isinstance(result, SubmitFailed)
    assert "Word" in result.reason
    assert "OnlyOffice" in result.reason
    assert "未找到 Word" in result.reason
    assert "未找到 OnlyOffice" in result.reason
    assert not any(record.levelno == logging.INFO for record in caplog.records)


def test_missing_file_does_not_call_an_engine(tmp_path: Path) -> None:
    """Preflight fails the item before Word starts."""
    called = False

    def engine(_job: DocxJob) -> SubmitResult:
        nonlocal called
        called = True
        return SubmitOk()

    result = _submit(DocxSubmit((("Word", engine),)), _docx_item(tmp_path / "gone.docx"), None)
    assert isinstance(result, SubmitFailed)
    assert result.reason == "文件不存在"
    assert called is False


def test_non_docx_fails_without_an_engine(tmp_path: Path) -> None:
    """The DOCX port does not print a PDF."""
    path = _touch(tmp_path / "page.pdf")
    item = PrintItem.added(path, Probe(DocKind.PDF, Measured(100, 200)))
    called = False

    def engine(_job: DocxJob) -> SubmitResult:
        nonlocal called
        called = True
        return SubmitOk()

    result = _submit(DocxSubmit((("Word", engine),)), item, None)
    assert isinstance(result, SubmitFailed)
    assert result.reason == "该格式暂不支持打印"
    assert called is False


def test_word_com_sets_printer_and_landscape_then_quits(tmp_path: Path) -> None:
    """Word observes facing, a non-default printer, a foreground print, and a quit."""
    document = _Doc()
    app = _App(document)
    path = tmp_path / "wide.docx"
    printer = WordComPrinter(app)
    printer.print_job(DocxJob(document=path, printer="HP Laser", facing=Facing.LANDSCAPE))
    printer.close()
    assert app.Visible is False
    assert app.DisplayAlerts == 0
    assert app.Documents.opened == (str(path), False, False, False)
    assert app.WordBasic.setup == ("HP Laser", 1)
    assert document.PageSetup.Orientation == 1
    assert ("PrintOut", False) in document.events
    assert document.Saved is True
    assert ("Close", 0) in document.events
    assert app.quit is True


def test_word_com_leaves_printer_default_alone(tmp_path: Path) -> None:
    """No printer name and no facing means Word keeps its current defaults."""
    document = _Doc()
    app = _App(document)
    printer = WordComPrinter(app)
    printer.print_job(
        DocxJob(document=tmp_path / "note.docx", printer="  ", facing=None),
    )
    printer.close()
    assert app.WordBasic.setup is None
    assert document.PageSetup.Orientation is None


def test_word_engine_closes_after_a_print_error() -> None:
    """A Word print error still quits Word and becomes a failed attempt."""
    opened = _BoomPrinter()

    def open_printer() -> _BoomPrinter:
        return opened

    result = word_engine(open_printer)(DocxJob(Path("note.docx"), None, Facing.PORTRAIT))
    assert isinstance(result, SubmitFailed)
    assert result.reason.startswith("Word 打印失败")
    assert opened.closed is True


def test_x2t_xml_requests_pdf(tmp_path: Path) -> None:
    """The converter task names PDF format 513 and escapes the path."""
    source = tmp_path / "a&b.docx"
    xml = x2t_params_xml(source, tmp_path / "out.pdf", tmp_path / "fonts")
    assert "<m_nFormatTo>513</m_nFormatTo>" in xml
    assert "a&amp;b.docx" in xml
    assert "<m_sFontDir>" in xml


def test_onlyoffice_converts_then_prints_with_sumatra(tmp_path: Path) -> None:
    """A Word miss uses x2t, then Sumatra's landscape token, and names OnlyOffice."""
    document = _touch(tmp_path / "wide.docx")
    x2t = _touch(tmp_path / "converter" / "x2t.exe")
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    exe = _touch(tmp_path / "SumatraPDF.exe")
    sumatra_argv: list[list[str]] = []

    def convert(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        params = Path(argv[1])
        text = params.read_text(encoding="utf-8")
        assert "<m_nFormatTo>513</m_nFormatTo>" in text
        assert str(fonts) in text
        target = text.split("<m_sFileTo>")[1].split("</m_sFileTo>")[0]
        Path(target).write_bytes(b"%PDF")
        return subprocess.CompletedProcess(list(argv), 0)

    def print_pdf(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        sumatra_argv.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 0)

    engine = onlyoffice_engine(x2t, sumatra=exe, run_convert=convert, run_sumatra=print_pdf)
    result = engine(DocxJob(document=document, printer="HP Laser", facing=Facing.LANDSCAPE))
    assert isinstance(result, SubmitOk)
    assert len(sumatra_argv) == 1
    argv = sumatra_argv[0]
    assert argv[argv.index("-print-to") + 1] == "HP Laser"
    assert argv[argv.index("-print-settings") + 1] == "landscape"
    assert "-silent" in argv
    assert argv[-1].endswith("out.pdf")


def test_missing_x2t_does_not_convert(tmp_path: Path) -> None:
    """No converter means OnlyOffice is unavailable. Sumatra is not started."""
    called = False

    def convert(_argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        nonlocal called
        called = True
        return subprocess.CompletedProcess([], 0)

    engine = onlyoffice_engine(tmp_path / "missing.exe", run_convert=convert)
    result = engine(DocxJob(tmp_path / "note.docx", None, Facing.PORTRAIT))
    assert isinstance(result, SubmitFailed)
    assert result.reason == "未找到 OnlyOffice"
    assert called is False


def test_convert_failure_does_not_print(tmp_path: Path) -> None:
    """A bad x2t exit fails OnlyOffice before Sumatra."""
    x2t = _touch(tmp_path / "x2t.exe")
    printed = False

    def convert(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(list(argv), 2, stderr="bad document")

    def print_pdf(_argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        nonlocal printed
        printed = True
        return subprocess.CompletedProcess([], 0)

    engine = onlyoffice_engine(x2t, sumatra=x2t, run_convert=convert, run_sumatra=print_pdf)
    result = engine(DocxJob(_touch(tmp_path / "note.docx"), None, None))
    assert isinstance(result, SubmitFailed)
    assert result.reason == "OnlyOffice 转换失败：bad document"
    assert printed is False


def test_run_x2t_process_returns_the_exit_code() -> None:
    """The real converter runner waits for the process and keeps its exit code."""
    completed = run_x2t_process([sys.executable, "-c", "import sys; sys.exit(3)"])
    assert completed.returncode == 3


def test_find_x2t_env_file_wins_and_missing_does_not_fall_through(tmp_path: Path) -> None:
    """An explicit converter path is the only candidate, even when it is missing."""
    exe = _touch(tmp_path / "x2t.exe")
    assert find_x2t(environ={"PAPERFLICK_ONLYOFFICE": str(exe)}) == exe
    real = _touch(tmp_path / "ONLYOFFICE" / "DesktopEditors" / "converter" / "x2t.exe")
    missing = tmp_path / "gone.exe"
    found = find_x2t(
        environ={"PAPERFLICK_ONLYOFFICE": str(missing), "PROGRAMFILES": str(tmp_path)},
        which=lambda _name: str(real),
    )
    assert found is None


def test_find_x2t_program_files_then_path(tmp_path: Path) -> None:
    """A bundled converter wins before a name on PATH."""
    exe = _touch(tmp_path / "ONLYOFFICE" / "DesktopEditors" / "converter" / "x2t.exe")
    found = find_x2t(environ={"PROGRAMFILES": str(tmp_path)}, which=lambda _name: None)
    assert found == exe
    on_path = _touch(tmp_path / "from-path.exe")
    from_path = find_x2t(
        environ={},
        candidates=(),
        which=lambda name: str(on_path) if name == "x2t" else None,
    )
    assert from_path == on_path


def test_dry_run_does_not_call_docx_engines(tmp_path: Path) -> None:
    """Dry Run returns before Word or OnlyOffice."""

    def engine(_job: DocxJob) -> SubmitResult:
        raise AssertionError("Dry Run must not print DOCX")

    port = choose_submit_port(
        _prefs(dry_run=True),
        docx=DocxSubmit((("Word", engine),)),
    )
    assert isinstance(port, DryRunSubmit)
    path = _touch(tmp_path / "note.docx")
    result = port.submit(SubmitRequest(item=_docx_item(path), printer="HP Laser"))
    assert isinstance(result, SubmitOk)


def test_live_batch_prints_pdf_and_docx_and_continues_after_an_image(tmp_path: Path) -> None:
    """One port routes PDF to Sumatra and DOCX to Word. An image fails. The Batch ends."""
    pdf = _touch(tmp_path / "page.pdf")
    docx = _touch(tmp_path / "note.docx")
    image = _touch(tmp_path / "note.png")
    exe = _touch(tmp_path / "SumatraPDF.exe")
    sumatra_calls: list[list[str]] = []
    word_calls: list[Path] = []

    def run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        sumatra_calls.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 0)

    def word(job: DocxJob) -> SubmitResult:
        word_calls.append(job.document)
        return SubmitOk()

    def onlyoffice(_job: DocxJob) -> SubmitResult:
        raise AssertionError("Word succeeded")

    docx_port = DocxSubmit((("Word", word), ("OnlyOffice", onlyoffice)))

    def factory(prefs: BatchPrefs) -> PrintSubmitPort:
        return choose_submit_port(prefs, executable=exe, run=run, docx=docx_port)

    session = BatchSession(submit_factory=factory)
    session.apply(AddPaths([pdf, docx, image]))
    session.apply(StartBatch(_prefs(printer="HP Laser")))
    clock = session.manual_clock
    assert clock is not None
    assert session.snapshot().items[0].status is ItemStatus.SUCCESS
    assert clock.advance()
    assert session.snapshot().items[1].status is ItemStatus.SUCCESS
    assert clock.advance()
    snap = session.snapshot()
    assert snap.phase is BatchPhase.IDLE
    assert snap.success_count == 2
    assert snap.failed_count == 1
    assert snap.items[2].failure_reason is not None
    assert snap.items[2].failure_reason.startswith("图片无法打开")
    assert word_calls == [docx]
    assert len(sumatra_calls) == 1
    assert sumatra_calls[0][-1] == str(pdf)


def test_both_failures_do_not_stop_the_next_docx(tmp_path: Path) -> None:
    """The first DOCX can fail both engines and the next DOCX still prints."""
    first = _touch(tmp_path / "a.docx")
    second = _touch(tmp_path / "b.docx")
    seen: list[tuple[str, str]] = []

    def word(job: DocxJob) -> SubmitResult:
        seen.append(("Word", job.document.name))
        return SubmitFailed("未找到 Word")

    def onlyoffice(job: DocxJob) -> SubmitResult:
        seen.append(("OnlyOffice", job.document.name))
        if job.document.name == "b.docx":
            return SubmitOk()
        return SubmitFailed("未找到 OnlyOffice")

    docx_port = DocxSubmit((("Word", word), ("OnlyOffice", onlyoffice)))
    session = BatchSession(
        submit_factory=lambda _prefs: choose_submit_port(_prefs, docx=docx_port),
    )
    session.apply(AddPaths([first, second]))
    session.apply(StartBatch(_prefs()))
    clock = session.manual_clock
    assert clock is not None
    assert session.snapshot().items[0].status is ItemStatus.FAILED
    assert "Word" in (session.snapshot().items[0].failure_reason or "")
    assert "OnlyOffice" in (session.snapshot().items[0].failure_reason or "")
    assert clock.advance()
    snap = session.snapshot()
    assert snap.phase is BatchPhase.IDLE
    assert snap.items[0].status is ItemStatus.FAILED
    assert snap.items[1].status is ItemStatus.SUCCESS
    assert seen == [
        ("Word", "a.docx"),
        ("OnlyOffice", "a.docx"),
        ("Word", "b.docx"),
        ("OnlyOffice", "b.docx"),
    ]

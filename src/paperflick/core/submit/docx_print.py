"""DOCX Print Jobs: Word COM, then OnlyOffice conversion printed as PDF."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4
from xml.sax.saxutils import escape

from paperflick.core.batch.formats import DocKind
from paperflick.core.batch.types import (
    Facing,
    ItemId,
    ItemStatus,
    Orientation,
    PrintItem,
    Unread,
    resolve_facing,
)
from paperflick.core.submit.pdf_sumatra import PdfSumatraSubmit, SumatraRunner
from paperflick.core.submit.port import (
    REASON_UNSUPPORTED,
    SubmitFailed,
    SubmitOk,
    SubmitRequest,
    SubmitResult,
)
from paperflick.core.submit.preflight import preflight

_log = logging.getLogger("paperflick.submit.docx")

REASON_WORD_MISSING = "未找到 Word"
REASON_WORD_FAILED = "Word 打印失败"
REASON_ONLYOFFICE_MISSING = "未找到 OnlyOffice"
REASON_ONLYOFFICE_CONVERT = "OnlyOffice 转换失败"
REASON_ONLYOFFICE_TIMEOUT = "OnlyOffice 转换超时"
REASON_ONLYOFFICE_LAUNCH = "无法启动 OnlyOffice"
REASON_ONLYOFFICE_PRINT = "OnlyOffice 打印失败"

DOCX_ENGINE_ORDER = ("Word", "OnlyOffice")
X2T_TIMEOUT_SECONDS = 120
_X2T_PDF = 0x0201
_ENV_ONLYOFFICE = "PAPERFLICK_ONLYOFFICE"
_DETAIL_LIMIT = 120
_WD_DO_NOT_SAVE = 0
_WD_ALERTS_NONE = 0
_WD_PORTRAIT = 0
_WD_LANDSCAPE = 1

DocxEngine = Callable[["DocxJob"], SubmitResult]
Which = Callable[[str], str | None]
X2tRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class DocxJob:
    """One DOCX print after facing has been resolved.

    ``facing`` None leaves direction to the printer. ``printer`` None, or a
    blank name, prints to the Windows default printer.
    """

    document: Path
    printer: str | None
    facing: Facing | None


class WordPrinter(Protocol):
    """One Word process that can print a single document and then quit."""

    def print_job(self, job: DocxJob) -> None:
        """Print ``job``. Raise when Word cannot print it."""

    def close(self) -> None:
        """Quit Word. Discard in-memory page setup so the file is not rewritten."""


class WordComPrinter:
    """Drive one ``Word.Application`` instance created with ``DispatchEx``."""

    def __init__(self, app: Any) -> None:
        self._app = app
        self._document: Any = None

    def print_job(self, job: DocxJob) -> None:
        """Open, optionally force facing and printer, then print in the foreground."""
        app = self._app
        app.Visible = False
        app.DisplayAlerts = _WD_ALERTS_NONE
        document = app.Documents.Open(
            str(job.document),
            ConfirmConversions=False,
            ReadOnly=False,
            AddToRecentFiles=False,
        )
        self._document = document
        printer = job.printer.strip() if job.printer else ""
        if printer:
            app.WordBasic.FilePrintSetup(Printer=printer, DoNotSetAsSysDefault=1)
        orientation = _word_orientation(job.facing)
        if orientation is not None:
            document.PageSetup.Orientation = orientation
        document.PrintOut(Background=False)

    def close(self) -> None:
        """Mark the document saved so Word does not prompt, then discard it."""
        document = self._document
        app = self._app
        self._document = None
        if document is not None:
            document.Saved = True
            document.Close(_WD_DO_NOT_SAVE)
        app.Quit()


def open_word_printer() -> WordPrinter:
    """Start a separate Word process. ``DispatchEx`` avoids the user's open Word."""
    import win32com.client

    return WordComPrinter(win32com.client.DispatchEx("Word.Application"))


def word_engine(open_printer: Callable[[], WordPrinter] | None = None) -> DocxEngine:
    """Return an engine that prints with Word and always quits that process."""
    opener = open_word_printer if open_printer is None else open_printer

    def run(job: DocxJob) -> SubmitResult:
        try:
            printer = opener()
        except Exception as exc:
            return SubmitFailed(_with_detail(REASON_WORD_MISSING, exc))
        failed: SubmitFailed | None = None
        try:
            printer.print_job(job)
        except Exception as exc:
            failed = SubmitFailed(_with_detail(REASON_WORD_FAILED, exc))
        finally:
            _close_quietly(printer)
        if failed is not None:
            return failed
        return SubmitOk()

    return run


def find_x2t(
    *,
    environ: Mapping[str, str] | None = None,
    candidates: Sequence[Path] | None = None,
    which: Which | None = None,
) -> Path | None:
    """Return OnlyOffice ``x2t.exe``, or None when none can be used.

    ``PAPERFLICK_ONLYOFFICE`` wins. A set value that is not a file returns None
    and does not fall through to another install.
    """
    env = os.environ if environ is None else environ
    override = env.get(_ENV_ONLYOFFICE)
    if override is not None:
        path = Path(override)
        return path if path.is_file() else None

    search = _install_candidates(env) if candidates is None else candidates
    for path in search:
        if path.is_file():
            return path

    lookup = shutil.which if which is None else which
    for name in ("x2t", "x2t.exe"):
        found = lookup(name)
        if found is None:
            continue
        path = Path(found)
        if path.is_file():
            return path
    return None


def x2t_params_xml(source: Path, target: Path, font_dir: Path | None = None) -> str:
    """Return the x2t task XML that converts one document to PDF.

    ``513`` is ``AVS_OFFICESTUDIO_FILE_CROSSPLATFORM_PDF`` (0x0201).
    """
    body = (
        f"<m_sFileFrom>{escape(str(source))}</m_sFileFrom>"
        f"<m_sFileTo>{escape(str(target))}</m_sFileTo>"
        f"<m_nFormatTo>{_X2T_PDF}</m_nFormatTo>"
    )
    if font_dir is not None:
        body += f"<m_sFontDir>{escape(str(font_dir))}</m_sFontDir>"
    return (
        f'<?xml version="1.0" encoding="utf-8"?><TaskQueueDataConvert>{body}</TaskQueueDataConvert>'
    )


def run_x2t_process(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Spawn one x2t command and wait until it exits.

    ``TimeoutExpired`` and ``OSError`` propagate. The engine turns them into
    a Print Item failure.
    """
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(
        list(argv),
        capture_output=True,
        text=True,
        errors="replace",
        timeout=X2T_TIMEOUT_SECONDS,
        check=False,
        creationflags=flags,
    )


def onlyoffice_engine(
    x2t: Path | None,
    *,
    sumatra: Path | None = None,
    run_convert: X2tRunner | None = None,
    run_sumatra: SumatraRunner | None = None,
) -> DocxEngine:
    """Convert with x2t, then hand the PDF to the Sumatra submit port.

    Desktop Editors has no silent-print flag. x2t is the headless converter
    that ships beside it. The PDF port is the Print Job that actually spools.
    """
    runner = run_x2t_process if run_convert is None else run_convert

    def run(job: DocxJob) -> SubmitResult:
        executable = x2t
        if executable is None or not executable.is_file():
            return SubmitFailed(REASON_ONLYOFFICE_MISSING)
        with tempfile.TemporaryDirectory(prefix="paperflick-docx-") as folder:
            root = Path(folder)
            pdf = root / "out.pdf"
            params = root / "params.xml"
            font_dir = _font_dir(executable)
            params.write_text(
                x2t_params_xml(job.document, pdf, font_dir),
                encoding="utf-8",
            )
            try:
                completed = runner((str(executable), str(params)))
            except subprocess.TimeoutExpired:
                return SubmitFailed(REASON_ONLYOFFICE_TIMEOUT)
            except OSError as exc:
                return SubmitFailed(_with_detail(REASON_ONLYOFFICE_LAUNCH, exc))
            if completed.returncode != 0 or not pdf.is_file():
                detail = _clip(completed.stderr) or _clip(completed.stdout)
                return SubmitFailed(_with_detail(REASON_ONLYOFFICE_CONVERT, detail))
            printed = _print_with_sumatra(pdf, job, sumatra, run_sumatra)
            if isinstance(printed, SubmitFailed):
                return SubmitFailed(_with_detail(REASON_ONLYOFFICE_PRINT, printed.reason))
            return printed

    return run


def build_docx_submit(
    sumatra: Path | None,
    run_sumatra: SumatraRunner | None = None,
) -> DocxSubmit:
    """Word first, then OnlyOffice. Both share the Batch's Sumatra executable."""
    engines = {
        "Word": word_engine(),
        "OnlyOffice": onlyoffice_engine(find_x2t(), sumatra=sumatra, run_sumatra=run_sumatra),
    }
    return DocxSubmit(tuple((name, engines[name]) for name in DOCX_ENGINE_ORDER))


class DocxSubmit:
    """Submit a DOCX Print Item. Try each engine until one accepts the job."""

    def __init__(self, engines: Sequence[tuple[str, DocxEngine]]) -> None:
        self._engines = tuple(engines)
        if not self._engines:
            raise ValueError("DocxSubmit needs an engine")

    def submit(self, request: SubmitRequest) -> SubmitResult:
        """Preflight, then Word and later engines. A failure stays on this item."""
        failed = preflight(request)
        if failed is not None:
            return failed
        if request.item.kind is not DocKind.DOCX:
            return SubmitFailed(REASON_UNSUPPORTED)
        job = DocxJob(
            document=request.item.path,
            printer=request.printer,
            facing=resolve_facing(request.item.orientation, request.item.shape),
        )
        reasons: list[str] = []
        for name, engine in self._engines:
            result = _call_engine(name, engine, job)
            if isinstance(result, SubmitOk):
                _log.info("docx engine=%s path=%s", name, job.document)
                return result
            reasons.append(f"{name}：{result.reason}")
        return SubmitFailed(_clip("；".join(reasons)))


def _call_engine(name: str, engine: DocxEngine, job: DocxJob) -> SubmitResult:
    """Turn an engine crash into a failed attempt so the next engine can run."""
    try:
        result = engine(job)
    except Exception as exc:
        _log.warning("docx engine=%s failed reason=%s", name, exc)
        return SubmitFailed(_with_detail(f"{name} 打印失败", exc))
    if isinstance(result, SubmitOk):
        return result
    if isinstance(result, SubmitFailed):
        _log.warning("docx engine=%s failed reason=%s", name, result.reason)
        return result
    _log.warning("docx engine=%s failed reason=bad result", name)
    return SubmitFailed(f"{name} 打印失败")


def _print_with_sumatra(
    pdf: Path,
    job: DocxJob,
    sumatra: Path | None,
    run_sumatra: SumatraRunner | None,
) -> SubmitResult:
    """Spool a converted PDF with the same port PDF Print Items use."""
    item = PrintItem(
        id=ItemId(uuid4()),
        path=pdf,
        kind=DocKind.PDF,
        shape=Unread("converted"),
        orientation=_orientation_for_facing(job.facing),
        status=ItemStatus.PRINTING,
    )
    if run_sumatra is None:
        port = PdfSumatraSubmit(sumatra)
    else:
        port = PdfSumatraSubmit(sumatra, run=run_sumatra)
    return port.submit(SubmitRequest(item=item, printer=job.printer))


def _orientation_for_facing(facing: Facing | None) -> Orientation:
    """Map a resolved direction back to a policy the PDF port understands."""
    if facing is Facing.LANDSCAPE:
        return Orientation.LANDSCAPE
    if facing is Facing.PORTRAIT:
        return Orientation.PORTRAIT
    return Orientation.PRINTER_DEFAULT


def _word_orientation(facing: Facing | None) -> int | None:
    """Map facing to Word's wdOrientPortrait (0) or wdOrientLandscape (1)."""
    if facing is Facing.LANDSCAPE:
        return _WD_LANDSCAPE
    if facing is Facing.PORTRAIT:
        return _WD_PORTRAIT
    return None


def _font_dir(x2t: Path) -> Path | None:
    """OnlyOffice fonts live next to ``converter/`` when x2t is the bundled one."""
    fonts = x2t.parent.parent / "fonts"
    if fonts.is_dir():
        return fonts
    return None


def _install_candidates(environ: Mapping[str, str]) -> tuple[Path, ...]:
    """Well-known Desktop Editors locations for ``converter/x2t.exe``."""
    relative = Path("ONLYOFFICE") / "DesktopEditors" / "converter" / "x2t.exe"
    paths: list[Path] = []
    for key in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        root = environ.get(key)
        if root:
            paths.append(Path(root) / relative)
    local = environ.get("LOCALAPPDATA")
    if local:
        root = Path(local)
        paths.append(root / relative)
        paths.append(root / "Programs" / relative)
    return tuple(paths)


def _close_quietly(printer: WordPrinter) -> None:
    """Quit Word after a print error without hiding that error."""
    try:
        printer.close()
    except Exception as exc:
        _log.warning("docx engine=Word close failed reason=%s", exc)


def _with_detail(reason: str, detail: object | None = None) -> str:
    """Append a short detail when it adds something the reason does not say."""
    text = _detail_text(detail)
    if not text or text == reason:
        return reason
    return _clip(f"{reason}：{text}")


def _detail_text(detail: object | None) -> str:
    """Collapse an exception or a process snippet into one line."""
    if detail is None:
        return ""
    if isinstance(detail, BaseException):
        strerror = getattr(detail, "strerror", None)
        return _clip(strerror or str(detail))
    if isinstance(detail, str):
        return _clip(detail)
    return ""


def _clip(text: str | bytes | None) -> str:
    """Collapse whitespace and cap the length shown on a list row."""
    if text is None:
        return ""
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    return " ".join(text.split())[:_DETAIL_LIMIT]

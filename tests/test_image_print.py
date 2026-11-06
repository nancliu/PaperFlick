"""Image Print Items submit through Pillow and Windows when Dry Run is off."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image, ImageOps, ImageWin
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
from paperflick.core.batch.types import Facing, Measured, PrintItem, Unread
from paperflick.core.submit import (
    DryRunSubmit,
    SubmitFailed,
    SubmitOk,
    SubmitRequest,
    choose_submit_port,
)
from paperflick.core.submit.image_win import (
    ImageWinSubmit,
    PrinterNotFound,
    _close_printer_dc,
    _open_printer_dc,
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


def _write_png(
    path: Path,
    width: int,
    height: int,
    color: tuple[int, int, int] = (10, 20, 30),
) -> Path:
    Image.new("RGB", (width, height), color).save(path)
    return path


def _image_item(
    path: Path,
    *,
    orientation: Orientation = Orientation.AUTO,
    shape: Measured | Unread | None = None,
) -> PrintItem:
    item = PrintItem.added(path, Probe(DocKind.IMAGE, shape or Measured(20, 10)))
    if orientation is Orientation.AUTO:
        return item
    return replace(item, orientation=orientation)


class _Page:
    """Recording page. One area stands in for the printable rectangle."""

    def __init__(self, printer: str, opened: list[_Page]) -> None:
        self.printer = printer
        self.opened = opened
        self.facing: Facing | None = None
        self.title = ""
        self.box: tuple[int, int, int, int] | None = None
        self.mode = ""
        self.pixel: tuple[int, int, int] | None = None
        self.finished = False
        self.aborted = False

    def begin(self, title: str, facing: Facing | None) -> tuple[int, int, int, int]:
        self.title = title
        self.facing = facing
        self.opened.append(self)
        return (0, 0, 1000, 1000)

    def blit(self, image: Image.Image, box: tuple[int, int, int, int]) -> None:
        self.box = box
        self.mode = image.mode
        pixel = image.getpixel((0, 0))
        assert isinstance(pixel, tuple)
        self.pixel = (int(pixel[0]), int(pixel[1]), int(pixel[2]))

    def finish(self) -> None:
        self.finished = True

    def abort(self) -> None:
        self.aborted = True


def _factory(opened: list[_Page]) -> Callable[[str], _Page]:
    def devices(printer: str) -> _Page:
        return _Page(printer, opened)

    return devices


def _submit(
    item: PrintItem,
    *,
    printer: str | None,
    default: str = "Office",
) -> tuple[SubmitOk | SubmitFailed, list[_Page]]:
    opened: list[_Page] = []

    def default_printer() -> str:
        return default

    result = ImageWinSubmit(devices=_factory(opened), default_printer=default_printer).submit(
        SubmitRequest(item=item, printer=printer)
    )
    return result, opened


@pytest.mark.parametrize(
    ("orientation", "shape", "facing"),
    [
        (Orientation.AUTO, Measured(20, 10), Facing.LANDSCAPE),
        (Orientation.AUTO, Measured(10, 20), Facing.PORTRAIT),
        (Orientation.AUTO, Measured(10, 10), Facing.PORTRAIT),
        (Orientation.AUTO, Unread("unread"), Facing.PORTRAIT),
        (Orientation.LANDSCAPE, Measured(10, 20), Facing.LANDSCAPE),
        (Orientation.PORTRAIT, Measured(20, 10), Facing.PORTRAIT),
        (Orientation.PRINTER_DEFAULT, Measured(20, 10), None),
    ],
)
def test_orientation_is_passed_to_the_page(
    tmp_path: Path,
    orientation: Orientation,
    shape: Measured | Unread,
    facing: Facing | None,
) -> None:
    path = _write_png(tmp_path / "page.png", 20, 10)
    item = _image_item(path, orientation=orientation, shape=shape)
    result, opened = _submit(item, printer="HP Laser")
    assert isinstance(result, SubmitOk)
    assert len(opened) == 1
    page = opened[0]
    assert page.facing is facing
    assert page.printer == "HP Laser"
    assert page.title == "page.png"
    assert page.finished is True
    assert page.aborted is False
    assert page.mode == "RGB"


def test_wide_image_is_centered_on_the_page(tmp_path: Path) -> None:
    path = _write_png(tmp_path / "wide.png", 20, 10)
    item = _image_item(path, shape=Measured(20, 10))
    result, opened = _submit(item, printer="HP Laser")
    assert isinstance(result, SubmitOk)
    assert opened[0].box == (0, 250, 1000, 750)


def test_blank_printer_uses_the_default_name(tmp_path: Path) -> None:
    path = _write_png(tmp_path / "page.png", 20, 10)
    item = _image_item(path, orientation=Orientation.PRINTER_DEFAULT)
    result, opened = _submit(item, printer="  ", default="Front Desk")
    assert isinstance(result, SubmitOk)
    assert opened[0].printer == "Front Desk"
    assert opened[0].facing is None


def test_transparent_pixel_prints_on_white(tmp_path: Path) -> None:
    path = tmp_path / "clear.png"
    Image.new("RGBA", (2, 2), (255, 0, 0, 0)).save(path)
    result, opened = _submit(_image_item(path), printer="HP Laser")
    assert isinstance(result, SubmitOk)
    assert opened[0].pixel == (255, 255, 255)


def test_first_gif_frame_is_the_one_printed(tmp_path: Path) -> None:
    path = tmp_path / "anim.gif"
    frames = [
        Image.new("RGB", (2, 2), (1, 2, 3)),
        Image.new("RGB", (2, 2), (9, 9, 9)),
    ]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=100, loop=0)
    result, opened = _submit(_image_item(path, shape=Measured(2, 2)), printer="HP Laser")
    assert isinstance(result, SubmitOk)
    assert opened[0].pixel == (1, 2, 3)


def test_exif_orientation_is_not_applied(tmp_path: Path) -> None:
    path = tmp_path / "flip.png"
    image = Image.new("RGB", (2, 1), (255, 255, 255))
    image.putpixel((0, 0), (255, 0, 0))
    exif = Image.Exif()
    exif[0x0112] = 2
    image.save(path, exif=exif)
    with Image.open(path) as saved:
        assert saved.getexif().get(0x0112) == 2
        stored = saved.convert("RGB").getpixel((0, 0))
        transposed = ImageOps.exif_transpose(saved).convert("RGB").getpixel((0, 0))
    assert stored != transposed
    result, opened = _submit(_image_item(path, shape=Measured(2, 1)), printer="HP Laser")
    assert isinstance(result, SubmitOk)
    assert opened[0].pixel == stored


def test_missing_default_printer_records_a_reason(tmp_path: Path) -> None:
    path = _write_png(tmp_path / "page.png", 20, 10)
    opened: list[_Page] = []

    def default_printer() -> str:
        raise OSError("no default")

    result = ImageWinSubmit(devices=_factory(opened), default_printer=default_printer).submit(
        SubmitRequest(item=_image_item(path), printer=None)
    )
    assert isinstance(result, SubmitFailed)
    assert result.reason == "未找到打印机"
    assert opened == []


def test_unknown_printer_records_a_reason_without_raising(tmp_path: Path) -> None:
    path = _write_png(tmp_path / "page.png", 8, 8)
    result = ImageWinSubmit().submit(
        SubmitRequest(item=_image_item(path), printer="PaperFlick Missing Printer XYZ")
    )
    assert isinstance(result, SubmitFailed)
    assert result.reason == "未找到打印机：PaperFlick Missing Printer XYZ"


def test_page_open_failure_names_the_printer(tmp_path: Path) -> None:
    path = _write_png(tmp_path / "page.png", 8, 8)

    class _Broken:
        def begin(self, title: str, facing: Facing | None) -> tuple[int, int, int, int]:
            raise PrinterNotFound("HP Laser")

        def blit(self, image: Image.Image, box: tuple[int, int, int, int]) -> None:
            raise AssertionError("blit")

        def finish(self) -> None:
            raise AssertionError("finish")

        def abort(self) -> None:
            raise AssertionError("abort")

    result = ImageWinSubmit(devices=lambda _printer: _Broken()).submit(
        SubmitRequest(item=_image_item(path), printer="HP Laser")
    )
    assert isinstance(result, SubmitFailed)
    assert result.reason == "未找到打印机：HP Laser"


def test_draw_failure_aborts_the_page_and_records_a_reason(tmp_path: Path) -> None:
    path = _write_png(tmp_path / "page.png", 8, 8)
    opened: list[_Page] = []

    class _Boom(_Page):
        def blit(self, image: Image.Image, box: tuple[int, int, int, int]) -> None:
            raise RuntimeError("spooler offline")

    def devices(printer: str) -> _Boom:
        page = _Boom(printer, opened)
        return page

    result = ImageWinSubmit(devices=devices).submit(
        SubmitRequest(item=_image_item(path), printer="HP Laser")
    )
    assert isinstance(result, SubmitFailed)
    assert result.reason == "图片打印失败：spooler offline"
    assert opened[0].aborted is True
    assert opened[0].finished is False


def test_corrupt_image_records_a_reason_without_opening_a_printer(tmp_path: Path) -> None:
    path = tmp_path / "bad.png"
    path.write_bytes(b"not-a-png")
    opened: list[_Page] = []
    result = ImageWinSubmit(devices=_factory(opened)).submit(
        SubmitRequest(item=_image_item(path), printer="HP Laser")
    )
    assert isinstance(result, SubmitFailed)
    assert result.reason.startswith("图片无法打开")
    assert opened == []


def test_decode_value_error_fails_the_item_not_the_batch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "odd.png"
    Image.new("RGB", (10, 10), color=(1, 1, 1)).save(path)
    opened: list[_Page] = []

    def _boom(_path: object) -> object:
        raise ValueError("synthetic decode failure")

    monkeypatch.setattr("paperflick.core.submit.image_win.Image.open", _boom)
    result = ImageWinSubmit(devices=_factory(opened)).submit(
        SubmitRequest(item=_image_item(path), printer="HP Laser")
    )
    assert isinstance(result, SubmitFailed)
    assert result.reason.startswith("图片无法打开")
    assert "synthetic decode failure" in result.reason
    assert opened == []


def test_missing_file_fails_before_the_printer(tmp_path: Path) -> None:
    opened: list[_Page] = []
    result = ImageWinSubmit(devices=_factory(opened)).submit(
        SubmitRequest(item=_image_item(tmp_path / "gone.png"), printer="HP Laser")
    )
    assert isinstance(result, SubmitFailed)
    assert result.reason == "文件不存在"
    assert opened == []


def test_non_image_fails_without_a_printer(tmp_path: Path) -> None:
    path = tmp_path / "note.docx"
    path.write_bytes(b"x")
    item = PrintItem.added(path, Probe(DocKind.DOCX, Measured(10, 20)))
    opened: list[_Page] = []
    result = ImageWinSubmit(devices=_factory(opened)).submit(
        SubmitRequest(item=item, printer="HP Laser")
    )
    assert isinstance(result, SubmitFailed)
    assert result.reason == "该格式暂不支持打印"
    assert opened == []


def test_dry_run_does_not_open_a_page(tmp_path: Path) -> None:
    path = _write_png(tmp_path / "page.png", 20, 10)

    def devices(_printer: str) -> _Page:
        raise AssertionError("Dry Run must not open a printer")

    port = choose_submit_port(_prefs(dry_run=True), devices=devices)
    assert isinstance(port, DryRunSubmit)
    result = port.submit(SubmitRequest(item=_image_item(path), printer="HP Laser"))
    assert isinstance(result, SubmitOk)


def test_image_batch_records_failures_and_continues(tmp_path: Path) -> None:
    wide = _write_png(tmp_path / "wide.png", 20, 10)
    tall = _write_png(tmp_path / "tall.png", 10, 20)
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not-a-png")
    docx = tmp_path / "note.docx"
    docx.write_bytes(b"x")
    pdf = tmp_path / "page.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=100)
    with pdf.open("wb") as handle:
        writer.write(handle)
    exe = tmp_path / "SumatraPDF.exe"
    exe.write_bytes(b"MZ")
    opened: list[_Page] = []
    argv_log: list[list[str]] = []

    def run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        argv_log.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 0)

    session = BatchSession(
        submit_factory=lambda prefs: choose_submit_port(
            prefs,
            executable=exe,
            run=run,
            devices=_factory(opened),
        )
    )
    session.apply(AddPaths([wide, bad, docx, pdf, tall]))
    session.apply(StartBatch(_prefs(interval=1.0, printer="HP Laser")))
    clock = session.manual_clock
    assert clock is not None

    assert session.snapshot().items[0].status is ItemStatus.SUCCESS
    assert opened[0].facing is Facing.LANDSCAPE
    assert len(argv_log) == 0

    assert clock.advance()
    assert session.snapshot().items[1].failure_reason is not None
    assert session.snapshot().items[1].failure_reason.startswith("图片无法打开")
    assert len(opened) == 1

    assert clock.advance()
    assert session.snapshot().items[2].failure_reason == "该格式暂不支持打印"

    assert clock.advance()
    assert len(argv_log) == 1
    assert argv_log[0][argv_log[0].index("-print-settings") + 1] == "landscape"
    assert argv_log[0][argv_log[0].index("-print-to") + 1] == "HP Laser"

    assert clock.advance()
    snap = session.snapshot()
    assert snap.phase is BatchPhase.IDLE
    assert snap.success_count == 3
    assert snap.failed_count == 2
    assert snap.items[4].status is ItemStatus.SUCCESS
    assert opened[1].facing is Facing.PORTRAIT
    assert opened[1].title == "tall.png"


def test_sumatra_port_still_rejects_an_image(tmp_path: Path) -> None:
    path = _write_png(tmp_path / "page.png", 8, 8)
    exe = tmp_path / "SumatraPDF.exe"
    exe.write_bytes(b"MZ")
    called = False

    def run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        nonlocal called
        called = True
        return subprocess.CompletedProcess(list(argv), 0)

    result = PdfSumatraSubmit(exe, run=run).submit(
        SubmitRequest(item=_image_item(path), printer=None)
    )
    assert isinstance(result, SubmitFailed)
    assert result.reason == "该格式暂不支持打印"
    assert called is False


def _default_printer_name() -> str | None:
    try:
        import win32print
    except ImportError:
        return None
    try:
        return str(win32print.GetDefaultPrinter())
    except Exception:
        return None


def test_landscape_page_swaps_axes_and_keeps_the_saved_default() -> None:
    """Open two device contexts, draw one bitmap, and delete them.

    This does not call StartDoc, so the printer does not receive a job.
    """
    name = _default_printer_name()
    if name is None:
        pytest.skip("no default printer")
    import win32print

    handle = win32print.OpenPrinter(name)
    before = int(win32print.GetPrinter(handle, 2)["pDevMode"].Orientation)
    win32print.ClosePrinter(handle)

    portrait = _open_printer_dc(name, Facing.PORTRAIT)
    landscape = _open_printer_dc(name, Facing.LANDSCAPE)
    try:
        assert portrait.area[2] == landscape.area[3]
        assert portrait.area[3] == landscape.area[2]
        assert portrait.area[2] != portrait.area[3]
        left, top, _width, _height = portrait.area
        ImageWin.Dib(Image.new("RGB", (8, 8), (1, 2, 3))).draw(
            portrait.hdc,
            (left, top, left + 8, top + 8),
        )
    finally:
        _close_printer_dc(portrait)
        _close_printer_dc(landscape)

    handle = win32print.OpenPrinter(name)
    after = int(win32print.GetPrinter(handle, 2)["pDevMode"].Orientation)
    win32print.ClosePrinter(handle)
    assert after == before

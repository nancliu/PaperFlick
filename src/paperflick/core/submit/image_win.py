"""Image Print Jobs via Pillow and one Windows printer device context."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, assert_never

from PIL import Image
from PIL.Image import DecompressionBombError

from paperflick.core.batch.formats import DocKind
from paperflick.core.batch.types import Facing, resolve_facing
from paperflick.core.submit.port import (
    REASON_UNSUPPORTED,
    SubmitFailed,
    SubmitOk,
    SubmitRequest,
    SubmitResult,
)
from paperflick.core.submit.preflight import preflight

REASON_NO_PRINTER = "未找到打印机"
REASON_IMAGE_OPEN = "图片无法打开"
REASON_IMAGE_FAILED = "图片打印失败"
_DETAIL_LIMIT = 120


class PrinterNotFound(Exception):
    """The named printer, or the Windows default, cannot be opened."""

    def __init__(self, name: str | None) -> None:
        self.name = name
        super().__init__(name or "")


class PageDevice(Protocol):
    """One printer page. The area is left, top, width, height in device pixels."""

    def begin(self, title: str, facing: Facing | None) -> tuple[int, int, int, int]:
        """Start the page. ``facing`` None leaves the printer direction unchanged."""

    def blit(self, image: Image.Image, box: tuple[int, int, int, int]) -> None:
        """Draw ``image`` into ``box`` as left, top, right, bottom."""

    def finish(self) -> None:
        """Commit the page."""

    def abort(self) -> None:
        """Drop the page. Safe when the page never started."""


DeviceFactory = Callable[[str], PageDevice]


@dataclass(frozen=True, slots=True)
class _OpenDc:
    """A printer handle and a device context that has not started a document."""

    handle: object
    hdc: object
    area: tuple[int, int, int, int]


def fit_box(
    image_size: tuple[int, int],
    area: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    """Center ``image_size`` inside ``area`` and keep the image aspect.

    ``area`` is left, top, width, height. The result is left, top, right, bottom.
    """
    image_w, image_h = image_size
    left, top, width, height = area
    if image_w <= 0 or image_h <= 0 or width <= 0 or height <= 0:
        raise ValueError("image and printable area must be positive")
    scale = min(width / image_w, height / image_h)
    drawn_w = min(width, max(1, int(image_w * scale)))
    drawn_h = min(height, max(1, int(image_h * scale)))
    x = left + (width - drawn_w) // 2
    y = top + (height - drawn_h) // 2
    return (x, y, x + drawn_w, y + drawn_h)


def _rgb_sheet(path: Path) -> Image.Image:
    """Return the first frame as RGB on white.

    Stored pixels are printed. EXIF orientation is not applied.
    """
    with Image.open(path) as image:
        try:
            image.seek(0)
        except EOFError:
            pass
        rgba = image.convert("RGBA")
        sheet = Image.new("RGB", rgba.size, "white")
        sheet.paste(rgba, mask=rgba.getchannel("A"))
        return sheet


def paint_sheet(
    sheet: Image.Image,
    title: str,
    facing: Facing | None,
    device: PageDevice,
) -> None:
    """Fit one RGB sheet on a page. Abort the page when drawing fails."""
    area = device.begin(title, facing)
    try:
        device.blit(sheet, fit_box((sheet.width, sheet.height), area))
    except Exception:
        device.abort()
        raise
    else:
        device.finish()


def resolve_printer_name(requested: str | None, default: Callable[[], str]) -> str:
    """Return the requested printer, or ``default`` when the request is blank."""
    name = requested.strip() if isinstance(requested, str) else ""
    if name:
        return name
    try:
        found = default().strip()
    except PrinterNotFound:
        raise
    except Exception as exc:
        raise PrinterNotFound(None) from exc
    if not found:
        raise PrinterNotFound(None)
    return found


def _with_detail(prefix: str, detail: str) -> str:
    """Append a clipped detail, or return ``prefix`` when the detail is empty."""
    clipped = " ".join(detail.split())[:_DETAIL_LIMIT]
    if clipped:
        return f"{prefix}：{clipped}"
    return prefix


def _reason_for(exc: Exception) -> SubmitFailed:
    """Map a submit failure onto the row reason."""
    if isinstance(exc, PrinterNotFound):
        if exc.name:
            return SubmitFailed(_with_detail(REASON_NO_PRINTER, exc.name))
        return SubmitFailed(REASON_NO_PRINTER)
    return SubmitFailed(_with_detail(REASON_IMAGE_FAILED, str(exc)))


def windows_default_printer() -> str:
    """Return the Windows default printer name."""
    import win32print

    return str(win32print.GetDefaultPrinter())


def win_spool_device(printer: str) -> PageDevice:
    """Return a page device that prints to ``printer``."""
    return WinSpoolPage(printer)


class ImageWinSubmit:
    """Submit an image Print Item. Any other kind fails the item."""

    def __init__(
        self,
        *,
        devices: DeviceFactory | None = None,
        default_printer: Callable[[], str] | None = None,
    ) -> None:
        self._devices = win_spool_device if devices is None else devices
        self._default_printer = (
            windows_default_printer if default_printer is None else default_printer
        )

    def submit(self, request: SubmitRequest) -> SubmitResult:
        """Preflight, then one page. A bad file or printer fails this item only."""
        failed = preflight(request)
        if failed is not None:
            return failed
        if request.item.kind is not DocKind.IMAGE:
            return SubmitFailed(REASON_UNSUPPORTED)
        try:
            sheet = _rgb_sheet(request.item.path)
        except (OSError, DecompressionBombError) as exc:
            return SubmitFailed(_with_detail(REASON_IMAGE_OPEN, str(exc)))
        try:
            printer = resolve_printer_name(request.printer, self._default_printer)
            facing = resolve_facing(request.item.orientation, request.item.shape)
            paint_sheet(sheet, request.item.path.name, facing, self._devices(printer))
        except Exception as exc:
            return _reason_for(exc)
        return SubmitOk()


def _orientation_code(facing: Facing | None) -> int | None:
    """Map a direction to a DEVMODE orientation. None keeps the current one."""
    import win32con

    if facing is None:
        return None
    if facing is Facing.LANDSCAPE:
        return int(win32con.DMORIENT_LANDSCAPE)
    if facing is Facing.PORTRAIT:
        return int(win32con.DMORIENT_PORTRAIT)
    assert_never(facing)


def _job_devmode(handle: object, printer: str, orientation: int | None) -> object:
    """Return a DEVMODE for this job.

    A requested orientation is merged into a new DEVMODE. This does not call
    SetPrinter, so the saved printer default stays as it was. ``orientation``
    None reuses the printer's current DEVMODE without changing its fields.
    """
    import pywintypes
    import win32con
    import win32print

    if orientation is None:
        return win32print.GetPrinter(handle, 2)["pDevMode"]
    size = win32print.DocumentProperties(0, handle, printer, None, None, 0)
    extra = size - pywintypes.DEVMODEType().Size
    mode = pywintypes.DEVMODEType(extra)
    mode.Fields = mode.Fields | win32con.DM_ORIENTATION
    mode.Orientation = orientation
    win32print.DocumentProperties(
        0,
        handle,
        printer,
        mode,
        mode,
        win32con.DM_IN_BUFFER | win32con.DM_OUT_BUFFER,
    )
    return mode


def _printable_area(hdc: object) -> tuple[int, int, int, int]:
    """Return the printable rectangle as left, top, width, height."""
    import win32con
    import win32print

    return (
        int(win32print.GetDeviceCaps(hdc, win32con.PHYSICALOFFSETX)),
        int(win32print.GetDeviceCaps(hdc, win32con.PHYSICALOFFSETY)),
        int(win32print.GetDeviceCaps(hdc, win32con.HORZRES)),
        int(win32print.GetDeviceCaps(hdc, win32con.VERTRES)),
    )


def _open_printer_dc(printer: str, facing: Facing | None) -> _OpenDc:
    """Open a device context for one job. The caller closes it.

    This does not call StartDoc.
    """
    import pywintypes
    import win32gui
    import win32print

    try:
        handle = win32print.OpenPrinter(printer)
    except pywintypes.error as exc:
        raise PrinterNotFound(printer) from exc
    hdc = None
    try:
        mode = _job_devmode(handle, printer, _orientation_code(facing))
        info = win32print.GetPrinter(handle, 2)
        hdc = win32gui.CreateDC(info["pPrintProcessor"], printer, mode)
        area = _printable_area(hdc)
    except Exception:
        if hdc is not None:
            win32gui.DeleteDC(hdc)
        win32print.ClosePrinter(handle)
        raise
    return _OpenDc(handle=handle, hdc=hdc, area=area)


def _close_printer_dc(opened: _OpenDc) -> None:
    """Delete the device context and close the printer handle."""
    import win32gui
    import win32print

    win32gui.DeleteDC(opened.hdc)
    win32print.ClosePrinter(opened.handle)


class WinSpoolPage:
    """One Windows print job for a single image page."""

    def __init__(self, printer: str) -> None:
        self._printer = printer
        self._handle: object | None = None
        self._hdc: object | None = None
        self._started = False

    def begin(self, title: str, facing: Facing | None) -> tuple[int, int, int, int]:
        """Start one document page and return the printable area."""
        import win32print

        opened = _open_printer_dc(self._printer, facing)
        self._handle = opened.handle
        self._hdc = opened.hdc
        try:
            win32print.StartDoc(self._hdc, (title, None, None, 0))
            self._started = True
            win32print.StartPage(self._hdc)
        except Exception:
            self._release(abort=True)
            raise
        return opened.area

    def blit(self, image: Image.Image, box: tuple[int, int, int, int]) -> None:
        """Draw ``image`` through Pillow's Windows bitmap."""
        from PIL import ImageWin

        if self._hdc is None:
            raise RuntimeError("page is not open")
        ImageWin.Dib(image).draw(self._hdc, box)

    def finish(self) -> None:
        """End the document and release the device context."""
        self._release(abort=False)

    def abort(self) -> None:
        """Cancel the document when it started, then release the device context."""
        self._release(abort=True)

    def _release(self, *, abort: bool) -> None:
        """End or cancel the document, then drop the device context and handle."""
        import win32gui
        import win32print

        hdc = self._hdc
        handle = self._handle
        started = self._started
        self._hdc = None
        self._handle = None
        self._started = False
        try:
            if hdc is not None and started:
                if abort:
                    win32print.AbortDoc(hdc)
                else:
                    win32print.EndPage(hdc)
                    win32print.EndDoc(hdc)
        finally:
            if hdc is not None:
                win32gui.DeleteDC(hdc)
            if handle is not None:
                win32print.ClosePrinter(handle)

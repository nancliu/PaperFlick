"""Windows Shell first-page thumbnails for preview (DOCX/DOC)."""

from __future__ import annotations

import ctypes
from collections.abc import Callable
from ctypes import POINTER, byref, c_ubyte, c_ulong, c_void_p, cast, windll
from ctypes.wintypes import DWORD, HBITMAP, LONG, LPCWSTR, WORD
from pathlib import Path

from PIL import Image

ShellThumbnailPort = Callable[[Path], Image.Image | None]

_SIIGBF_THUMBNAILONLY = 0x08
_SIIGBF_BIGGERSIZEOK = 0x01
_REQUEST_SIZE = 360

_HRESULT = ctypes.c_long


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", DWORD),
        ("Data2", WORD),
        ("Data3", WORD),
        ("Data4", c_ubyte * 8),
    ]


class _SIZE(ctypes.Structure):
    _fields_ = [("cx", LONG), ("cy", LONG)]


# IID_IShellItemImageFactory = {bcc18b79-ba16-442f-80c4-8a59c30c463b}
_IID_FACTORY = _GUID(
    0xBCC18B79,
    0xBA16,
    0x442F,
    (c_ubyte * 8)(0x80, 0xC4, 0x8A, 0x59, 0xC3, 0x0C, 0x46, 0x3B),
)


def windows_shell_thumbnail(path: Path) -> Image.Image | None:
    """Return a Shell page thumbnail for ``path``, or None when unavailable.

    Uses ``SIIGBF_THUMBNAILONLY`` so a generic file icon is treated as failure.
    Never raises: COM / GDI / import problems become None.
    """
    try:
        return _extract_shell_thumbnail(path)
    except Exception:
        return None


def _extract_shell_thumbnail(path: Path) -> Image.Image | None:
    """Call IShellItemImageFactory::GetImage and convert the HBITMAP to RGB."""
    import win32ui

    absolute = Path(path).resolve()
    if not absolute.is_file():
        return None

    windll.ole32.CoInitialize(None)
    factory = c_void_p()
    create = windll.shell32.SHCreateItemFromParsingName
    create.argtypes = [LPCWSTR, c_void_p, POINTER(_GUID), POINTER(c_void_p)]
    create.restype = _HRESULT
    hr = create(str(absolute), None, byref(_IID_FACTORY), byref(factory))
    if hr != 0 or not factory.value:
        return None

    vtable = cast(cast(factory, POINTER(c_void_p))[0], POINTER(c_void_p))
    get_image = ctypes.WINFUNCTYPE(
        _HRESULT, c_void_p, _SIZE, ctypes.c_uint, POINTER(HBITMAP)
    )(vtable[3])
    release = ctypes.WINFUNCTYPE(c_ulong, c_void_p)(vtable[2])

    hbitmap = HBITMAP()
    flags = _SIIGBF_THUMBNAILONLY | _SIIGBF_BIGGERSIZEOK
    hr = get_image(factory, _SIZE(_REQUEST_SIZE, _REQUEST_SIZE), flags, byref(hbitmap))
    release(factory)
    if hr != 0 or not hbitmap.value:
        return None

    handle = int(hbitmap.value)
    try:
        bitmap = win32ui.CreateBitmapFromHandle(handle)
        info = bitmap.GetInfo()
        bits = bitmap.GetBitmapBits(True)
        width = int(info["bmWidth"])
        height = int(info["bmHeight"])
        if width < 1 or height < 1 or len(bits) < width * height * 4:
            return None
        return Image.frombuffer(
            "RGB",
            (width, height),
            bits,
            "raw",
            "BGRX",
            0,
            1,
        ).copy()
    finally:
        windll.gdi32.DeleteObject(c_void_p(handle))

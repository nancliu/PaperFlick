"""Format registry: classify a path and measure its first page."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from docx import Document
from PIL import Image
from pypdf import PdfReader

from paperflick.core.batch.types import Measured, Unread

_log = logging.getLogger("paperflick.formats")


class DocKind(StrEnum):
    """File kind. Values stay the historical kind strings."""

    PDF = "pdf"
    DOCX = "docx"
    IMAGE = "image"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Probe:
    """What intake learns about one path in one pass."""

    kind: DocKind
    shape: Measured | Unread


SizeReader = Callable[[Path], tuple[float, float]]


@dataclass(frozen=True, slots=True)
class _Format:
    """One suffix group and the reader that measures its first page."""

    kind: DocKind
    suffixes: frozenset[str]
    read_size: SizeReader


def _pdf_size(path: Path) -> tuple[float, float]:
    """Return page 0 mediabox width and height in PDF points.

    Product plan compares the mediabox axes as stored. ``/Rotate`` is ignored.
    """
    page = PdfReader(path).pages[0]
    box = page.mediabox
    return float(box.width), float(box.height)


def _docx_size(path: Path) -> tuple[float, float]:
    """Return the first section's page size in EMU.

    Word's orientation flag is advisory. The stored width and height are the fact.
    """
    section = Document(path).sections[0]
    width = section.page_width
    height = section.page_height
    if width is None or height is None:
        raise ValueError("section has no page size")
    return float(width), float(height)


def _image_size(path: Path) -> tuple[float, float]:
    """Return Pillow pixel size without applying EXIF display transforms."""
    with Image.open(path) as image:
        width, height = image.size
    return float(width), float(height)


_FORMATS: tuple[_Format, ...] = (
    _Format(DocKind.PDF, frozenset({".pdf"}), _pdf_size),
    _Format(DocKind.DOCX, frozenset({".docx", ".doc"}), _docx_size),
    _Format(
        DocKind.IMAGE,
        frozenset({".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".gif", ".webp"}),
        _image_size,
    ),
)

_BY_SUFFIX: dict[str, _Format] = {suffix: fmt for fmt in _FORMATS for suffix in fmt.suffixes}


def probe(path: Path) -> Probe:
    """Classify a path and measure its first page.

    Never raises. A missing file, an unknown suffix, a reader error, or a
    non-positive size becomes an unread shape and one warning log line.
    """
    fmt = _BY_SUFFIX.get(path.suffix.lower())
    if fmt is None:
        return _unread(DocKind.UNKNOWN, path, "unsupported suffix")
    try:
        width, height = fmt.read_size(path)
    except Exception as exc:
        return _unread(fmt.kind, path, f"{type(exc).__name__}: {exc}")
    if width <= 0 or height <= 0:
        return _unread(fmt.kind, path, "degenerate page size")
    return Probe(kind=fmt.kind, shape=Measured(width, height))


def _unread(kind: DocKind, path: Path, reason: str) -> Probe:
    """Log an unread first page once and return an unread probe."""
    _log.warning("page geometry unread for %s: %s", path, reason)
    return Probe(kind=kind, shape=Unread(reason))

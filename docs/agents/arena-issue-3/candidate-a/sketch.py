"""Candidate A sketch for issue #3. Module map, types, signatures. Not runnable product code.

Module map (all under src/paperflick/core/batch/ unless noted):
    types.py       + Facing, Measured, Unread, PageShape, resolve_facing, PrintItem.added
    formats.py     NEW. DocKind + the one format registry (suffixes + first-page reader) + probe()
    path_intake.py sniff_kind deleted; _append_file calls probe() and PrintItem.added()
    __init__.py    re-export Facing, PageShape, Measured, Unread, resolve_facing, DocKind
    ui/item_list.py  orientation_label(item) + row text
    pyproject.toml / environment.yml  + pypdf, pillow, python-docx
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, StrEnum
from pathlib import Path
from uuid import UUID

# ---------------------------------------------------------------------------
# types.py
# ---------------------------------------------------------------------------


class Orientation(Enum):
    """Page orientation policy for one Print Item. Unchanged from today."""

    AUTO = "auto"
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    PRINTER_DEFAULT = "printer_default"


class Facing(Enum):
    """A resolved page direction. Never a policy, so it cannot be assigned to PrintItem.orientation."""

    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"


@dataclass(frozen=True, slots=True)
class Measured:
    """First-page size as displayed, in any consistent unit (rotation and EXIF already applied).

    Invariant: width > 0 and height > 0. Enforced in formats.probe, trusted afterwards.
    """

    width: float
    height: float


@dataclass(frozen=True, slots=True)
class Unread:
    """The first page could not be measured. Auto resolves this to Portrait."""

    reason: str


PageShape = Measured | Unread


def resolve_facing(policy: Orientation, shape: PageShape) -> Facing | None:
    """The single rule turning policy + fact into a direction. None means defer to the printer.

    AUTO + Measured(w, h)  -> LANDSCAPE if w > h else PORTRAIT (square is Portrait)
    AUTO + Unread          -> PORTRAIT
    LANDSCAPE / PORTRAIT   -> that Facing, shape ignored
    PRINTER_DEFAULT        -> None
    """
    # TODO: match on policy, then on shape type. assert_never on both for exhaustiveness.
    raise NotImplementedError


class ItemStatus(Enum):
    """Unchanged."""

    WAITING = "waiting"
    PRINTING = "printing"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ItemId:
    """Unchanged."""

    value: UUID


@dataclass(frozen=True, slots=True)
class PrintItem:
    """One row in the Batch list.

    `orientation` is policy (user intent). `shape` is fact (read once at AddPaths).
    Neither is derived from the other, and the direction is never stored.
    """

    id: ItemId
    path: Path
    kind: DocKind
    shape: PageShape
    orientation: Orientation
    status: ItemStatus
    failure_reason: str | None = None

    @classmethod
    def added(cls, path: Path, probed: Probe) -> PrintItem:
        """The only constructor for a newly added row. AUTO + WAITING by construction.

        Deliberately has no orientation parameter so no prior bulk override can be threaded in.
        """
        # TODO: cls(id=ItemId(uuid4()), path=path, kind=probed.kind, shape=probed.shape,
        #           orientation=Orientation.AUTO, status=ItemStatus.WAITING)
        raise NotImplementedError


# ---------------------------------------------------------------------------
# formats.py
# ---------------------------------------------------------------------------

_log = logging.getLogger("paperflick.formats")


class DocKind(StrEnum):
    """Kind label. StrEnum keeps `item.kind == "pdf"` true for existing callers."""

    PDF = "pdf"
    DOCX = "docx"
    IMAGE = "image"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Probe:
    """What intake learns about one path in a single pass."""

    kind: DocKind
    shape: PageShape


SizeReader = Callable[[Path], tuple[float, float]]


@dataclass(frozen=True, slots=True)
class _Format:
    kind: DocKind
    suffixes: frozenset[str]
    read_size: SizeReader


def _pdf_size(path: Path) -> tuple[float, float]:
    # pypdf: PdfReader(path).pages[0]. Use mediabox width/height, then swap when
    # page.rotation % 180 == 90, because a rotated portrait mediabox prints landscape.
    raise NotImplementedError


def _docx_size(path: Path) -> tuple[float, float]:
    # python-docx: Document(path).sections[0].page_width / page_height (EMU).
    # section.orientation is advisory in Word; trust the dimensions.
    raise NotImplementedError


def _image_size(path: Path) -> tuple[float, float]:
    # Pillow: with Image.open(path) as im: size = im.size; swap for EXIF Orientation 5..8,
    # since phone photos store sensor-landscape pixels with a portrait EXIF tag.
    raise NotImplementedError


_FORMATS: tuple[_Format, ...] = (
    _Format(DocKind.PDF, frozenset({".pdf"}), _pdf_size),
    # .doc stays DOCX kind for printing; python-docx cannot open it, so it probes as Unread.
    _Format(DocKind.DOCX, frozenset({".docx", ".doc"}), _docx_size),
    _Format(
        DocKind.IMAGE,
        frozenset({".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".gif", ".webp"}),
        _image_size,
    ),
)

_BY_SUFFIX: dict[str, _Format] = {s: f for f in _FORMATS for s in f.suffixes}


def probe(path: Path) -> Probe:
    """Classify a path and measure its first page. Never raises.

    Boundary for untrusted files: any reader exception, a missing file, an unknown suffix,
    or a non-positive dimension becomes Unread(reason) plus one warning log line.
    """
    # TODO:
    #   fmt = _BY_SUFFIX.get(path.suffix.lower())
    #   if fmt is None: return _unread(DocKind.UNKNOWN, path, "unsupported suffix")
    #   try: w, h = fmt.read_size(path)
    #   except Exception as exc: return _unread(fmt.kind, path, f"{type(exc).__name__}: {exc}")
    #   if w <= 0 or h <= 0: return _unread(fmt.kind, path, "degenerate page size")
    #   return Probe(fmt.kind, Measured(w, h))
    raise NotImplementedError


def _unread(kind: DocKind, path: Path, reason: str) -> Probe:
    # TODO: _log.warning("orientation fallback to Portrait for %s: %s", path, reason)
    raise NotImplementedError


# ---------------------------------------------------------------------------
# path_intake.py (delta only)
# ---------------------------------------------------------------------------


def _append_file(path: Path, seen: set[Path], items: list[PrintItem]) -> None:
    # TODO: unchanged dedupe; then items.append(PrintItem.added(path, probe(path)))
    raise NotImplementedError


# ---------------------------------------------------------------------------
# ui/item_list.py (delta only)
# ---------------------------------------------------------------------------

_FACING_LABEL: dict[Facing, str] = {Facing.LANDSCAPE: "横向", Facing.PORTRAIT: "纵向"}


def orientation_label(item: PrintItem) -> str:
    """Row text for the Orientation column. Auto rows show the inferred direction."""
    # TODO:
    #   facing = resolve_facing(item.orientation, item.shape)
    #   AUTO            -> f"自动·{_FACING_LABEL[facing]}"
    #   PRINTER_DEFAULT -> "打印机"
    #   otherwise       -> _FACING_LABEL[facing]
    raise NotImplementedError

"""Issue 3 candidate B. Contract sketch, not runtime.

Module map:

    paperflick/core/batch/types.py
        PrintItem stays a policy record. No page-shape field.
        Orientation stays Auto, Landscape, Portrait, PrinterDefault.
    paperflick/core/batch/geometry.py
        PageShape, GeometryReading, read_first_page.
        Owns file parsing, the width rule, and the fallback log.
    paperflick/core/batch/path_intake.py
        sniff_kind stays. expand_paths is deleted in the same change.
        intake_paths returns Birth values. _mint is the only new-row constructor.
    paperflick/core/batch/rows.py
        StoredRow, BatchRows, ListRow, ExplicitPolicy, as_orientation.
        One ordered list of pairs. Not exported from package __init__.
    paperflick/core/batch/state.py
        BatchState.items is replaced by BatchState.rows.
        BatchSnapshot.items is replaced by BatchSnapshot.rows.
    paperflick/core/batch/reduce.py
        AddPaths calls intake_paths then BatchRows.append_births.
        Remove, clear, and stop call BatchRows methods. They do not assign items.
    paperflick/core/batch/session.py
        apply, snapshot, and subscribe stay the public entry.
        The tick calls BatchRows.put_status. It does not rebuild a row.
    paperflick/core/batch/__init__.py
        Export ListRow. PageShape, GeometryReading, Birth, BatchRows,
        ExplicitPolicy, and read_first_page stay unexported.
    paperflick/core/settings.py
        Unchanged. No Orientation field.
    paperflick/core/batch/prefs.py
        Unchanged. No Orientation field.

Dependencies to add when implementing, via mamba first:
    pypdf, python-docx, Pillow.

Invariants:
    A Birth carries a Print Item whose Orientation is Auto.
    PageShape member names and values do not construct an Orientation.
    There is no function from PageShape to Orientation.
    BatchRows has no default Orientation field.
    list_rows reads the reading, and does not read item.orientation.
    A failed geometry read returns portrait and logs once inside read_first_page.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal
from uuid import UUID


# ---------------------------------------------------------------------------
# types.py (existing). PrintItem deliberately has no geometry field.
# ---------------------------------------------------------------------------


class Orientation(Enum):
    """Page orientation policy for one Print Item."""

    AUTO = "auto"
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    PRINTER_DEFAULT = "printer_default"


class ItemStatus(Enum):
    """Lifecycle of one Print Item inside a Batch."""

    WAITING = "waiting"
    PRINTING = "printing"
    SUCCESS = "success"
    FAILED = "failed"


class BatchPhase(Enum):
    """Whether a Batch is idle or advancing."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


@dataclass(frozen=True, slots=True)
class ItemId:
    """Opaque id for one Print Item row."""

    value: UUID


@dataclass(frozen=True, slots=True)
class PrintItem:
    """Policy and lifecycle for one file. Page shape lives on StoredRow."""

    id: ItemId
    path: Path
    kind: str
    orientation: Orientation
    status: ItemStatus
    failure_reason: str | None = None


# ---------------------------------------------------------------------------
# geometry.py
# ---------------------------------------------------------------------------


class PageShape(Enum):
    """First-page geometry.

    Names and values are deliberately different from Orientation so
    Orientation[shape.name] and Orientation(shape.value) both fail.
    """

    PAGE_LANDSCAPE = "page_landscape"
    PAGE_PORTRAIT = "page_portrait"


@dataclass(frozen=True, slots=True)
class GeometryReading:
    """One completed read. fell_back is true only for the portrait fallback."""

    shape: PageShape
    fell_back: bool


GeometryLabel = Literal["横向", "纵向"]


def shape_from_size(width: float, height: float) -> PageShape:
    """Map a positive page size to a shape.

    Landscape only when width is strictly greater than height. A square is
    portrait because the product rule uses a strict greater-than.
    """
    # if width <= 0 or height <= 0: raise ValueError
    # if width > height: return PageShape.PAGE_LANDSCAPE
    # return PageShape.PAGE_PORTRAIT
    raise NotImplementedError


def _read_pdf(path: Path) -> tuple[float, float]:
    """Return page 0 mediabox width and height.

    Uses pypdf. Ignores the page Rotate entry. Whether Rotate should change
    the shape is an open product question, so the box axes stand alone.
    """
    raise NotImplementedError


def _read_docx(path: Path) -> tuple[float, float]:
    """Return the first section page_width and page_height.

    Uses python-docx. An empty section list raises. A legacy .doc sniffed as
    docx fails here and becomes the portrait fallback.
    """
    raise NotImplementedError


def _read_image(path: Path) -> tuple[float, float]:
    """Return Pillow size as width and height. Close the image before return."""
    raise NotImplementedError


_SIZE_READERS: dict[str, Callable[[Path], tuple[float, float]]] = {
    "pdf": _read_pdf,
    "docx": _read_docx,
    "image": _read_image,
}


def _portrait_fallback(path: Path, reason: str) -> GeometryReading:
    """Log one warning and return portrait.

    This is the only fallback constructor, so a success path does not log.
    """
    # log.warning("page geometry fell back to portrait path=%s reason=%s", path, reason)
    # return GeometryReading(PageShape.PAGE_PORTRAIT, fell_back=True)
    raise NotImplementedError


def read_first_page(path: Path, kind: str) -> GeometryReading:
    """Read the first-page shape for a sniffed kind.

    Any failure returns portrait. Callers always receive a GeometryReading.
    Catching a broad error is the product rule. Missing files, empty PDFs,
    and unreadable documents share one row outcome.
    """
    # reader = _SIZE_READERS.get(kind)
    # if reader is None:
    #     return _portrait_fallback(path, "unsupported-kind")
    # try:
    #     width, height = reader(path)
    #     shape = shape_from_size(width, height)
    # except Exception as exc:
    #     return _portrait_fallback(path, type(exc).__name__)
    # return GeometryReading(shape, fell_back=False)
    raise NotImplementedError


# ---------------------------------------------------------------------------
# path_intake.py
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Birth:
    """A new row waiting to be appended. No policy argument exists."""

    item: PrintItem
    reading: GeometryReading

    def __post_init__(self) -> None:
        """Require Auto, Waiting, and an empty failure reason."""
        # if self.item.orientation is not Orientation.AUTO: raise ValueError
        # if self.item.status is not ItemStatus.WAITING: raise ValueError
        # if self.item.failure_reason is not None: raise ValueError
        raise NotImplementedError


def intake_paths(paths: Sequence[Path]) -> tuple[Birth, ...]:
    """Expand files and folders into births.

    Dedupes by resolved path inside this call, matching today's expand_paths.
    The arguments are the paths from AddPaths. Stored rows and Settings stay
    outside this function.
    """
    # for each file from the existing walk:
    #     kind = sniff_kind(path)
    #     reading = read_first_page(path, kind)
    #     births.append(_mint(path, kind, reading))
    # return tuple(births)
    raise NotImplementedError


def _mint(path: Path, kind: str, reading: GeometryReading) -> Birth:
    """Build one Birth. Orientation is Auto here and in no other helper."""
    # item = PrintItem(
    #     id=ItemId(uuid4()),
    #     path=path,
    #     kind=kind,
    #     orientation=Orientation.AUTO,
    #     status=ItemStatus.WAITING,
    # )
    # return Birth(item, reading)
    raise NotImplementedError


# ---------------------------------------------------------------------------
# rows.py
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ListRow:
    """What the list widget binds. Orientation is not on this object."""

    id: ItemId
    name: str
    status: ItemStatus
    geometry_label: GeometryLabel


class ExplicitPolicy(Enum):
    """Issue 5 override payload. Auto is absent, so a bulk write cannot be a birth."""

    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    PRINTER_DEFAULT = "printer_default"


def as_orientation(policy: ExplicitPolicy) -> Orientation:
    """Map an override onto the stored Orientation enum.

    PageShape has no overload here. Birth does not call this function.
    """
    # return {
    #     ExplicitPolicy.LANDSCAPE: Orientation.LANDSCAPE,
    #     ExplicitPolicy.PORTRAIT: Orientation.PORTRAIT,
    #     ExplicitPolicy.PRINTER_DEFAULT: Orientation.PRINTER_DEFAULT,
    # }[policy]
    raise NotImplementedError


@dataclass(frozen=True, slots=True)
class StoredRow:
    """Private pair. The reading stays put when status or policy changes."""

    item: PrintItem
    reading: GeometryReading


class BatchRows:
    """Sole writer of the ordered row list.

    No default Orientation field. append_births does not read existing policy.
    """

    def __init__(self) -> None:
        """Start empty."""
        self._rows: list[StoredRow] = []

    def append_births(self, births: Sequence[Birth]) -> None:
        """Append births after the local list is fully built.

        Ignores Orientation values already in self._rows. A repeat of the same
        paths appends again, which matches today's AddPaths.
        """
        # stored = [StoredRow(birth.item, birth.reading) for birth in births]
        # self._rows.extend(stored)
        raise NotImplementedError

    def drop(self, item_ids: Sequence[ItemId]) -> bool:
        """Remove matching pairs. Return whether the list changed."""
        # Drop the StoredRow. Do not leave its reading behind.
        raise NotImplementedError

    def clear(self) -> bool:
        """Remove every pair. Return whether the list was non-empty."""
        raise NotImplementedError

    def put_status(
        self,
        index: int,
        status: ItemStatus,
        failure_reason: str | None,
    ) -> PrintItem:
        """Replace status at index. Keep id, path, orientation, and reading."""
        # item = replace(self._rows[index].item, status=status, failure_reason=...)
        # self._rows[index] = replace(self._rows[index], item=item)
        # return item
        raise NotImplementedError

    def override_policy(self, item_ids: Sequence[ItemId], policy: ExplicitPolicy) -> bool:
        """Issue 5 fills this body. Issue 3 leaves it unimplemented.

        Replace orientation on matching ids via as_orientation. Leave each
        reading in place. Store nothing on this instance.
        """
        raise NotImplementedError

    def items(self) -> tuple[PrintItem, ...]:
        """Return a tuple copy for counts and submit."""
        raise NotImplementedError

    def list_rows(self) -> tuple[ListRow, ...]:
        """Project labels from the reading only.

        item.orientation is unread. Issue 5 edits this method when an override
        should change the visible word. New files still enter through _mint.
        """
        # label = "横向" if reading.shape is PageShape.PAGE_LANDSCAPE else "纵向"
        # name = item.path.name or str(item.path)
        raise NotImplementedError


# ---------------------------------------------------------------------------
# state.py
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BatchPrefs:
    """Unchanged preference snapshot for one Start. No Orientation field."""

    interval_seconds: float
    wait_for_empty_queue: bool
    dry_run: bool
    selected_printer: str | None


@dataclass
class BatchState:
    """Authoritative batch document. Row edits go through BatchRows methods."""

    rows: BatchRows = field(default_factory=BatchRows)
    phase: BatchPhase = BatchPhase.IDLE
    prefs: BatchPrefs | None = None
    cursor: int = 0


@dataclass(frozen=True, slots=True)
class BatchSnapshot:
    """Read-only view. rows replaces items."""

    rows: tuple[ListRow, ...]
    phase: BatchPhase
    success_count: int
    failed_count: int
    waiting_count: int
    printing_count: int
    dry_run: bool


def snapshot_from(state: BatchState) -> BatchSnapshot:
    """Build the snapshot from BatchRows.list_rows and BatchRows.items."""
    # counts come from items(). labels come from list_rows(). No second read.
    raise NotImplementedError


# ---------------------------------------------------------------------------
# commands.py (existing AddPaths, shown to fix the field list)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddPaths:
    """Add files or folders. paths is the only field."""

    paths: Sequence[Path]


@dataclass(frozen=True, slots=True)
class ItemsChanged:
    """Placeholder for the existing event. The real union stays in events.py."""


# Name used by the reduce signatures. The real BatchEvent union is wider.
BatchEvent = ItemsChanged


# ---------------------------------------------------------------------------
# reduce.py (changed methods)
# ---------------------------------------------------------------------------


def _add_paths(state: BatchState, command: AddPaths) -> tuple[BatchState, list[BatchEvent]]:
    """Add births. File reads stay inside intake_paths, as the folder walk does today."""
    # births = intake_paths(command.paths)
    # if not births: return state, []
    # state.rows.append_births(births)
    # items = list(state.rows.items())
    # return state, [ItemsChanged(), _counts_event(items)]
    raise NotImplementedError


def _remove_items(state: BatchState, command: object) -> tuple[BatchState, list[BatchEvent]]:
    """Drop pairs through BatchRows.drop, then clamp cursor against the new length."""
    raise NotImplementedError


def _clear_items(state: BatchState) -> tuple[BatchState, list[BatchEvent]]:
    """Clear through BatchRows.clear and set cursor to 0."""
    raise NotImplementedError


def _stop(state: BatchState) -> tuple[BatchState, list[BatchEvent]]:
    """Return PRINTING rows to WAITING through put_status, then go IDLE."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# session.py (public entry unchanged in shape)
# ---------------------------------------------------------------------------


class BatchSession:
    """apply, snapshot, and subscribe stay the only UI entry."""

    def apply(self, command: object) -> None:
        """Apply one command. AddPaths still carries paths only."""
        raise NotImplementedError

    def snapshot(self) -> BatchSnapshot:
        """Return snapshot_from. The UI draws labels from this snapshot."""
        raise NotImplementedError

    def subscribe(self, listener: Callable[[object], None]) -> Callable[[], None]:
        """Register a listener. Returns unsubscribe."""
        raise NotImplementedError

    def _on_interval_tick(self) -> None:
        """Advance one item. Status writes go through BatchRows.put_status.

        SubmitRequest still receives the PrintItem. Dry Run still ignores
        Orientation. The tick calls put_status.
        """
        raise NotImplementedError

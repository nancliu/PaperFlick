"""Wave 1 type sketch: deep BatchSession + printer catalog.

Module map (planned package layout; this file is the contract, not importable runtime):

    paperflick/core/
      settings.py          # preferences only; + selected_printer (branch #4)
      printers.py          # list_installed_printers -> list[PrinterName] (branch #4)
      batch/
        __init__.py        # public re-exports only (Session, commands, events, snapshot)
        types.py           # PrintItem, ItemId, ItemStatus, Orientation, BatchPhase
        commands.py        # AddPaths, RemoveItems, ClearItems, Start/Pause/Resume/Stop
        events.py          # BatchEvent union
        prefs.py           # BatchPrefs snapshot for one Start
        state.py           # BatchState owned exclusively by the session
        reduce.py          # pure (state, command) -> (state, events); no I/O
        clock.py           # interval ticks; owned by session, not UI
        session.py         # BatchSession: apply / snapshot / subscribe
      submit/
        __init__.py        # PrintSubmitPort protocol
        dry_run.py         # DryRunSubmit: always succeeds without Print Job
        # real.py later    # Windows Print Job submitter (post wave 1)

Invariants encoded here:
- Settings never holds Print Item rows.
- Only BatchSession mutates BatchState.
- Dry Run vs real print diverges only behind PrintSubmitPort.submit.
- Start with dry_run=True does not require selected_printer.
- apply(command) is idempotent for duplicate Pause/Stop/Resume where already there.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Protocol, Sequence
from uuid import UUID


# ---------------------------------------------------------------------------
# Domain primitives (GLOSSARY)
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
    """Opaque id for one Print Item row. Brand raw UUID so callers cannot mix paths."""

    value: UUID


@dataclass(frozen=True, slots=True)
class PrinterName:
    """Installed printer display name. Parsed at the Windows boundary."""

    value: str


@dataclass(frozen=True, slots=True)
class PrintItem:
    """One row in the Batch list (GLOSSARY: Print Item)."""

    id: ItemId
    path: Path
    # File kind string for wave 1 UI (pdf/docx/image/unknown); handlers come later.
    kind: str
    orientation: Orientation
    status: ItemStatus
    failure_reason: str | None = None


# ---------------------------------------------------------------------------
# Settings preference extension (branch #4 write)
# ---------------------------------------------------------------------------


@dataclass
class Settings:
    """User preferences. Not list runtime state."""

    interval_seconds: float = 2.0
    wait_for_empty_queue: bool = False
    dry_run: bool = False
    selected_printer: str | None = None


def load() -> Settings:
    raise NotImplementedError


def save(settings: Settings) -> None:
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Printer catalog (branch #4)
# ---------------------------------------------------------------------------


def list_installed_printers() -> list[PrinterName]:
    """Enumerate installed printers. Parse win32 names into PrinterName; never leak win32 types."""
    # TODO: call win32print.EnumPrinters at the boundary; map to PrinterName
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Batch prefs snapshot (copied at Start; not a live Settings handle)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BatchPrefs:
    """Immutable prefs captured for one Batch run."""

    interval_seconds: float
    wait_for_empty_queue: bool
    dry_run: bool
    selected_printer: str | None

    @classmethod
    def from_settings(cls, settings: Settings) -> BatchPrefs:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Commands (user intent) and events (facts for UI)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddPaths:
    paths: Sequence[Path]


@dataclass(frozen=True, slots=True)
class RemoveItems:
    item_ids: Sequence[ItemId]


@dataclass(frozen=True, slots=True)
class ClearItems:
    pass


@dataclass(frozen=True, slots=True)
class StartBatch:
    prefs: BatchPrefs


@dataclass(frozen=True, slots=True)
class PauseBatch:
    pass


@dataclass(frozen=True, slots=True)
class ResumeBatch:
    pass


@dataclass(frozen=True, slots=True)
class StopBatch:
    pass


BatchCommand = (
    AddPaths
    | RemoveItems
    | ClearItems
    | StartBatch
    | PauseBatch
    | ResumeBatch
    | StopBatch
)


@dataclass(frozen=True, slots=True)
class ItemsChanged:
    """List membership or row fields changed; UI should rebind from snapshot."""


@dataclass(frozen=True, slots=True)
class ItemStatusChanged:
    item_id: ItemId
    status: ItemStatus
    failure_reason: str | None = None


@dataclass(frozen=True, slots=True)
class PhaseChanged:
    phase: BatchPhase


@dataclass(frozen=True, slots=True)
class CountsChanged:
    success: int
    failed: int
    waiting: int
    printing: int


BatchEvent = ItemsChanged | ItemStatusChanged | PhaseChanged | CountsChanged


# ---------------------------------------------------------------------------
# Owned state + snapshot (single writer: BatchSession)
# ---------------------------------------------------------------------------


@dataclass
class BatchState:
    """Authoritative Batch document. Only reduce() and Session tick mutate this."""

    items: list[PrintItem] = field(default_factory=list)
    phase: BatchPhase = BatchPhase.IDLE
    prefs: BatchPrefs | None = None
    # Index of the next Waiting item to claim; advanced only by the session clock.
    cursor: int = 0


@dataclass(frozen=True, slots=True)
class BatchSnapshot:
    """Read-only view for UI bind. Derived from BatchState; never mutated by callers."""

    items: tuple[PrintItem, ...]
    phase: BatchPhase
    success_count: int
    failed_count: int
    waiting_count: int
    printing_count: int
    dry_run: bool


def reduce(state: BatchState, command: BatchCommand) -> tuple[BatchState, list[BatchEvent]]:
    """Pure command application. No clock, no submit, no Settings I/O.

    Idempotency:
    - Pause while PAUSED / Stop while IDLE / Resume while RUNNING -> no-op, empty events.
    - Start while RUNNING or PAUSED -> rejected as no-op (or later a typed error event).
    - Remove of unknown ids -> no-op for missing ids.
    Failures during a Batch do not stop the Batch (GLOSSARY).
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Print Job submit boundary (Dry Run divert lives here only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SubmitRequest:
    """Intent to produce one Print Job for a Print Item."""

    item: PrintItem
    printer: str | None


@dataclass(frozen=True, slots=True)
class SubmitResult:
    ok: bool
    failure_reason: str | None = None


class PrintSubmitPort(Protocol):
    def submit(self, request: SubmitRequest) -> SubmitResult:
        """Boundary where Dry Run no-ops and real print would send a Print Job."""
        ...


class DryRunSubmit:
    """Always ok; never talks to a printer."""

    def submit(self, request: SubmitRequest) -> SubmitResult:
        raise NotImplementedError


def choose_submit_port(prefs: BatchPrefs) -> PrintSubmitPort:
    """Select submit implementation from prefs.dry_run. Wave 1: DryRunSubmit only path in tests."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Deep public API
# ---------------------------------------------------------------------------

EventListener = Callable[[BatchEvent], None]


class BatchSession:
    """Single deep facade for Print Item list + Batch lifecycle.

    Hides: reducer, cursor, interval clock, submit-port choice, status transitions.
    Exposes: apply / snapshot / subscribe.
    """

    def __init__(self, *, submit_factory: Callable[[BatchPrefs], PrintSubmitPort] | None = None) -> None:
        # TODO: own BatchState; wire clock to Tk/after or a testable Clock port
        raise NotImplementedError

    def subscribe(self, listener: EventListener) -> Callable[[], None]:
        """Register UI listener. Returns unsubscribe. Listener must not call apply re-entrantly."""
        raise NotImplementedError

    def snapshot(self) -> BatchSnapshot:
        raise NotImplementedError

    def apply(self, command: BatchCommand) -> None:
        """Apply a user command. May schedule clock work for Start/Resume.

        StartBatch:
        - copies prefs onto state
        - chooses PrintSubmitPort via dry_run
        - does not require selected_printer when dry_run is True
        - begins serial advancement Waiting -> Printing -> Success|Failed
        """
        raise NotImplementedError

    # --- session-private tick (not for UI import; shown for contract clarity) ---

    def _on_interval_tick(self) -> None:
        """Claim next Waiting item, call submit port, record status, schedule next tick.

        Divert only at submit(). Interval and pause/stop gate the tick, not the submitter.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# UI orchestration seams (signatures only; live in ui/, not core/)
# ---------------------------------------------------------------------------


class MainWindow:
    """Orchestrates widgets. Holds Settings + BatchSession. Does not own item mutations."""

    def __init__(self, settings: Settings | None = None) -> None:
        raise NotImplementedError

    def _on_add_files(self, paths: list[Path]) -> None:
        raise NotImplementedError

    def _on_start(self) -> None:
        raise NotImplementedError

    def _on_pause(self) -> None:
        raise NotImplementedError

    def _on_stop(self) -> None:
        raise NotImplementedError

    def _refresh_printer_sidebar(self) -> None:
        raise NotImplementedError

    def _on_printer_picked(self, name: str) -> None:
        raise NotImplementedError

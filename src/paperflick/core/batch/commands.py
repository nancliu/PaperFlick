"""User-intent commands for BatchSession.apply."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from paperflick.core.batch.prefs import BatchPrefs
from paperflick.core.batch.types import ItemId, Orientation


@dataclass(frozen=True, slots=True)
class AddPaths:
    """Add files or folders; session expands folders before reduce."""

    paths: Sequence[Path]


@dataclass(frozen=True, slots=True)
class RemoveItems:
    """Remove Print Items by id. Unknown ids are ignored."""

    item_ids: Sequence[ItemId]


@dataclass(frozen=True, slots=True)
class ClearItems:
    """Remove every Print Item from the list."""


@dataclass(frozen=True, slots=True)
class StartBatch:
    """Begin a Batch with an immutable prefs snapshot."""

    prefs: BatchPrefs


@dataclass(frozen=True, slots=True)
class PauseBatch:
    """Pause a RUNNING Batch."""


@dataclass(frozen=True, slots=True)
class ResumeBatch:
    """Resume a PAUSED Batch."""


@dataclass(frozen=True, slots=True)
class StopBatch:
    """Stop a Batch and return to IDLE."""


@dataclass(frozen=True, slots=True)
class ReprintFailed:
    """Reset every FAILED item to WAITING, then run ``start``. One reduce, all or nothing.

    No-op unless the Batch is IDLE and at least one item is FAILED.
    """

    start: StartBatch


@dataclass(frozen=True, slots=True)
class ClearSucceeded:
    """Remove SUCCESS rows. FAILED, WAITING, and PRINTING rows stay."""


class ApplyScope(Enum):
    """Which existing Print Items a preview orientation applies to."""

    THIS = "this"
    SAME_KIND = "same_kind"
    ALL = "all"


@dataclass(frozen=True, slots=True)
class SetOrientation:
    """Set one Orientation on a scope of existing Print Items.

    ``anchor`` is the previewed row. ``THIS`` updates that row. ``SAME_KIND``
    updates every row with the anchor's kind, including the anchor. Both no-op
    when the anchor is gone. ``ALL`` updates every current row and does not
    require the anchor to still exist.

    New rows stay Auto. ``PrintItem.added`` never reads this command.
    """

    anchor: ItemId
    orientation: Orientation
    scope: ApplyScope


BatchCommand = (
    AddPaths
    | RemoveItems
    | ClearItems
    | ClearSucceeded
    | SetOrientation
    | StartBatch
    | ReprintFailed
    | PauseBatch
    | ResumeBatch
    | StopBatch
)


def starting_batch(command: BatchCommand) -> StartBatch | None:
    """Return the StartBatch a command would run, if any."""
    if isinstance(command, StartBatch):
        return command
    if isinstance(command, ReprintFailed):
        return command.start
    return None

"""User-intent commands for BatchSession.apply."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from paperflick.core.batch.prefs import BatchPrefs
from paperflick.core.batch.types import ItemId


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


BatchCommand = (
    AddPaths
    | RemoveItems
    | ClearItems
    | ClearSucceeded
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

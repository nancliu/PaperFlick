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


BatchCommand = (
    AddPaths | RemoveItems | ClearItems | StartBatch | PauseBatch | ResumeBatch | StopBatch
)

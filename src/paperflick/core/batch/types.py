"""Domain primitives for Print Items and Batch lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from uuid import UUID


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
    """One row in the Batch list."""

    id: ItemId
    path: Path
    kind: str
    orientation: Orientation
    status: ItemStatus
    failure_reason: str | None = None

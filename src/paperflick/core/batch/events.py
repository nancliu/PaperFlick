"""Facts emitted after Batch state changes."""

from __future__ import annotations

from dataclasses import dataclass

from paperflick.core.batch.types import BatchPhase, ItemId, ItemStatus


@dataclass(frozen=True, slots=True)
class ItemsChanged:
    """List membership or row fields changed; UI should rebind from snapshot."""


@dataclass(frozen=True, slots=True)
class ItemStatusChanged:
    """One Print Item status (and optional failure reason) changed."""

    item_id: ItemId
    status: ItemStatus
    failure_reason: str | None = None


@dataclass(frozen=True, slots=True)
class PhaseChanged:
    """Batch phase changed."""

    phase: BatchPhase


@dataclass(frozen=True, slots=True)
class CountsChanged:
    """Aggregate status counts changed."""

    success: int
    failed: int
    waiting: int
    printing: int


BatchEvent = ItemsChanged | ItemStatusChanged | PhaseChanged | CountsChanged

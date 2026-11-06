"""Authoritative Batch document and read-only snapshot."""

from __future__ import annotations

from dataclasses import dataclass, field

from paperflick.core.batch.prefs import BatchPrefs
from paperflick.core.batch.types import BatchPhase, ItemId, ItemStatus, PrintItem


@dataclass
class BatchState:
    """Authoritative Batch document. Only reduce and Session tick mutate this."""

    items: list[PrintItem] = field(default_factory=list)
    phase: BatchPhase = BatchPhase.IDLE
    prefs: BatchPrefs | None = None
    cursor: int = 0


@dataclass(frozen=True, slots=True)
class BatchSnapshot:
    """Read-only view for UI bind. Never mutated by callers."""

    items: tuple[PrintItem, ...]
    phase: BatchPhase
    success_count: int
    failed_count: int
    waiting_count: int
    printing_count: int
    dry_run: bool

    def ids_with(self, status: ItemStatus) -> list[ItemId]:
        """Ids of items in ``status``, in list order."""
        return [item.id for item in self.items if item.status is status]


def count_statuses(items: list[PrintItem]) -> tuple[int, int, int, int]:
    """Return success, failed, waiting, printing counts."""
    success = failed = waiting = printing = 0
    for item in items:
        if item.status is ItemStatus.SUCCESS:
            success += 1
        elif item.status is ItemStatus.FAILED:
            failed += 1
        elif item.status is ItemStatus.WAITING:
            waiting += 1
        elif item.status is ItemStatus.PRINTING:
            printing += 1
    return success, failed, waiting, printing


def snapshot_from(state: BatchState) -> BatchSnapshot:
    """Derive a BatchSnapshot from BatchState."""
    success, failed, waiting, printing = count_statuses(state.items)
    dry_run = state.prefs.dry_run if state.prefs is not None else False
    return BatchSnapshot(
        items=tuple(state.items),
        phase=state.phase,
        success_count=success,
        failed_count=failed,
        waiting_count=waiting,
        printing_count=printing,
        dry_run=dry_run,
    )

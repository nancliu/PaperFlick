"""Pure command application. No clock, no submit, no Settings I/O."""

from __future__ import annotations

from dataclasses import replace

from paperflick.core.batch.commands import (
    AddPaths,
    BatchCommand,
    ClearItems,
    PauseBatch,
    RemoveItems,
    ResumeBatch,
    StartBatch,
    StopBatch,
)
from paperflick.core.batch.events import (
    BatchEvent,
    CountsChanged,
    ItemsChanged,
    PhaseChanged,
)
from paperflick.core.batch.path_intake import expand_paths
from paperflick.core.batch.state import BatchState, count_statuses
from paperflick.core.batch.types import BatchPhase, ItemStatus, PrintItem


def reduce(state: BatchState, command: BatchCommand) -> tuple[BatchState, list[BatchEvent]]:
    """Apply one command. Idempotent for duplicate Pause/Stop/Resume/Start."""
    if isinstance(command, AddPaths):
        return _add_paths(state, command)
    if isinstance(command, RemoveItems):
        return _remove_items(state, command)
    if isinstance(command, ClearItems):
        return _clear_items(state)
    if isinstance(command, StartBatch):
        return _start(state, command)
    if isinstance(command, PauseBatch):
        return _pause(state)
    if isinstance(command, ResumeBatch):
        return _resume(state)
    if isinstance(command, StopBatch):
        return _stop(state)
    return state, []


def _counts_event(items: list[PrintItem]) -> CountsChanged:
    success, failed, waiting, printing = count_statuses(items)
    return CountsChanged(
        success=success,
        failed=failed,
        waiting=waiting,
        printing=printing,
    )


def _add_paths(state: BatchState, command: AddPaths) -> tuple[BatchState, list[BatchEvent]]:
    new_items = expand_paths(command.paths)
    if not new_items:
        return state, []
    items = list(state.items) + new_items
    state.items = items
    return state, [ItemsChanged(), _counts_event(items)]


def _remove_items(state: BatchState, command: RemoveItems) -> tuple[BatchState, list[BatchEvent]]:
    remove_ids = {item_id.value for item_id in command.item_ids}
    if not remove_ids:
        return state, []
    kept = [item for item in state.items if item.id.value not in remove_ids]
    if len(kept) == len(state.items):
        return state, []
    state.items = kept
    if state.cursor > len(kept):
        state.cursor = len(kept)
    return state, [ItemsChanged(), _counts_event(kept)]


def _clear_items(state: BatchState) -> tuple[BatchState, list[BatchEvent]]:
    if not state.items:
        return state, []
    state.items = []
    state.cursor = 0
    return state, [ItemsChanged(), _counts_event([])]


def _start(state: BatchState, command: StartBatch) -> tuple[BatchState, list[BatchEvent]]:
    if state.phase in (BatchPhase.RUNNING, BatchPhase.PAUSED):
        return state, []
    state.prefs = command.prefs
    state.phase = BatchPhase.RUNNING
    state.cursor = 0
    return state, [PhaseChanged(BatchPhase.RUNNING), _counts_event(state.items)]


def _pause(state: BatchState) -> tuple[BatchState, list[BatchEvent]]:
    if state.phase is not BatchPhase.RUNNING:
        return state, []
    state.phase = BatchPhase.PAUSED
    return state, [PhaseChanged(BatchPhase.PAUSED)]


def _resume(state: BatchState) -> tuple[BatchState, list[BatchEvent]]:
    if state.phase is not BatchPhase.PAUSED:
        return state, []
    state.phase = BatchPhase.RUNNING
    return state, [PhaseChanged(BatchPhase.RUNNING)]


def _stop(state: BatchState) -> tuple[BatchState, list[BatchEvent]]:
    if state.phase is BatchPhase.IDLE:
        return state, []
    events: list[BatchEvent] = []
    items = list(state.items)
    changed = False
    for index, item in enumerate(items):
        if item.status is ItemStatus.PRINTING:
            items[index] = replace(item, status=ItemStatus.WAITING, failure_reason=None)
            changed = True
    state.items = items
    state.phase = BatchPhase.IDLE
    state.cursor = 0
    events.append(PhaseChanged(BatchPhase.IDLE))
    if changed:
        events.append(ItemsChanged())
        events.append(_counts_event(items))
    return state, events

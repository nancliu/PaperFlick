"""Pure command application. No clock, no submit, no Settings I/O."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import assert_never

from paperflick.core.batch.commands import (
    AddPaths,
    ApplyScope,
    BatchCommand,
    ClearItems,
    ClearSucceeded,
    PauseBatch,
    RemoveItems,
    ReprintFailed,
    ResumeBatch,
    SetOrientation,
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
from paperflick.core.batch.types import BatchPhase, ItemId, ItemStatus, PrintItem


def reduce(state: BatchState, command: BatchCommand) -> tuple[BatchState, list[BatchEvent]]:
    """Apply one command. Repeat Pause, Stop, Resume, Start, or SetOrientation is a no-op."""
    if isinstance(command, AddPaths):
        return _add_paths(state, command)
    if isinstance(command, RemoveItems):
        return _remove_items(state, command)
    if isinstance(command, ClearItems):
        return _clear_items(state)
    if isinstance(command, ClearSucceeded):
        return _clear_succeeded(state)
    if isinstance(command, SetOrientation):
        return _set_orientation(state, command)
    if isinstance(command, StartBatch):
        return _start(state, command)
    if isinstance(command, ReprintFailed):
        return _reprint_failed(state, command)
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
    return _retain(state, lambda item: item.id.value not in remove_ids)


def _clear_items(state: BatchState) -> tuple[BatchState, list[BatchEvent]]:
    return _retain(state, lambda _item: False)


def _clear_succeeded(state: BatchState) -> tuple[BatchState, list[BatchEvent]]:
    return _retain(state, lambda item: item.status is not ItemStatus.SUCCESS)


def _find_item(items: list[PrintItem], item_id: ItemId) -> PrintItem | None:
    """Return the row with ``item_id``, or None when the preview target is gone."""
    for item in items:
        if item.id == item_id:
            return item
    return None


def _in_orientation_scope(item: PrintItem, scope: ApplyScope, anchor: PrintItem | None) -> bool:
    """Whether ``item`` receives the preview orientation."""
    if scope is ApplyScope.ALL:
        return True
    if anchor is None:
        return False
    if scope is ApplyScope.THIS:
        return item.id == anchor.id
    if scope is ApplyScope.SAME_KIND:
        return item.kind == anchor.kind
    assert_never(scope)


def _set_orientation(
    state: BatchState, command: SetOrientation
) -> tuple[BatchState, list[BatchEvent]]:
    """Write ``command.orientation`` onto the scope. Unchanged rows emit nothing."""
    anchor = _find_item(state.items, command.anchor)
    items = list(state.items)
    changed = False
    for index, item in enumerate(items):
        if not _in_orientation_scope(item, command.scope, anchor):
            continue
        if item.orientation is command.orientation:
            continue
        items[index] = replace(item, orientation=command.orientation)
        changed = True
    if not changed:
        return state, []
    state.items = items
    return state, [ItemsChanged()]


def _retain(
    state: BatchState,
    keep: Callable[[PrintItem], bool],
) -> tuple[BatchState, list[BatchEvent]]:
    """Drop rows ``keep`` rejects and move the cursor with the kept prefix.

    The next cursor is how many kept rows sat strictly before the old cursor.
    Dropping a row before the cursor must not skip the next Waiting item.
    """
    kept: list[PrintItem] = []
    new_cursor = 0
    for index, item in enumerate(state.items):
        if keep(item):
            kept.append(item)
            if index < state.cursor:
                new_cursor += 1
    if len(kept) == len(state.items):
        return state, []
    state.items = kept
    state.cursor = new_cursor
    return state, [ItemsChanged(), _counts_event(kept)]


def _reprint_failed(
    state: BatchState, command: ReprintFailed
) -> tuple[BatchState, list[BatchEvent]]:
    """IDLE with at least one FAILED item: reset those rows, then start.

    A running Batch only walks forward, so a reset behind the cursor would be skipped.
    Zero FAILED items do not start a Batch the user did not ask for.
    """
    if state.phase is not BatchPhase.IDLE:
        return state, []
    items = list(state.items)
    reset = False
    for index, item in enumerate(items):
        if item.status is ItemStatus.FAILED:
            items[index] = replace(item, status=ItemStatus.WAITING, failure_reason=None)
            reset = True
    if not reset:
        return state, []
    state.items = items
    state, start_events = _start(state, command.start)
    return state, [ItemsChanged(), *start_events]


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

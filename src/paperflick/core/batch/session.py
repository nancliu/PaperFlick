"""BatchSession: single writer for Print Item list + Batch lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from paperflick.core.batch.clock import CancelAfter, ManualClock, ScheduleAfter
from paperflick.core.batch.commands import BatchCommand, starting_batch
from paperflick.core.batch.events import (
    BatchEvent,
    CountsChanged,
    ItemsChanged,
    ItemStatusChanged,
    PhaseChanged,
)
from paperflick.core.batch.prefs import BatchPrefs
from paperflick.core.batch.reduce import reduce
from paperflick.core.batch.state import BatchSnapshot, BatchState, count_statuses, snapshot_from
from paperflick.core.batch.types import BatchPhase, ItemStatus, PrintItem
from paperflick.core.submit import (
    PrintSubmitPort,
    StartNeedsDryRunError,
    SubmitFailed,
    SubmitOk,
    SubmitRequest,
    SubmitResult,
    choose_submit_port,
)

EventListener = Callable[[BatchEvent], None]


def _row_after_submit(
    item: PrintItem, result: SubmitResult
) -> tuple[PrintItem, ItemStatus, str | None]:
    """Map one port result onto the row that was just claimed."""
    if isinstance(result, SubmitOk):
        return (
            replace(item, status=ItemStatus.SUCCESS, failure_reason=None),
            ItemStatus.SUCCESS,
            None,
        )
    if isinstance(result, SubmitFailed):
        return (
            replace(item, status=ItemStatus.FAILED, failure_reason=result.reason),
            ItemStatus.FAILED,
            result.reason,
        )
    raise TypeError(f"Unexpected submit result: {type(result)!r}")


class BatchSession:
    """Deep facade: apply / snapshot / subscribe. Owns reduce, clock, submit port."""

    def __init__(
        self,
        *,
        submit_factory: Callable[[BatchPrefs], PrintSubmitPort] | None = None,
        schedule_after: ScheduleAfter | None = None,
        cancel_after: CancelAfter | None = None,
    ) -> None:
        self._state = BatchState()
        self._listeners: list[EventListener] = []
        self._submit_factory = submit_factory or choose_submit_port
        self._submitter: PrintSubmitPort | None = None
        self._tick_handle: Any = None
        self._manual: ManualClock | None = None
        if schedule_after is None or cancel_after is None:
            self._manual = ManualClock()
            self._schedule_after = self._manual.schedule
            self._cancel_after = self._manual.cancel
        else:
            self._schedule_after = schedule_after
            self._cancel_after = cancel_after

    @property
    def manual_clock(self) -> ManualClock | None:
        """Test hook when no external scheduler was injected."""
        return self._manual

    def subscribe(self, listener: EventListener) -> Callable[[], None]:
        """Register UI listener. Returns unsubscribe. Do not call apply re-entrantly."""
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    def snapshot(self) -> BatchSnapshot:
        """Read-only view of current Batch state."""
        return snapshot_from(self._state)

    def apply(self, command: BatchCommand) -> None:
        """Apply a user command. May schedule clock work for Start/Resume."""
        start = starting_batch(command)
        if start is not None and not start.prefs.dry_run:
            raise StartNeedsDryRunError(
                "Enable Dry Run before Start. Real print is not available yet."
            )

        was_idle = self._state.phase is BatchPhase.IDLE
        events: list[BatchEvent]
        self._state, events = reduce(self._state, command)
        self._emit_all(events)

        if was_idle and self._state.phase is BatchPhase.RUNNING:
            prefs = self._state.prefs
            assert prefs is not None
            self._submitter = self._submit_factory(prefs)
            self._cancel_pending_tick()
            # First item advances immediately; later items wait for the interval.
            self._on_interval_tick()
        elif self._state.phase is BatchPhase.PAUSED:
            self._cancel_pending_tick()
        elif self._state.phase is BatchPhase.IDLE:
            self._cancel_pending_tick()
            self._submitter = None
        elif self._state.phase is BatchPhase.RUNNING and self._tick_handle is None:
            self._schedule_next_tick()

    def _emit_all(self, events: list[BatchEvent]) -> None:
        for event in events:
            for listener in list(self._listeners):
                listener(event)

    def _cancel_pending_tick(self) -> None:
        if self._tick_handle is not None:
            self._cancel_after(self._tick_handle)
            self._tick_handle = None

    def _schedule_next_tick(self) -> None:
        prefs = self._state.prefs
        if prefs is None:
            return
        self._cancel_pending_tick()
        delay = max(0.0, prefs.interval_seconds)
        self._tick_handle = self._schedule_after(delay, self._on_interval_tick)

    def _on_interval_tick(self) -> None:
        """Claim next Waiting item, submit, record status, schedule next tick."""
        self._tick_handle = None
        if self._state.phase is not BatchPhase.RUNNING:
            return
        prefs = self._state.prefs
        submitter = self._submitter
        if prefs is None or submitter is None:
            return

        index = self._find_next_waiting(self._state.cursor)
        if index is None:
            self._finish_batch()
            return

        item = self._state.items[index]
        printing = replace(item, status=ItemStatus.PRINTING, failure_reason=None)
        self._state.items[index] = printing
        self._state.cursor = index + 1
        self._emit_all(
            [
                ItemStatusChanged(item.id, ItemStatus.PRINTING),
                ItemsChanged(),
                self._counts_event(),
            ]
        )

        # wait_for_empty_queue is a no-op under Dry Run (preference still persisted).
        result = submitter.submit(SubmitRequest(item=printing, printer=prefs.selected_printer))
        final, status, reason = _row_after_submit(printing, result)
        self._state.items[index] = final
        self._emit_all(
            [
                ItemStatusChanged(item.id, status, reason),
                ItemsChanged(),
                self._counts_event(),
            ]
        )

        if self._state.phase is not BatchPhase.RUNNING:
            return
        if self._find_next_waiting(self._state.cursor) is None:
            self._finish_batch()
            return
        self._schedule_next_tick()

    def _find_next_waiting(self, start: int) -> int | None:
        items = self._state.items
        for index in range(start, len(items)):
            if items[index].status is ItemStatus.WAITING:
                return index
        return None

    def _finish_batch(self) -> None:
        self._cancel_pending_tick()
        if self._state.phase is BatchPhase.IDLE:
            return
        self._state.phase = BatchPhase.IDLE
        self._submitter = None
        self._emit_all([PhaseChanged(BatchPhase.IDLE)])

    def _counts_event(self) -> CountsChanged:
        success, failed, waiting, printing = count_statuses(self._state.items)
        return CountsChanged(
            success=success,
            failed=failed,
            waiting=waiting,
            printing=printing,
        )

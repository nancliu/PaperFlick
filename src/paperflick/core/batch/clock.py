"""Injectable interval scheduler owned by BatchSession."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol


class ScheduleAfter(Protocol):
    """Schedule ``callback`` after ``delay_seconds``. Return a cancel handle."""

    def __call__(self, delay_seconds: float, callback: Callable[[], None]) -> Any: ...


class CancelAfter(Protocol):
    """Cancel a handle returned by ScheduleAfter."""

    def __call__(self, handle: Any) -> None: ...


@dataclass
class ManualClock:
    """Deterministic clock for tests. Call ``advance`` to fire due callbacks."""

    _pending: list[tuple[float, Callable[[], None], int]] = field(default_factory=list)
    _next_id: int = 0
    _cancelled: set[int] = field(default_factory=set)

    def schedule(self, delay_seconds: float, callback: Callable[[], None]) -> int:
        handle = self._next_id
        self._next_id += 1
        self._pending.append((delay_seconds, callback, handle))
        return handle

    def cancel(self, handle: int) -> None:
        self._cancelled.add(handle)

    def advance(self) -> bool:
        """Fire the next non-cancelled callback. Returns False when empty."""
        while self._pending:
            _delay, callback, handle = self._pending.pop(0)
            if handle in self._cancelled:
                self._cancelled.discard(handle)
                continue
            callback()
            return True
        return False

    def drain(self, limit: int = 10_000) -> int:
        """Advance until empty or ``limit`` firings. Returns how many ran."""
        count = 0
        while count < limit and self.advance():
            count += 1
        return count

"""Print Job submit port types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from paperflick.core.batch.types import PrintItem


@dataclass(frozen=True, slots=True)
class SubmitRequest:
    """Intent to produce one Print Job for a Print Item."""

    item: PrintItem
    printer: str | None


@dataclass(frozen=True, slots=True)
class SubmitResult:
    """Outcome of one submit attempt."""

    ok: bool
    failure_reason: str | None = None


class PrintSubmitPort(Protocol):
    """Boundary where Dry Run no-ops and real print would send a Print Job."""

    def submit(self, request: SubmitRequest) -> SubmitResult:
        """Submit one Print Item. Dry Run always returns ok without OS print."""
        ...

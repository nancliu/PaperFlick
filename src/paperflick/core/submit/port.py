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
class SubmitOk:
    """The Print Job was handed off, or Dry Run would have handed it off."""


@dataclass(frozen=True, slots=True)
class SubmitFailed:
    """The Print Item could not be submitted. ``reason`` is shown on the list row."""

    reason: str

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("SubmitFailed requires a reason")


SubmitResult = SubmitOk | SubmitFailed


class PrintSubmitPort(Protocol):
    """Boundary where Dry Run no-ops and real print would send a Print Job."""

    def submit(self, request: SubmitRequest) -> SubmitResult:
        """Submit one Print Item. Return SubmitOk or SubmitFailed."""
        ...

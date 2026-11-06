"""This-run handoff counts."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import assert_never

from paperflick.core.batch.types import ItemStatus, PrintItem
from paperflick.core.submit.port import SubmitFailed, SubmitOk, SubmitResult


@dataclass(frozen=True, slots=True)
class RunLedger:
    """Handoffs since the last transition into RUNNING.

    Rows that were already SUCCESS when Start ran stay out. Removing a
    SUCCESS row later does not decrement these counts.
    """

    success: int = 0
    failed: int = 0

    def __post_init__(self) -> None:
        if self.success < 0 or self.failed < 0:
            raise ValueError("run ledger counts must be non-negative")


def apply_handoff(
    item: PrintItem,
    ledger: RunLedger,
    result: SubmitResult,
) -> tuple[PrintItem, RunLedger]:
    """Write one submit result onto the row and the ledger."""
    if isinstance(result, SubmitOk):
        updated = replace(item, status=ItemStatus.SUCCESS, failure_reason=None)
        return updated, RunLedger(ledger.success + 1, ledger.failed)
    if isinstance(result, SubmitFailed):
        updated = replace(item, status=ItemStatus.FAILED, failure_reason=result.reason)
        return updated, RunLedger(ledger.success, ledger.failed + 1)
    assert_never(result)

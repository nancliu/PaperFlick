"""Whether the next print item may be submitted."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, assert_never

from paperflick.core.batch.prefs import BatchPrefs
from paperflick.core.printers import ProbeFailed, SpoolerCount


class SpoolerProbe(Protocol):
    def __call__(self, printer: str | None) -> SpoolerCount | ProbeFailed:
        """Count jobs for ``printer``. ``None`` selects the default printer."""


@dataclass(frozen=True, slots=True)
class SubmitNext:
    pass


@dataclass(frozen=True, slots=True)
class WaitInterval:
    """Schedule the same interval again. Leave phase and rows alone."""


GateDecision = SubmitNext | WaitInterval


def gate_decision(prefs: BatchPrefs, probe: SpoolerProbe) -> GateDecision:
    """Return the next decision. Dry Run does not call the probe."""
    if prefs.dry_run or not prefs.wait_for_empty_queue:
        return SubmitNext()
    observed = probe(prefs.selected_printer)
    if isinstance(observed, SpoolerCount) and observed.jobs == 0:
        return SubmitNext()
    if isinstance(observed, (SpoolerCount, ProbeFailed)):
        return WaitInterval()
    assert_never(observed)

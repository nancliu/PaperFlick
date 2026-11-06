"""Dry Run submitter: always ok, never talks to a printer."""

from __future__ import annotations

from paperflick.core.batch.prefs import BatchPrefs
from paperflick.core.submit.port import PrintSubmitPort, SubmitRequest, SubmitResult


class DryRunSubmit:
    """Always succeeds without opening a Print Job."""

    def submit(self, request: SubmitRequest) -> SubmitResult:
        return SubmitResult(ok=True)


def choose_submit_port(prefs: BatchPrefs) -> PrintSubmitPort:
    """Select submit implementation from prefs. Wave 1: DryRunSubmit only."""
    if prefs.dry_run:
        return DryRunSubmit()
    raise StartNeedsDryRunError("Wave 1 only supports Dry Run. Enable Dry Run before Start.")


class StartNeedsDryRunError(ValueError):
    """Raised when Start is requested without Dry Run (no real sink yet)."""

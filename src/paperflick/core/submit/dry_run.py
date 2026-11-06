"""Dry Run submitter. Never talks to a printer."""

from __future__ import annotations

from collections.abc import Sequence

from paperflick.core.submit.port import SubmitOk, SubmitRequest, SubmitResult
from paperflick.core.submit.preflight import preflight


class SubmitScript:
    """Ordered Dry Run results. Past the last step every call returns SubmitOk.

    Share one script across the DryRunSubmit instances a session builds, so a
    reprint reads the next step instead of starting over.
    """

    def __init__(self, steps: Sequence[SubmitResult] = ()) -> None:
        self._steps = tuple(steps)
        self._index = 0

    def next(self) -> SubmitResult:
        """Return the current step and advance."""
        if self._index >= len(self._steps):
            return SubmitOk()
        result = self._steps[self._index]
        self._index += 1
        return result


class DryRunSubmit:
    """Run preflight, then the script. An empty script accepts every readable file."""

    def __init__(self, script: SubmitScript | None = None) -> None:
        self._script = script if script is not None else SubmitScript()

    def submit(self, request: SubmitRequest) -> SubmitResult:
        """Preflight first. A missing file does not advance the script."""
        failed = preflight(request)
        if failed is not None:
            return failed
        return self._script.next()

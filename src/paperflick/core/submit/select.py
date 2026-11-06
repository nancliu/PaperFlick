"""Pick the Print Job submitter for one Batch."""

from __future__ import annotations

from pathlib import Path

from paperflick.core.batch.prefs import BatchPrefs
from paperflick.core.submit.dry_run import DryRunSubmit
from paperflick.core.submit.pdf_sumatra import PdfSumatraSubmit, SumatraRunner, find_sumatra
from paperflick.core.submit.port import PrintSubmitPort


def choose_submit_port(
    prefs: BatchPrefs,
    *,
    executable: Path | None = None,
    run: SumatraRunner | None = None,
) -> PrintSubmitPort:
    """Return Dry Run when asked. Otherwise one Sumatra port for the Batch.

    ``executable`` None searches the machine. A passed path is used as given,
    including when the file is missing, so a test can fail closed without
    launching an installed SumatraPDF.
    """
    if prefs.dry_run:
        return DryRunSubmit()
    found = find_sumatra() if executable is None else executable
    if run is None:
        return PdfSumatraSubmit(found)
    return PdfSumatraSubmit(found, run=run)

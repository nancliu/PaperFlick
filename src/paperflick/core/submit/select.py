"""Pick the Print Job submitter for one Batch."""

from __future__ import annotations

from pathlib import Path

from paperflick.core.batch.prefs import BatchPrefs
from paperflick.core.submit.docx_print import build_docx_submit
from paperflick.core.submit.dry_run import DryRunSubmit
from paperflick.core.submit.image_win import DeviceFactory, ImageWinSubmit
from paperflick.core.submit.live import LiveSubmit
from paperflick.core.submit.pdf_sumatra import PdfSumatraSubmit, SumatraRunner, find_sumatra
from paperflick.core.submit.port import PrintSubmitPort


def choose_submit_port(
    prefs: BatchPrefs,
    *,
    executable: Path | None = None,
    run: SumatraRunner | None = None,
    devices: DeviceFactory | None = None,
    docx: PrintSubmitPort | None = None,
) -> PrintSubmitPort:
    """Return Dry Run when asked. Otherwise PDF, image, and DOCX ports.

    ``executable`` None searches the machine. A passed path is used as given,
    including when the file is missing, so a test can fail closed without
    launching an installed SumatraPDF. ``devices`` None draws each image
    through the Windows spooler. ``docx`` replaces the Word/OnlyOffice port
    for the same reason.
    """
    if prefs.dry_run:
        return DryRunSubmit()
    found = find_sumatra() if executable is None else executable
    if run is None:
        pdf: PrintSubmitPort = PdfSumatraSubmit(found)
    else:
        pdf = PdfSumatraSubmit(found, run=run)
    image = ImageWinSubmit() if devices is None else ImageWinSubmit(devices=devices)
    docx_port = build_docx_submit(found, run) if docx is None else docx
    return LiveSubmit(pdf, image, docx_port)

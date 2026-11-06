"""Real Print Job port. PDF and images dispatch by DocKind."""

from __future__ import annotations

from paperflick.core.batch.formats import DocKind
from paperflick.core.submit.image_win import ImageWinSubmit
from paperflick.core.submit.pdf_sumatra import PdfSumatraSubmit
from paperflick.core.submit.port import (
    REASON_UNSUPPORTED,
    PrintSubmitPort,
    SubmitFailed,
    SubmitRequest,
    SubmitResult,
)
from paperflick.core.submit.preflight import preflight


class LiveSubmit:
    """Submit one Print Item through the engine for its kind.

    PDF uses SumatraPDF. Images use Pillow and Windows printing. Every other
    kind fails that item. DOCX is one of those kinds until its own issue.
    """

    def __init__(self, pdf: PdfSumatraSubmit, image: ImageWinSubmit) -> None:
        self._ports: dict[DocKind, PrintSubmitPort] = {
            DocKind.PDF: pdf,
            DocKind.IMAGE: image,
        }

    def submit(self, request: SubmitRequest) -> SubmitResult:
        """Dispatch one item. An unknown kind is a failure, not a raised error."""
        port = self._ports.get(request.item.kind)
        if port is None:
            failed = preflight(request)
            if failed is not None:
                return failed
            return SubmitFailed(REASON_UNSUPPORTED)
        return port.submit(request)

"""Checks shared by Dry Run and a future real submit."""

from __future__ import annotations

from paperflick.core.submit.port import SubmitFailed, SubmitRequest

REASON_MISSING = "文件不存在"
REASON_UNREADABLE = "文件无法读取"


def preflight(request: SubmitRequest) -> SubmitFailed | None:
    """Return a failure when the file is missing or unreadable.

    A Dry Run failure here is a failure a real submit would also report.
    """
    path = request.item.path
    if not path.is_file():
        return SubmitFailed(REASON_MISSING)
    try:
        with path.open("rb"):
            pass
    except OSError:
        return SubmitFailed(REASON_UNREADABLE)
    return None

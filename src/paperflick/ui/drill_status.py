"""Status-line copy for Dry Run. No widget imports."""

from __future__ import annotations

DRILL_UI_LABEL = "演练（不送打印机）"
DRILL_BATCH_PREFIX = "演练 · "


def format_status_line(message: str, *, dry_run: bool, batch_active: bool) -> str:
    """Choose the status line for Dry Run.

    Args:
        message: Text already on the status line, or the text about to be shown.
        dry_run: Whether the Dry Run control is on.
        batch_active: Whether the Batch is running or paused.

    Returns:
        Idle Dry Run with no other message shows 「演练（不送打印机）」.
        An active Batch prefixes with 「演练 · 」. A non-empty idle message,
        including the batch-end report, is left as written.
    """
    body = _strip_drill_chrome(message)
    if not dry_run:
        return body
    if batch_active:
        if body:
            return f"{DRILL_BATCH_PREFIX}{body}"
        return DRILL_BATCH_PREFIX
    if body == "":
        return DRILL_UI_LABEL
    return body


def _strip_drill_chrome(message: str) -> str:
    """Remove a drill prefix or idle hint so a later format does not nest them."""
    body = message
    if body.startswith(DRILL_BATCH_PREFIX):
        body = body[len(DRILL_BATCH_PREFIX) :]
    if body == DRILL_UI_LABEL:
        return ""
    return body

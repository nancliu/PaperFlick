"""Left/right split for the printer sidebar.

The sash is remembered for this process only. It is not a Settings field.
"""

from __future__ import annotations

SIDEBAR_DEFAULT_PX = 280
SIDEBAR_MIN_PX = 200

_preferred_px: int | None = None


def clamp_sidebar_width(requested: int, window_width: int) -> int:
    """Clamp a left-pane width into the drag range for this window.

    The range is 200px through half the window width. When the window is
    narrower than 400px, half the window is below 200px, and the pane uses
    that half so the right side stays on screen.
    """
    if window_width <= 0:
        return SIDEBAR_MIN_PX
    upper = window_width // 2
    if upper < SIDEBAR_MIN_PX:
        return max(0, min(requested, upper))
    return max(SIDEBAR_MIN_PX, min(requested, upper))


def session_sidebar_preferred_px() -> int | None:
    """Return the remembered sash width, or None before the user drags."""
    return _preferred_px


def remember_sidebar_width(width: int) -> None:
    """Remember the sash width for this process only."""
    global _preferred_px
    _preferred_px = int(width)


def reset_sidebar_split_session() -> None:
    """Drop the in-process sash memory."""
    global _preferred_px
    _preferred_px = None


def displayed_sidebar_width(window_width: int) -> int:
    """Return the left-pane width to show for this window.

    Uses the session sash when the user has dragged one; otherwise 280px.
    The result is clamped to the drag range.
    """
    preferred = SIDEBAR_DEFAULT_PX if _preferred_px is None else _preferred_px
    return clamp_sidebar_width(preferred, window_width)

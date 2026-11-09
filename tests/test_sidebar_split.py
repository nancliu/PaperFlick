"""Session-only printer sidebar sash. Nothing here is written to Settings."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from paperflick.core.settings import Settings
from paperflick.ui.sidebar_split import (
    SIDEBAR_DEFAULT_PX,
    SIDEBAR_MIN_PX,
    clamp_sidebar_width,
    displayed_sidebar_width,
    remember_sidebar_width,
    reset_sidebar_split_session,
    session_sidebar_preferred_px,
)


@pytest.fixture(autouse=True)
def _clear_sash_session() -> Iterator[None]:
    reset_sidebar_split_session()
    yield
    reset_sidebar_split_session()


def test_default_left_pane_is_about_280() -> None:
    assert SIDEBAR_DEFAULT_PX == 280
    assert displayed_sidebar_width(780) == 280
    assert displayed_sidebar_width(640) == 280


def test_drag_range_is_200_through_half_the_window() -> None:
    assert SIDEBAR_MIN_PX == 200
    assert clamp_sidebar_width(100, 780) == 200
    assert clamp_sidebar_width(280, 780) == 280
    assert clamp_sidebar_width(500, 780) == 390
    assert clamp_sidebar_width(400, 640) == 320
    assert clamp_sidebar_width(-20, 800) == 200


def test_narrow_window_uses_half_when_half_is_below_the_minimum() -> None:
    assert clamp_sidebar_width(280, 300) == 150
    assert clamp_sidebar_width(10, 300) == 10
    assert clamp_sidebar_width(280, 0) == SIDEBAR_MIN_PX


def test_session_remembers_sash_until_reset_and_does_not_touch_settings() -> None:
    assert session_sidebar_preferred_px() is None
    remember_sidebar_width(350)
    assert session_sidebar_preferred_px() == 350
    assert displayed_sidebar_width(780) == 350
    assert displayed_sidebar_width(600) == 300
    assert session_sidebar_preferred_px() == 350
    assert displayed_sidebar_width(1000) == 350

    reset_sidebar_split_session()
    assert session_sidebar_preferred_px() is None
    assert displayed_sidebar_width(780) == 280

    fields = set(Settings.__dataclass_fields__)
    assert "selected_printer" in fields
    assert not any("sash" in name or "sidebar" in name for name in fields)

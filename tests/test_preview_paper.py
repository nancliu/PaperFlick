"""Preview Paper expresses Facing without changing Orientation storage."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image

from paperflick.core.batch import (
    DocKind,
    Facing,
    ItemId,
    ItemStatus,
    Measured,
    Orientation,
    PrintItem,
    Unread,
)
from paperflick.ui.preview_window import (
    UNFORCED_COPY,
    _page_image,
    draft_facing,
    facing_summary,
    fit_inside,
    paper_pixel_size,
)


def test_draft_facing_empty_radio_follows_auto_shape() -> None:
    tall = Measured(100, 200)
    wide = Measured(200, 100)
    assert draft_facing(None, tall) is Facing.PORTRAIT
    assert draft_facing(None, wide) is Facing.LANDSCAPE
    assert draft_facing(None, Unread("x")) is Facing.PORTRAIT


def test_draft_facing_forced_and_printer_default() -> None:
    tall = Measured(100, 200)
    assert draft_facing(Orientation.LANDSCAPE, tall) is Facing.LANDSCAPE
    assert draft_facing(Orientation.PORTRAIT, Measured(200, 100)) is Facing.PORTRAIT
    assert draft_facing(Orientation.PRINTER_DEFAULT, tall) is None
    assert draft_facing(Orientation.AUTO, tall) is Facing.PORTRAIT


def test_paper_pixel_size_swaps_a4_aspect() -> None:
    portrait = paper_pixel_size(Facing.PORTRAIT, max_width=300, max_height=300)
    landscape = paper_pixel_size(Facing.LANDSCAPE, max_width=300, max_height=300)
    unforced = paper_pixel_size(None, max_width=300, max_height=300)

    assert portrait[1] > portrait[0]
    assert landscape[0] > landscape[1]
    assert abs(portrait[0] / portrait[1] - 210 / 297) < 0.02
    assert abs(landscape[0] / landscape[1] - 297 / 210) < 0.02
    assert unforced[0] == unforced[1]
    assert unforced != portrait
    assert unforced != landscape


def test_fit_inside_keeps_aspect_and_fits() -> None:
    assert fit_inside(200, 100, 100, 100) == (100, 50)
    assert fit_inside(100, 200, 100, 100) == (50, 100)
    assert fit_inside(50, 50, 100, 100) == (100, 100)


def test_facing_summary_copy() -> None:
    assert facing_summary(Facing.LANDSCAPE) == "横向"
    assert facing_summary(Facing.PORTRAIT) == "纵向"
    assert facing_summary(None) == UNFORCED_COPY


def test_page_image_still_decodes_for_paper_fit(tmp_path: Path) -> None:
    """Raster path stays available; Preview Paper scales it via fit_inside."""
    path = tmp_path / "wide.png"
    Image.new("RGB", (200, 80), color=(1, 2, 3)).save(path)
    item = PrintItem(
        id=ItemId(uuid4()),
        path=path,
        kind=DocKind.IMAGE,
        status=ItemStatus.WAITING,
        orientation=Orientation.AUTO,
        shape=Measured(200, 80),
        failure_reason=None,
    )
    drawn = _page_image(item)
    assert drawn is not None
    fitted = fit_inside(drawn.width, drawn.height, 180, 120)
    assert fitted[0] <= 180
    assert fitted[1] <= 120
    assert fitted[0] / fitted[1] == pytest.approx(drawn.width / drawn.height, rel=0.05)

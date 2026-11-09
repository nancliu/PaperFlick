"""Pure ItemStatus → text color mapping for Print Item rows."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from paperflick.core.batch import ItemStatus
from paperflick.core.batch.formats import probe
from paperflick.core.batch.types import PrintItem
from paperflick.ui.item_list import (
    identity_text,
    status_text,
    status_text_color,
)


def test_status_text_color_light_palette() -> None:
    assert status_text_color(ItemStatus.WAITING, "light") == "#6C6C6C"
    assert status_text_color(ItemStatus.PRINTING, "Light") == "#0072B2"
    assert status_text_color(ItemStatus.SUCCESS, "LIGHT") == "#009E73"
    assert status_text_color(ItemStatus.FAILED, "light") == "#D55E00"


def test_status_text_color_dark_palette() -> None:
    assert status_text_color(ItemStatus.WAITING, "dark") == "#B8B8B8"
    assert status_text_color(ItemStatus.PRINTING, "Dark") == "#56B4E9"
    assert status_text_color(ItemStatus.SUCCESS, "DARK") == "#2ECC9A"
    assert status_text_color(ItemStatus.FAILED, "dark") == "#FF7A1A"


def test_status_text_color_unknown_mode_uses_light() -> None:
    assert status_text_color(ItemStatus.PRINTING, "system") == "#0072B2"
    assert status_text_color(ItemStatus.FAILED, "") == "#D55E00"


def test_status_and_identity_text_keep_chinese_labels(tmp_path: Path) -> None:
    path = tmp_path / "demo.pdf"
    path.write_bytes(b"%PDF-1.4")
    item = PrintItem.added(path, probe(path))

    assert identity_text(item).startswith("demo.pdf")
    assert status_text(item) == "[等待]"

    printing = replace(item, status=ItemStatus.PRINTING)
    assert status_text(printing) == "[打印中]"

    success = replace(item, status=ItemStatus.SUCCESS)
    assert status_text(success) == "[成功]"

    failed = replace(item, status=ItemStatus.FAILED, failure_reason="卡纸")
    assert status_text(failed) == "[失败]  卡纸"

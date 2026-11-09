"""Dry Run status copy: idle hint, in-batch prefix, report left intact."""

from __future__ import annotations

from paperflick.ui.drill_status import format_status_line

_REPORT = "本批完成：成功 1、失败 1"


def test_idle_dry_run_with_no_message_shows_the_drill_label() -> None:
    assert format_status_line("", dry_run=True, batch_active=False) == "演练（不送打印机）"


def test_idle_without_dry_run_stays_empty() -> None:
    assert format_status_line("", dry_run=False, batch_active=False) == ""


def test_batch_end_report_is_not_replaced_or_prefixed() -> None:
    assert format_status_line(_REPORT, dry_run=True, batch_active=False) == _REPORT


def test_during_batch_prefixes_a_message() -> None:
    assert format_status_line("卡纸", dry_run=True, batch_active=True) == "演练 · 卡纸"


def test_during_batch_with_no_message_is_the_prefix() -> None:
    assert format_status_line("", dry_run=True, batch_active=True) == "演练 · "


def test_prefix_is_not_doubled() -> None:
    assert format_status_line("演练 · 卡纸", dry_run=True, batch_active=True) == "演练 · 卡纸"


def test_idle_hint_is_not_nested_into_the_batch_prefix() -> None:
    hint = "演练（不送打印机）"
    assert format_status_line(hint, dry_run=True, batch_active=True) == "演练 · "


def test_turning_dry_run_off_clears_the_idle_hint_and_the_prefix() -> None:
    assert format_status_line("演练（不送打印机）", dry_run=False, batch_active=False) == ""
    assert format_status_line("演练 · 卡纸", dry_run=False, batch_active=False) == "卡纸"


def test_live_batch_does_not_prefix() -> None:
    assert format_status_line("卡纸", dry_run=False, batch_active=True) == "卡纸"

"""Printer sidebar labels: display suffix stays off the real name and the hover text."""

from __future__ import annotations

from paperflick.ui.printer_sidebar import printer_display_label, sidebar_entries


def test_printer_display_label_adds_default_suffix_only_when_asked() -> None:
    assert printer_display_label("HP LaserJet", is_system_default=False) == "HP LaserJet"
    assert printer_display_label("HP LaserJet", is_system_default=True) == "HP LaserJet（默认）"


def test_sidebar_entries_keep_real_name_on_hover_and_mark_only_the_default() -> None:
    entries = sidebar_entries(["Alpha", "Beta"], "Beta")
    assert [(entry.real_name, entry.display_label, entry.hover_text) for entry in entries] == [
        ("Alpha", "Alpha", "Alpha"),
        ("Beta", "Beta（默认）", "Beta"),
    ]


def test_sidebar_entries_skip_the_suffix_when_the_default_is_not_installed() -> None:
    assert sidebar_entries([], "HP") == ()
    missing = sidebar_entries(["Alpha"], None)
    assert missing[0].display_label == "Alpha"
    assert missing[0].hover_text == "Alpha"
    other = sidebar_entries(["Alpha"], "Other")
    assert other[0].display_label == "Alpha"
    assert other[0].hover_text == "Alpha"

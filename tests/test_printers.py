"""list_installed_printers brands EnumPrinters names; no real printer required."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from paperflick.core.printers import (
    brand_printer_name,
    list_installed_printers,
    resolve_selected_printer,
    resolve_sidebar_printer,
    selected_printer_for_persist,
)


def test_brand_printer_name() -> None:
    assert brand_printer_name("  HP LaserJet  ") == "HP LaserJet"
    assert brand_printer_name("") is None
    assert brand_printer_name("   ") is None
    assert brand_printer_name(None) is None
    assert brand_printer_name(12) is None


def test_resolve_selected_printer() -> None:
    installed = ["A", "B"]
    assert resolve_selected_printer("A", installed) == "A"
    assert resolve_selected_printer("  B  ", installed) == "B"
    assert resolve_selected_printer("Missing", installed) is None
    assert resolve_selected_printer(None, installed) is None


def test_selected_printer_for_persist_keeps_stale() -> None:
    assert selected_printer_for_persist("Live", "Old") == "Live"
    assert selected_printer_for_persist(None, "Gone Printer") == "Gone Printer"
    assert selected_printer_for_persist(None, None) is None
    assert selected_printer_for_persist(None, "  ") is None


def test_resolve_sidebar_printer_falls_back_to_system_default() -> None:
    installed = ["A", "B", "C"]
    assert resolve_sidebar_printer(None, installed, system_default="B") == "B"
    assert resolve_sidebar_printer("  ", installed, system_default="B") == "B"
    assert resolve_sidebar_printer("A", installed, system_default="B") == "A"
    assert resolve_sidebar_printer("Gone", installed, system_default="B") is None
    assert resolve_sidebar_printer(None, installed, system_default="Missing") is None
    assert resolve_sidebar_printer(None, installed, system_default=None) is None


def test_list_installed_printers_parses_enum_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        (0, "desc", "Printer One", "comment"),
        (0, "desc", "  Printer Two  ", "comment"),
        (0, "desc", "Printer One", "dup"),
        (0, "desc", "", "empty"),
        (0, "short"),
    ]

    fake_win32 = SimpleNamespace(
        PRINTER_ENUM_LOCAL=1,
        PRINTER_ENUM_CONNECTIONS=2,
        EnumPrinters=lambda *_args, **_kwargs: rows,
    )
    monkeypatch.setitem(sys.modules, "win32print", fake_win32)

    assert list_installed_printers() == ["Printer One", "Printer Two"]


def test_list_installed_printers_empty_without_win32(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "win32print", None)
    assert list_installed_printers() == []


def test_list_installed_printers_empty_on_enum_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(*_args: object, **_kwargs: object) -> list[object]:
        raise OSError("enum failed")

    fake_win32 = SimpleNamespace(
        PRINTER_ENUM_LOCAL=1,
        PRINTER_ENUM_CONNECTIONS=2,
        EnumPrinters=_fail,
    )
    monkeypatch.setitem(sys.modules, "win32print", fake_win32)
    assert list_installed_printers() == []

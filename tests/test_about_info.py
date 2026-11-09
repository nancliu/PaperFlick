"""About copy is built from a supplied version, not a second literal."""

from __future__ import annotations

from paperflick.ui.about_info import about_lines, version_badge


def test_about_lines_use_the_supplied_version() -> None:
    name, version_line, tagline, url = about_lines("9.8.7")
    assert name == "纸闪 PaperFlick"
    assert version_line == "版本 9.8.7"
    assert tagline == "个人向 Windows 批量打印工具"
    assert url == "https://github.com/nancliu/PaperFlick"


def test_version_badge_prefixes_v() -> None:
    assert version_badge("9.8.7") == "v9.8.7"

"""Windows Shell thumbnail adapter: failure paths without Word or Explorer."""

from __future__ import annotations

from pathlib import Path

from paperflick.core.shell_thumbnail import windows_shell_thumbnail


def test_windows_shell_thumbnail_missing_file(tmp_path: Path) -> None:
    assert windows_shell_thumbnail(tmp_path / "missing.docx") is None


def test_windows_shell_thumbnail_rejects_generic_bytes(tmp_path: Path) -> None:
    path = tmp_path / "fake.docx"
    path.write_bytes(b"not-a-real-office-document")
    assert windows_shell_thumbnail(path) is None

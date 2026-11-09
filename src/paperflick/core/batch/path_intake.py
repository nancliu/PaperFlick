"""Expand AddPaths into concrete Print Item rows."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from paperflick.core.batch.formats import probe
from paperflick.core.batch.types import PrintItem


def expand_paths(paths: Sequence[Path]) -> list[PrintItem]:
    """Turn user-selected files and folders into Waiting Print Items.

    Rows are deduped by resolved path. Each new row is Auto. A missing path
    still becomes a row so the user can see it later.
    """
    seen: set[Path] = set()
    items: list[PrintItem] = []
    for path in iter_intake_files(paths):
        _append_file(path, seen, items)
    return items


def iter_intake_files(paths: Sequence[Path]) -> list[Path]:
    """Expand folders to files in AddPaths order. Non-directories stay as-is."""
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(_iter_files(path))
        else:
            files.append(path)
    return files


def _iter_files(directory: Path) -> list[Path]:
    files: list[Path] = []
    try:
        for child in sorted(directory.rglob("*")):
            if child.is_file():
                files.append(child)
    except OSError:
        return files
    return files


def _append_file(path: Path, seen: set[Path], items: list[PrintItem]) -> None:
    try:
        key = path.resolve()
    except OSError:
        key = path
    if key in seen:
        return
    seen.add(key)
    items.append(PrintItem.added(path, probe(path)))

"""Expand AddPaths into concrete Print Item rows (folder walk + kind sniff)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from uuid import uuid4

from paperflick.core.batch.types import ItemId, ItemStatus, Orientation, PrintItem

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".gif", ".webp"}
_DOC_SUFFIXES = {".doc", ".docx"}
_PDF_SUFFIXES = {".pdf"}


def sniff_kind(path: Path) -> str:
    """Map a file suffix to a wave-1 kind label."""
    suffix = path.suffix.lower()
    if suffix in _PDF_SUFFIXES:
        return "pdf"
    if suffix in _DOC_SUFFIXES:
        return "docx"
    if suffix in _IMAGE_SUFFIXES:
        return "image"
    return "unknown"


def expand_paths(paths: Sequence[Path]) -> list[PrintItem]:
    """Turn user-selected files/folders into Waiting Print Items (deduped by resolved path)."""
    seen: set[Path] = set()
    items: list[PrintItem] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            for child in _iter_files(path):
                _append_file(child, seen, items)
        else:
            # Missing paths still become rows so the user can see them fail later.
            _append_file(path, seen, items)
    return items


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
    items.append(
        PrintItem(
            id=ItemId(uuid4()),
            path=path,
            kind=sniff_kind(path),
            orientation=Orientation.AUTO,
            status=ItemStatus.WAITING,
        )
    )

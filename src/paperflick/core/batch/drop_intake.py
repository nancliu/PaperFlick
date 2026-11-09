"""Classify Explorer drops into AddPaths inputs and UNKNOWN skip feedback."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from paperflick.core.batch.formats import DocKind, kind_for_path
from paperflick.core.batch.path_intake import iter_intake_files

# Brace-wrapped tokens (spaces) or bare non-space tokens. Avoid Tcl splitlist
# so Windows backslashes like ``\a`` are not treated as escapes.
_DND_PATH_TOKEN = re.compile(r"\{([^{}]*)\}|(\S+)")


@dataclass(frozen=True, slots=True)
class DropIntake:
    """Paths safe for AddPaths, plus DnD-only UNKNOWN skip feedback."""

    paths: tuple[Path, ...]
    skipped_unknown: int

    @property
    def status_text(self) -> str:
        """Status-bar summary when DnD skipped unsupported files; else empty."""
        if self.skipped_unknown <= 0:
            return ""
        return f"已跳过 {self.skipped_unknown} 个不支持的文件"


def parse_dnd_files_payload(data: str) -> list[Path]:
    """Parse a ``DND_FILES`` payload into paths.

    Handles brace-wrapped paths with spaces and bare multi-select lists without
    Tcl backslash substitution.
    """
    paths: list[Path] = []
    for match in _DND_PATH_TOKEN.finditer(data.strip()):
        token = match.group(1) if match.group(1) is not None else match.group(2)
        if token:
            paths.append(Path(token))
    return paths


def classify_dropped_paths(paths: Sequence[Path]) -> DropIntake:
    """Expand folders, keep non-UNKNOWN files for AddPaths, count UNKNOWN skips.

    Button Add / Add folder does not use this filter. Missing paths are still
    classified by suffix so a dropped ``.pdf`` stays in the list.
    """
    accepted: list[Path] = []
    skipped = 0
    for path in iter_intake_files(paths):
        if kind_for_path(path) is DocKind.UNKNOWN:
            skipped += 1
            continue
        accepted.append(path)
    return DropIntake(paths=tuple(accepted), skipped_unknown=skipped)

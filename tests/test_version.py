"""Package version has one truth, shared with pyproject.toml."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from paperflick import __version__

_ROOT = Path(__file__).resolve().parents[1]
_VERSION_LITERAL = re.compile(r"\d+\.\d+\.\d+")


def test_package_version_matches_pyproject() -> None:
    """``paperflick.__version__`` and ``[project].version`` stay the same string."""
    data = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert __version__ == data["project"]["version"]


def test_version_literal_is_not_repeated_in_the_package() -> None:
    """UI and core copy must not hard-code a third version string."""
    src = _ROOT / "src" / "paperflick"
    offenders: list[str] = []
    for path in sorted(src.rglob("*.py")):
        if path == src / "__init__.py":
            continue
        if _VERSION_LITERAL.search(path.read_text(encoding="utf-8")):
            offenders.append(path.relative_to(src).as_posix())
    assert offenders == []

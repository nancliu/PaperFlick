"""About dialog copy. Callers pass ``paperflick.__version__``."""

from __future__ import annotations

PRODUCT_NAME = "纸闪 PaperFlick"
TAGLINE = "个人向 Windows 批量打印工具"
REPO_URL = "https://github.com/nancliu/PaperFlick"


def about_lines(version: str) -> tuple[str, str, str, str]:
    """Return product name, version line, tagline, and repository URL.

    Args:
        version: Version string to show, without a leading ``v``.

    Returns:
        The four About lines, in display order.
    """
    return (PRODUCT_NAME, f"版本 {version}", TAGLINE, REPO_URL)


def version_badge(version: str) -> str:
    """Return the status-bar badge ``vX.Y.Z``.

    Args:
        version: Version string from ``paperflick.__version__``.

    Returns:
        The badge text.
    """
    return f"v{version}"

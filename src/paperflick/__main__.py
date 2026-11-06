"""Entry point for ``python -m paperflick``."""

from __future__ import annotations

from paperflick.ui.main_window import run


def main() -> None:
    """Launch the PaperFlick main window."""
    run()


if __name__ == "__main__":
    main()

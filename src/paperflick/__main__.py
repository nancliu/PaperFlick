from __future__ import annotations

import logging

from paperflick.ui.main_window import run


def main() -> None:
    """Launch the window. Engine choice is logged when a DOCX Print Item prints."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()


if __name__ == "__main__":
    main()

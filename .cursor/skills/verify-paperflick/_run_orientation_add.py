"""Headless verify for orientation-on-add."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

from paperflick.core.batch import AddPaths, Orientation
from paperflick.ui.item_list import orientation_label
from paperflick.ui.main_window import MainWindow


def main() -> None:
    """Add landscape PNG and corrupt PDF; assert Auto + labels."""
    root = Path(tempfile.mkdtemp(prefix="paperflick-orient-"))
    landscape = root / "wide.png"
    Image.new("RGB", (200, 100), color=(20, 20, 20)).save(landscape)
    broken = root / "broken.pdf"
    broken.write_bytes(b"not-a-pdf")

    app = MainWindow()
    app.update_idletasks()
    app._session.apply(AddPaths([landscape, broken]))
    app.update_idletasks()
    snap = app._session.snapshot()
    assert len(snap.items) == 2
    assert all(item.orientation is Orientation.AUTO for item in snap.items)
    texts = [orientation_label(item) for item in snap.items]
    assert texts == ["横向", "纵向"], texts
    app.destroy()
    print("PASS orientation-add")


if __name__ == "__main__":
    main()

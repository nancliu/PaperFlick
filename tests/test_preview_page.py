"""Page thumbnails for preview: image and PDF first page."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pymupdf
from PIL import Image

from paperflick.core.batch import DocKind, ItemId, ItemStatus, Orientation, PrintItem, Unread
from paperflick.ui.preview_window import _page_image


def _item(path: Path, kind: DocKind) -> PrintItem:
    return PrintItem(
        id=ItemId(uuid4()),
        path=path,
        kind=kind,
        status=ItemStatus.WAITING,
        orientation=Orientation.AUTO,
        shape=Unread("test"),
        failure_reason=None,
    )


def test_page_image_for_png(tmp_path: Path) -> None:
    path = tmp_path / "a.png"
    Image.new("RGB", (80, 40), color=(10, 20, 30)).save(path)
    drawn = _page_image(_item(path, DocKind.IMAGE))
    assert drawn is not None
    assert drawn.width <= 360
    assert drawn.height <= 240


def test_page_image_for_pdf(tmp_path: Path) -> None:
    path = tmp_path / "a.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "preview")
    doc.save(path)
    doc.close()

    drawn = _page_image(_item(path, DocKind.PDF))
    assert drawn is not None
    assert drawn.width <= 360
    assert drawn.height <= 240


def test_page_image_docx_is_none(tmp_path: Path) -> None:
    path = tmp_path / "a.docx"
    path.write_bytes(b"not-a-real-docx")
    assert _page_image(_item(path, DocKind.DOCX)) is None


def test_page_image_bad_pdf_is_none(tmp_path: Path) -> None:
    path = tmp_path / "bad.pdf"
    path.write_bytes(b"%PDF-not-really")
    assert _page_image(_item(path, DocKind.PDF)) is None

"""Orientation apply scopes leave shape, status, and new Auto rows alone."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from docx import Document
from docx.shared import Mm
from PIL import Image
from pypdf import PageObject, PdfWriter

from paperflick.core.batch import (
    AddPaths,
    ApplyScope,
    BatchPhase,
    Facing,
    ItemId,
    ItemsChanged,
    Orientation,
    PrintItem,
    SetOrientation,
    resolve_facing,
)
from paperflick.core.batch.session import BatchSession
from paperflick.ui.item_list import orientation_label


def _write_pdf(path: Path, width: float, height: float) -> None:
    """Write a one-page PDF with the given mediabox."""
    writer = PdfWriter()
    writer.add_page(PageObject.create_blank_page(width=width, height=height))
    with path.open("wb") as handle:
        writer.write(handle)


def _write_png(path: Path, width: int, height: int) -> None:
    """Write a solid PNG of the given pixel size."""
    Image.new("RGB", (width, height), "white").save(path, format="PNG")


def _write_docx(path: Path, width_mm: float, height_mm: float) -> None:
    """Write a DOCX whose first section has the given page size."""
    document = Document()
    section = document.sections[0]
    section.page_width = Mm(width_mm)
    section.page_height = Mm(height_mm)
    document.save(path)


def _by_name(session: BatchSession, name: str) -> PrintItem:
    """Return the snapshot row with this file name."""
    return next(item for item in session.snapshot().items if item.path.name == name)


def test_scopes_update_marks_without_sticky_auto(tmp_path: Path) -> None:
    """This, same kind, and all change policies. A later add stays Auto."""
    tall_png = tmp_path / "tall.png"
    wide_png = tmp_path / "wide.png"
    pdf = tmp_path / "page.pdf"
    docx = tmp_path / "page.docx"
    _write_png(tall_png, 100, 200)
    _write_png(wide_png, 200, 100)
    _write_pdf(pdf, 595, 842)
    _write_docx(docx, 210, 297)

    session = BatchSession()
    session.apply(AddPaths([tall_png, wide_png, pdf, docx]))
    tall = _by_name(session, "tall.png")
    assert tall.orientation is Orientation.AUTO
    assert orientation_label(tall) == "纵向"
    assert resolve_facing(Orientation.AUTO, tall.shape) is Facing.PORTRAIT

    events: list[object] = []
    session.subscribe(events.append)
    session.apply(
        SetOrientation(anchor=tall.id, orientation=Orientation.LANDSCAPE, scope=ApplyScope.THIS)
    )
    tall = _by_name(session, "tall.png")
    assert tall.orientation is Orientation.LANDSCAPE
    assert orientation_label(tall) == "横向"
    assert resolve_facing(Orientation.AUTO, tall.shape) is Facing.PORTRAIT
    assert _by_name(session, "wide.png").orientation is Orientation.AUTO
    assert _by_name(session, "page.pdf").orientation is Orientation.AUTO
    assert _by_name(session, "page.docx").orientation is Orientation.AUTO
    assert events == [ItemsChanged()]
    assert session.snapshot().phase is BatchPhase.IDLE

    events.clear()
    session.apply(
        SetOrientation(anchor=tall.id, orientation=Orientation.LANDSCAPE, scope=ApplyScope.THIS)
    )
    assert events == []

    wide = _by_name(session, "wide.png")
    session.apply(
        SetOrientation(
            anchor=wide.id,
            orientation=Orientation.PRINTER_DEFAULT,
            scope=ApplyScope.SAME_KIND,
        )
    )
    assert _by_name(session, "tall.png").orientation is Orientation.PRINTER_DEFAULT
    assert orientation_label(_by_name(session, "tall.png")) == "打印机"
    assert _by_name(session, "wide.png").orientation is Orientation.PRINTER_DEFAULT
    assert _by_name(session, "page.pdf").orientation is Orientation.AUTO
    assert _by_name(session, "page.docx").orientation is Orientation.AUTO

    session.apply(
        SetOrientation(anchor=wide.id, orientation=Orientation.PORTRAIT, scope=ApplyScope.ALL)
    )
    assert all(item.orientation is Orientation.PORTRAIT for item in session.snapshot().items)
    assert orientation_label(_by_name(session, "wide.png")) == "纵向"

    extra = tmp_path / "later.png"
    _write_png(extra, 200, 100)
    session.apply(AddPaths([extra]))
    added = _by_name(session, "later.png")
    assert added.orientation is Orientation.AUTO
    assert orientation_label(added) == "横向"
    assert all(
        item.orientation is Orientation.PORTRAIT
        for item in session.snapshot().items
        if item.id != added.id
    )


def test_missing_anchor_skips_item_scopes_and_all_still_applies(tmp_path: Path) -> None:
    """A gone preview target does not match this or same kind. All still writes."""
    path = tmp_path / "wide.png"
    _write_png(path, 200, 100)
    session = BatchSession()
    session.apply(AddPaths([path]))
    missing = ItemId(uuid4())
    session.apply(
        SetOrientation(anchor=missing, orientation=Orientation.LANDSCAPE, scope=ApplyScope.THIS)
    )
    session.apply(
        SetOrientation(
            anchor=missing,
            orientation=Orientation.LANDSCAPE,
            scope=ApplyScope.SAME_KIND,
        )
    )
    assert session.snapshot().items[0].orientation is Orientation.AUTO
    session.apply(
        SetOrientation(anchor=missing, orientation=Orientation.PORTRAIT, scope=ApplyScope.ALL)
    )
    item = session.snapshot().items[0]
    assert item.orientation is Orientation.PORTRAIT
    assert orientation_label(item) == "纵向"

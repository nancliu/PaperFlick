"""Orientation cell text for Print Item rows."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from pypdf import PageObject, PdfWriter

from paperflick.core.batch import Orientation
from paperflick.core.batch.formats import probe
from paperflick.core.batch.types import PrintItem
from paperflick.ui.item_list import orientation_label


def _write_pdf(path: Path, width: float, height: float) -> None:
    writer = PdfWriter()
    page = PageObject.create_blank_page(width=width, height=height)
    writer.add_page(page)
    with path.open("wb") as handle:
        writer.write(handle)


def test_auto_row_label_is_bare_facing(tmp_path: Path) -> None:
    wide = tmp_path / "wide.pdf"
    tall = tmp_path / "tall.pdf"
    bad = tmp_path / "bad.pdf"
    _write_pdf(wide, 842, 595)
    _write_pdf(tall, 595, 842)
    bad.write_bytes(b"not a pdf")

    landscape = PrintItem.added(wide, probe(wide))
    portrait = PrintItem.added(tall, probe(tall))
    unread = PrintItem.added(bad, probe(bad))

    assert orientation_label(landscape) == "横向"
    assert orientation_label(portrait) == "纵向"
    assert orientation_label(unread) == "纵向"
    assert orientation_label(replace(portrait, orientation=Orientation.LANDSCAPE)) == "横向"
    assert orientation_label(replace(landscape, orientation=Orientation.PORTRAIT)) == "纵向"
    printer = replace(landscape, orientation=Orientation.PRINTER_DEFAULT)
    assert orientation_label(printer) == "打印机"

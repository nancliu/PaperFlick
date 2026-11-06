"""First-page facing for PDF, DOCX, and image Print Items."""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

import pytest
from docx import Document
from docx.shared import Mm
from PIL import Image
from pypdf import PageObject, PdfWriter

from paperflick.core.batch import (
    AddPaths,
    Facing,
    ItemStatus,
    Measured,
    Orientation,
    Unread,
    resolve_facing,
)
from paperflick.core.batch.formats import probe
from paperflick.core.batch.reduce import reduce
from paperflick.core.batch.state import BatchState

_EXIF_ORIENTATION = 274


def _write_pdf(path: Path, width: float, height: float, rotation: int = 0) -> None:
    writer = PdfWriter()
    page = PageObject.create_blank_page(width=width, height=height)
    if rotation:
        page.rotation = rotation
    writer.add_page(page)
    with path.open("wb") as handle:
        writer.write(handle)


def _write_png(path: Path, width: int, height: int) -> None:
    Image.new("RGB", (width, height), "white").save(path, format="PNG")


def _write_jpeg(path: Path, width: int, height: int, exif_orientation: int) -> None:
    image = Image.new("RGB", (width, height), "white")
    exif = image.getexif()
    exif[_EXIF_ORIENTATION] = exif_orientation
    image.save(path, format="JPEG", exif=exif)


def _write_docx(path: Path, width_mm: float, height_mm: float) -> None:
    document = Document()
    section = document.sections[0]
    section.page_width = Mm(width_mm)
    section.page_height = Mm(height_mm)
    document.save(path)


def _facing(path: Path) -> Facing | None:
    probed = probe(path)
    assert isinstance(probed.shape, Measured)
    return resolve_facing(Orientation.AUTO, probed.shape)


def test_landscape_and_portrait_files(tmp_path: Path) -> None:
    wide_pdf = tmp_path / "wide.pdf"
    tall_pdf = tmp_path / "tall.pdf"
    turned_pdf = tmp_path / "turned.pdf"
    wide_png = tmp_path / "wide.png"
    tall_png = tmp_path / "tall.png"
    wide_docx = tmp_path / "wide.docx"
    tall_docx = tmp_path / "tall.docx"
    _write_pdf(wide_pdf, 842, 595)
    _write_pdf(tall_pdf, 595, 842)
    _write_pdf(turned_pdf, 595, 842, rotation=90)
    _write_png(wide_png, 120, 80)
    _write_png(tall_png, 80, 120)
    _write_docx(wide_docx, 297, 210)
    _write_docx(tall_docx, 210, 297)

    assert _facing(wide_pdf) is Facing.LANDSCAPE
    assert _facing(tall_pdf) is Facing.PORTRAIT
    assert _facing(turned_pdf) is Facing.LANDSCAPE
    assert _facing(wide_png) is Facing.LANDSCAPE
    assert _facing(tall_png) is Facing.PORTRAIT
    assert _facing(wide_docx) is Facing.LANDSCAPE
    assert _facing(tall_docx) is Facing.PORTRAIT
    assert probe(wide_pdf).kind == "pdf"
    assert probe(wide_png).kind == "image"
    assert probe(wide_docx).kind == "docx"


def test_exif_orientation_swaps_axes(tmp_path: Path) -> None:
    path = tmp_path / "phone.jpg"
    _write_jpeg(path, 200, 100, exif_orientation=6)
    assert _facing(path) is Facing.PORTRAIT


def test_square_page_is_portrait() -> None:
    assert resolve_facing(Orientation.AUTO, Measured(100, 100)) is Facing.PORTRAIT


def test_forced_policy_ignores_shape() -> None:
    tall = Measured(10, 200)
    wide = Measured(200, 10)
    assert resolve_facing(Orientation.LANDSCAPE, tall) is Facing.LANDSCAPE
    assert resolve_facing(Orientation.PORTRAIT, wide) is Facing.PORTRAIT
    assert resolve_facing(Orientation.PRINTER_DEFAULT, wide) is None
    assert resolve_facing(Orientation.PRINTER_DEFAULT, Unread("missing")) is None


def test_corrupt_pdf_falls_back_to_portrait(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "bad.pdf"
    path.write_bytes(b"not a pdf")
    with caplog.at_level(logging.WARNING, logger="paperflick.formats"):
        probed = probe(path)
    assert probed.kind == "pdf"
    assert isinstance(probed.shape, Unread)
    assert resolve_facing(Orientation.AUTO, probed.shape) is Facing.PORTRAIT
    warnings = [record for record in caplog.records if record.name == "paperflick.formats"]
    assert len(warnings) == 1
    assert path.name in warnings[0].getMessage()


def test_legacy_doc_is_unread(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    path = tmp_path / "old.doc"
    path.write_bytes(b"not a word file")
    with caplog.at_level(logging.WARNING, logger="paperflick.formats"):
        probed = probe(path)
    assert probed.kind == "docx"
    assert isinstance(probed.shape, Unread)
    assert resolve_facing(Orientation.AUTO, probed.shape) is Facing.PORTRAIT
    assert len(caplog.records) == 1


def test_added_row_stays_auto_after_an_earlier_override(tmp_path: Path) -> None:
    wide = tmp_path / "wide.pdf"
    tall = tmp_path / "tall.pdf"
    _write_pdf(wide, 842, 595)
    _write_pdf(tall, 595, 842)
    state = BatchState()
    state, _events = reduce(state, AddPaths([wide]))
    state.items[0] = replace(state.items[0], orientation=Orientation.LANDSCAPE)
    state, _events = reduce(state, AddPaths([tall]))

    assert state.items[0].orientation is Orientation.LANDSCAPE
    added = state.items[1]
    assert added.orientation is Orientation.AUTO
    assert added.status is ItemStatus.WAITING
    assert resolve_facing(added.orientation, added.shape) is Facing.PORTRAIT

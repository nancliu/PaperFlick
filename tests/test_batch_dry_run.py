"""Dry Run Batch behavior: add/remove, start/pause/stop, no real print."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from paperflick.core.batch import (
    AddPaths,
    BatchPhase,
    BatchPrefs,
    BatchSession,
    Facing,
    ItemStatus,
    Orientation,
    PauseBatch,
    RemoveItems,
    ResumeBatch,
    StartBatch,
    StopBatch,
    Unread,
    resolve_facing,
)
from paperflick.core.submit import DryRunSubmit, SubmitOk, SubmitRequest, choose_submit_port


def _prefs(*, dry_run: bool = True, interval: float = 0.01) -> BatchPrefs:
    return BatchPrefs(
        interval_seconds=interval,
        wait_for_empty_queue=False,
        dry_run=dry_run,
        selected_printer=None,
    )


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")
    return path


def test_add_files_and_folder_populate_list(tmp_path: Path) -> None:
    a = _touch(tmp_path / "a.pdf")
    b = _touch(tmp_path / "sub" / "b.docx")
    folder = tmp_path / "folder"
    _touch(folder / "c.png")
    _touch(folder / "nested" / "d.txt")

    session = BatchSession()
    session.apply(AddPaths([a, b]))
    session.apply(AddPaths([folder]))

    snap = session.snapshot()
    names = sorted(item.path.name for item in snap.items)
    assert names == ["a.pdf", "b.docx", "c.png", "d.txt"]
    assert all(item.status is ItemStatus.WAITING for item in snap.items)
    assert all(item.orientation is Orientation.AUTO for item in snap.items)
    pdf_item = snap.items[0]
    assert pdf_item.kind == "pdf"
    assert isinstance(pdf_item.shape, Unread)
    assert resolve_facing(pdf_item.orientation, pdf_item.shape) is Facing.PORTRAIT
    assert {item.kind for item in snap.items if item.path.name == "c.png"} == {"image"}
    txt_item = next(item for item in snap.items if item.path.name == "d.txt")
    assert txt_item.kind == "unknown"
    assert isinstance(txt_item.shape, Unread)


def test_remove_selected_items(tmp_path: Path) -> None:
    session = BatchSession()
    session.apply(AddPaths([_touch(tmp_path / "one.pdf"), _touch(tmp_path / "two.pdf")]))
    first_id = session.snapshot().items[0].id
    session.apply(RemoveItems([first_id]))
    snap = session.snapshot()
    assert len(snap.items) == 1
    assert snap.items[0].path.name == "two.pdf"


def test_dry_run_advances_to_success_at_interval(tmp_path: Path) -> None:
    session = BatchSession()
    clock = session.manual_clock
    assert clock is not None
    paths = [_touch(tmp_path / f"{i}.pdf") for i in range(3)]
    session.apply(AddPaths(paths))
    session.apply(StartBatch(_prefs(interval=1.0)))

    # First item completes immediately on Start.
    snap = session.snapshot()
    assert snap.phase is BatchPhase.RUNNING
    assert snap.success_count == 1
    assert snap.waiting_count == 2

    assert clock.advance()
    assert session.snapshot().success_count == 2
    assert clock.advance()
    snap = session.snapshot()
    assert snap.success_count == 3
    assert snap.waiting_count == 0
    assert snap.phase is BatchPhase.IDLE


def test_pause_and_stop(tmp_path: Path) -> None:
    session = BatchSession()
    clock = session.manual_clock
    assert clock is not None
    session.apply(AddPaths([_touch(tmp_path / f"{i}.pdf") for i in range(4)]))
    session.apply(StartBatch(_prefs(interval=1.0)))
    assert session.snapshot().success_count == 1

    session.apply(PauseBatch())
    assert session.snapshot().phase is BatchPhase.PAUSED
    assert clock.advance() is False  # cancelled pending tick

    session.apply(ResumeBatch())
    assert session.snapshot().phase is BatchPhase.RUNNING
    assert clock.advance()
    assert session.snapshot().success_count == 2

    session.apply(StopBatch())
    snap = session.snapshot()
    assert snap.phase is BatchPhase.IDLE
    assert snap.success_count == 2
    assert snap.waiting_count == 2


def test_remove_while_paused_keeps_phase(tmp_path: Path) -> None:
    """A paused Batch still drops the row RemoveItems names."""
    session = BatchSession()
    session.apply(AddPaths([_touch(tmp_path / f"{name}.pdf") for name in ("a", "b", "c")]))
    session.apply(StartBatch(_prefs(interval=1.0)))
    session.apply(PauseBatch())
    assert session.snapshot().phase is BatchPhase.PAUSED
    waiting_id = next(
        item.id for item in session.snapshot().items if item.status is ItemStatus.WAITING
    )
    session.apply(RemoveItems([waiting_id]))
    snap = session.snapshot()
    assert snap.phase is BatchPhase.PAUSED
    assert len(snap.items) == 2
    assert all(item.id != waiting_id for item in snap.items)


def test_second_start_while_running_is_noop(tmp_path: Path) -> None:
    session = BatchSession()
    clock = session.manual_clock
    assert clock is not None
    session.apply(AddPaths([_touch(tmp_path / f"{i}.pdf") for i in range(3)]))
    session.apply(StartBatch(_prefs(interval=1.0)))
    assert session.snapshot().success_count == 1
    session.apply(StartBatch(_prefs(interval=1.0)))
    assert session.snapshot().success_count == 1
    assert clock.advance()
    assert session.snapshot().success_count == 2


def test_dry_run_submit_never_calls_win32(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_win32 = MagicMock()
    monkeypatch.setitem(__import__("sys").modules, "win32print", fake_win32)
    monkeypatch.setitem(__import__("sys").modules, "win32api", fake_win32)

    def _refuse_process(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Dry Run must not start a process")

    monkeypatch.setattr("subprocess.run", _refuse_process)

    path = _touch(tmp_path / "x.pdf")
    port = DryRunSubmit()
    from paperflick.core.batch.formats import DocKind, Probe
    from paperflick.core.batch.types import Measured, PrintItem

    item = PrintItem.added(path, Probe(DocKind.PDF, Measured(100, 200)))
    result = port.submit(SubmitRequest(item=item, printer=None))
    assert isinstance(result, SubmitOk)
    fake_win32.assert_not_called()
    again = choose_submit_port(_prefs(dry_run=True)).submit(SubmitRequest(item=item, printer=None))
    assert isinstance(again, SubmitOk)
    fake_win32.assert_not_called()

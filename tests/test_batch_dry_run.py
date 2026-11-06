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
    ItemStatus,
    PauseBatch,
    RemoveItems,
    ResumeBatch,
    StartBatch,
    StopBatch,
)
from paperflick.core.submit import DryRunSubmit, StartNeedsDryRunError, SubmitRequest
from paperflick.core.submit.dry_run import choose_submit_port


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
    assert snap.items[0].kind == "pdf"
    assert {item.kind for item in snap.items if item.path.name == "c.png"} == {"image"}


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


def test_start_without_dry_run_refuses() -> None:
    session = BatchSession()
    with pytest.raises(StartNeedsDryRunError, match="Dry Run"):
        session.apply(StartBatch(_prefs(dry_run=False)))
    assert session.snapshot().phase is BatchPhase.IDLE


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


def test_dry_run_submit_never_calls_win32(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_win32 = MagicMock()
    monkeypatch.setitem(__import__("sys").modules, "win32print", fake_win32)
    monkeypatch.setitem(__import__("sys").modules, "win32api", fake_win32)

    port = DryRunSubmit()
    from uuid import uuid4

    from paperflick.core.batch.types import ItemId, Orientation, PrintItem

    item = PrintItem(
        id=ItemId(uuid4()),
        path=Path("x.pdf"),
        kind="pdf",
        orientation=Orientation.AUTO,
        status=ItemStatus.WAITING,
    )
    result = port.submit(SubmitRequest(item=item, printer=None))
    assert result.ok is True
    fake_win32.assert_not_called()
    assert (
        choose_submit_port(_prefs(dry_run=True)).submit(SubmitRequest(item=item, printer=None)).ok
    )


def test_choose_submit_port_rejects_non_dry_run() -> None:
    with pytest.raises(StartNeedsDryRunError):
        choose_submit_port(_prefs(dry_run=False))

"""Failed Print Items stay, the Batch continues, reprint and clear stay atomic."""

from __future__ import annotations

from pathlib import Path

import pytest

from paperflick.core.batch import (
    AddPaths,
    BatchPhase,
    BatchPrefs,
    BatchSession,
    ClearSucceeded,
    ItemStatus,
    PauseBatch,
    RemoveItems,
    ReprintFailed,
    StartBatch,
)
from paperflick.core.batch.formats import DocKind, Probe
from paperflick.core.batch.types import Measured, PrintItem
from paperflick.core.submit import (
    DryRunSubmit,
    SubmitFailed,
    SubmitOk,
    SubmitRequest,
    SubmitScript,
)


def _prefs(*, dry_run: bool = True, interval: float = 1.0) -> BatchPrefs:
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


def _item(path: Path) -> PrintItem:
    return PrintItem.added(path, Probe(DocKind.PDF, Measured(100, 200)))


def _session(script: SubmitScript) -> BatchSession:
    return BatchSession(submit_factory=lambda _prefs: DryRunSubmit(script))


def _finish_pair(tmp_path: Path, script: SubmitScript) -> BatchSession:
    session = _session(script)
    session.apply(AddPaths([_touch(tmp_path / "a.pdf"), _touch(tmp_path / "b.pdf")]))
    session.apply(StartBatch(_prefs()))
    clock = session.manual_clock
    assert clock is not None
    assert clock.advance()
    return session


def test_empty_script_accepts_a_readable_file(tmp_path: Path) -> None:
    port = DryRunSubmit()
    item = _item(_touch(tmp_path / "a.pdf"))
    request = SubmitRequest(item=item, printer=None)
    assert isinstance(port.submit(request), SubmitOk)
    assert isinstance(port.submit(request), SubmitOk)


def test_script_injects_one_failure_then_accepts(tmp_path: Path) -> None:
    port = DryRunSubmit(SubmitScript((SubmitFailed("卡纸"),)))
    item = _item(_touch(tmp_path / "a.pdf"))
    request = SubmitRequest(item=item, printer=None)
    first = port.submit(request)
    second = port.submit(request)
    assert isinstance(first, SubmitFailed)
    assert first.reason == "卡纸"
    assert isinstance(second, SubmitOk)


def test_missing_file_fails_without_consuming_the_script(tmp_path: Path) -> None:
    port = DryRunSubmit(SubmitScript((SubmitFailed("卡纸"),)))
    missing = port.submit(SubmitRequest(item=_item(tmp_path / "gone.pdf"), printer=None))
    present = port.submit(SubmitRequest(item=_item(_touch(tmp_path / "ok.pdf")), printer=None))
    assert isinstance(missing, SubmitFailed)
    assert missing.reason == "文件不存在"
    assert isinstance(present, SubmitFailed)
    assert present.reason == "卡纸"


def test_unreadable_file_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _touch(tmp_path / "locked.pdf")

    def _deny(*_args: object, **_kwargs: object) -> None:
        raise OSError("denied")

    monkeypatch.setattr(Path, "open", _deny)
    result = DryRunSubmit().submit(SubmitRequest(item=_item(path), printer=None))
    assert isinstance(result, SubmitFailed)
    assert result.reason == "文件无法读取"


def test_submit_failed_requires_a_reason() -> None:
    with pytest.raises(ValueError, match="reason"):
        SubmitFailed("  ")


def test_scripted_failure_keeps_reason_and_batch_continues(tmp_path: Path) -> None:
    session = _finish_pair(tmp_path, SubmitScript((SubmitFailed("卡纸"),)))
    snap = session.snapshot()
    assert snap.phase is BatchPhase.IDLE
    assert snap.items[0].status is ItemStatus.FAILED
    assert snap.items[0].failure_reason == "卡纸"
    assert snap.items[1].status is ItemStatus.SUCCESS
    assert snap.failed_count == 1
    assert snap.success_count == 1
    assert snap.ids_with(ItemStatus.FAILED) == [snap.items[0].id]


def test_missing_file_stays_failed_and_batch_continues(tmp_path: Path) -> None:
    session = BatchSession()
    session.apply(AddPaths([tmp_path / "gone.pdf", _touch(tmp_path / "good.pdf")]))
    session.apply(StartBatch(_prefs()))
    clock = session.manual_clock
    assert clock is not None
    snap = session.snapshot()
    assert snap.items[0].status is ItemStatus.FAILED
    assert snap.items[0].failure_reason == "文件不存在"
    assert snap.items[1].status is ItemStatus.WAITING
    assert snap.phase is BatchPhase.RUNNING
    assert clock.advance()
    snap = session.snapshot()
    assert snap.failed_count == 1
    assert snap.success_count == 1
    assert snap.phase is BatchPhase.IDLE


def test_reprint_failed_resets_and_starts(tmp_path: Path) -> None:
    session = _finish_pair(tmp_path, SubmitScript((SubmitFailed("卡纸"),)))
    failed_id = session.snapshot().ids_with(ItemStatus.FAILED)[0]
    session.apply(ReprintFailed(StartBatch(_prefs())))
    snap = session.snapshot()
    assert snap.phase is BatchPhase.IDLE
    assert snap.failed_count == 0
    assert snap.success_count == 2
    reprinted = next(item for item in snap.items if item.id == failed_id)
    assert reprinted.status is ItemStatus.SUCCESS
    assert reprinted.failure_reason is None


def test_reprint_with_dry_run_off_submits(tmp_path: Path) -> None:
    session = _finish_pair(tmp_path, SubmitScript((SubmitFailed("卡纸"),)))
    session.apply(ReprintFailed(StartBatch(_prefs(dry_run=False))))
    snap = session.snapshot()
    assert snap.phase is BatchPhase.IDLE
    assert snap.dry_run is False
    assert snap.failed_count == 0
    assert snap.items[0].status is ItemStatus.SUCCESS
    assert snap.items[0].failure_reason is None


def test_reprint_while_paused_is_noop(tmp_path: Path) -> None:
    session = _session(SubmitScript((SubmitFailed("卡纸"),)))
    session.apply(AddPaths([_touch(tmp_path / "a.pdf"), _touch(tmp_path / "b.pdf")]))
    session.apply(StartBatch(_prefs()))
    session.apply(PauseBatch())
    session.apply(ReprintFailed(StartBatch(_prefs())))
    snap = session.snapshot()
    assert snap.phase is BatchPhase.PAUSED
    assert snap.items[0].status is ItemStatus.FAILED
    assert snap.items[0].failure_reason == "卡纸"
    assert snap.items[1].status is ItemStatus.WAITING


def test_reprint_with_no_failures_does_not_start(tmp_path: Path) -> None:
    session = BatchSession()
    session.apply(AddPaths([_touch(tmp_path / "a.pdf")]))
    session.apply(ReprintFailed(StartBatch(_prefs())))
    snap = session.snapshot()
    assert snap.phase is BatchPhase.IDLE
    assert snap.items[0].status is ItemStatus.WAITING


def test_clear_succeeded_keeps_failed_rows(tmp_path: Path) -> None:
    session = _finish_pair(tmp_path, SubmitScript((SubmitFailed("卡纸"),)))
    session.apply(ClearSucceeded())
    snap = session.snapshot()
    assert len(snap.items) == 1
    assert snap.items[0].status is ItemStatus.FAILED
    assert snap.items[0].failure_reason == "卡纸"
    assert snap.success_count == 0
    assert snap.failed_count == 1


def test_clear_succeeded_while_running_does_not_skip_waiting(tmp_path: Path) -> None:
    session = BatchSession()
    clock = session.manual_clock
    assert clock is not None
    session.apply(
        AddPaths(
            [_touch(tmp_path / "a.pdf"), _touch(tmp_path / "b.pdf"), _touch(tmp_path / "c.pdf")]
        )
    )
    session.apply(StartBatch(_prefs()))
    session.apply(ClearSucceeded())
    snap = session.snapshot()
    assert [item.path.name for item in snap.items] == ["b.pdf", "c.pdf"]
    assert clock.advance()
    snap = session.snapshot()
    assert snap.items[0].path.name == "b.pdf"
    assert snap.items[0].status is ItemStatus.SUCCESS
    assert snap.items[1].status is ItemStatus.WAITING


def test_remove_earlier_success_does_not_skip_waiting(tmp_path: Path) -> None:
    session = BatchSession()
    clock = session.manual_clock
    assert clock is not None
    session.apply(
        AddPaths(
            [_touch(tmp_path / "a.pdf"), _touch(tmp_path / "b.pdf"), _touch(tmp_path / "c.pdf")]
        )
    )
    session.apply(StartBatch(_prefs()))
    success_id = session.snapshot().items[0].id
    session.apply(RemoveItems([success_id]))
    assert clock.advance()
    snap = session.snapshot()
    assert snap.items[0].path.name == "b.pdf"
    assert snap.items[0].status is ItemStatus.SUCCESS
    assert snap.items[1].path.name == "c.pdf"
    assert snap.items[1].status is ItemStatus.WAITING

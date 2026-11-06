from __future__ import annotations

from pathlib import Path

from paperflick.core.batch import (
    AddPaths,
    BatchPhase,
    BatchPrefs,
    BatchSession,
    ItemStatus,
    RunReported,
    StartBatch,
    StopBatch,
)
from paperflick.core.batch.ledger import RunLedger
from paperflick.core.printers import ProbeFailed, SpoolerCount
from paperflick.core.submit import DryRunSubmit, SubmitFailed, SubmitScript


def _prefs(
    *,
    dry_run: bool = True,
    wait: bool = False,
    printer: str | None = None,
    interval: float = 1.0,
) -> BatchPrefs:
    return BatchPrefs(
        interval_seconds=interval,
        wait_for_empty_queue=wait,
        dry_run=dry_run,
        selected_printer=printer,
    )


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")
    return path


def _reports(session: BatchSession) -> list[RunReported]:
    found: list[RunReported] = []

    def listen(event: object) -> None:
        if isinstance(event, RunReported):
            found.append(event)

    session.subscribe(listen)
    return found


def test_report_counts_this_start_and_leaves_the_census(tmp_path: Path) -> None:
    session = BatchSession()
    reports = _reports(session)
    clock = session.manual_clock
    assert clock is not None
    session.apply(AddPaths([_touch(tmp_path / "old.pdf")]))
    session.apply(StartBatch(_prefs()))
    assert clock.drain() == 0
    assert session.snapshot().success_count == 1
    assert reports[-1].ledger == RunLedger(1, 0)

    session.apply(AddPaths([_touch(tmp_path / "new.pdf")]))
    session.apply(StartBatch(_prefs()))
    assert clock.drain() == 0
    snap = session.snapshot()
    assert snap.success_count == 2
    assert snap.phase is BatchPhase.IDLE
    assert reports[-1].ledger == RunLedger(1, 0)
    assert reports[-1].text == "本批完成：成功 1、失败 0"


def test_stop_publishes_no_report(tmp_path: Path) -> None:
    session = BatchSession()
    reports = _reports(session)
    clock = session.manual_clock
    assert clock is not None
    session.apply(AddPaths([_touch(tmp_path / "a.pdf"), _touch(tmp_path / "b.pdf")]))
    session.apply(StartBatch(_prefs()))
    assert session.snapshot().success_count == 1
    assert reports == []
    session.apply(StopBatch())
    stopped = session.snapshot()
    assert stopped.phase is BatchPhase.IDLE
    assert stopped.waiting_count == 1
    assert stopped.success_count == 1
    assert reports == []
    assert clock.advance() is False


def test_one_failure_stays_in_the_report_and_the_batch_continues(tmp_path: Path) -> None:
    script = SubmitScript((SubmitFailed("缺纸"),))
    session = BatchSession(submit_factory=lambda _prefs: DryRunSubmit(script))
    reports = _reports(session)
    clock = session.manual_clock
    assert clock is not None
    session.apply(AddPaths([_touch(tmp_path / "bad.pdf"), _touch(tmp_path / "good.pdf")]))
    session.apply(StartBatch(_prefs()))
    assert clock.drain() >= 1
    snap = session.snapshot()
    assert snap.phase is BatchPhase.IDLE
    assert snap.waiting_count == 0
    assert snap.items[0].status is ItemStatus.FAILED
    assert snap.items[0].failure_reason == "缺纸"
    assert snap.items[1].status is ItemStatus.SUCCESS
    assert reports[-1].text == "本批完成：成功 1、失败 1"


def test_mixed_kinds_share_one_finish_line(tmp_path: Path) -> None:
    session = BatchSession()
    reports = _reports(session)
    clock = session.manual_clock
    assert clock is not None
    session.apply(
        AddPaths(
            [
                _touch(tmp_path / "a.pdf"),
                _touch(tmp_path / "b.docx"),
                _touch(tmp_path / "c.png"),
                tmp_path / "gone.jpg",
            ]
        )
    )
    session.apply(StartBatch(_prefs(wait=True)))
    assert clock.drain() >= 1
    snap = session.snapshot()
    assert [item.kind for item in snap.items] == ["pdf", "docx", "image", "image"]
    assert snap.items[3].failure_reason == "文件不存在"
    assert snap.success_count == 3
    assert snap.failed_count == 1
    assert reports[-1].ledger == RunLedger(success=3, failed=1)
    assert reports[-1].text == "本批完成：成功 3、失败 1"


def test_dry_run_does_not_read_the_spooler(tmp_path: Path) -> None:
    def probe(_printer: str | None) -> SpoolerCount:
        raise AssertionError("dry run must not read the spooler")

    session = BatchSession(spooler=probe)
    reports = _reports(session)
    clock = session.manual_clock
    assert clock is not None
    session.apply(AddPaths([_touch(tmp_path / "a.pdf"), _touch(tmp_path / "b.docx")]))
    session.apply(StartBatch(_prefs(dry_run=True, wait=True, printer="HP Laser")))
    assert clock.drain() >= 1
    assert session.snapshot().success_count == 2
    assert reports[-1].ledger == RunLedger(2, 0)


def test_queue_hold_releases_only_when_the_printer_is_empty(tmp_path: Path) -> None:
    seen: list[str | None] = []
    depths = iter((SpoolerCount(2), ProbeFailed("无法读取打印队列"), SpoolerCount(0)))

    def probe(printer: str | None) -> SpoolerCount | ProbeFailed:
        seen.append(printer)
        return next(depths)

    session = BatchSession(submit_factory=lambda _prefs: DryRunSubmit(), spooler=probe)
    reports = _reports(session)
    clock = session.manual_clock
    assert clock is not None
    session.apply(AddPaths([_touch(tmp_path / "a.pdf"), _touch(tmp_path / "b.png")]))
    session.apply(StartBatch(_prefs(dry_run=False, wait=True, printer="HP Laser")))
    assert seen == []
    assert session.snapshot().items[0].status is ItemStatus.SUCCESS
    assert session.snapshot().items[1].status is ItemStatus.WAITING

    assert clock.advance()
    held = session.snapshot()
    assert seen == ["HP Laser"]
    assert held.phase is BatchPhase.RUNNING
    assert held.items[0].status is ItemStatus.SUCCESS
    assert held.items[1].status is ItemStatus.WAITING
    assert reports == []

    assert clock.advance()
    assert session.snapshot().items[1].status is ItemStatus.WAITING
    assert clock.advance()
    done = session.snapshot()
    assert done.phase is BatchPhase.IDLE
    assert done.success_count == 2
    assert done.waiting_count == 0
    assert reports[-1].text == "本批完成：成功 2、失败 0"
    assert seen == ["HP Laser", "HP Laser", "HP Laser"]


def test_wait_off_does_not_probe(tmp_path: Path) -> None:
    def probe(_printer: str | None) -> SpoolerCount:
        raise AssertionError("wait off must not read the spooler")

    session = BatchSession(submit_factory=lambda _prefs: DryRunSubmit(), spooler=probe)
    clock = session.manual_clock
    assert clock is not None
    session.apply(AddPaths([_touch(tmp_path / "a.pdf"), _touch(tmp_path / "b.pdf")]))
    session.apply(StartBatch(_prefs(dry_run=False, wait=False, printer="HP Laser")))
    assert session.snapshot().success_count == 1
    assert clock.advance()
    assert session.snapshot().success_count == 2
    assert session.snapshot().phase is BatchPhase.IDLE

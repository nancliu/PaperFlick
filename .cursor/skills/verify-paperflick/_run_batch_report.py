from __future__ import annotations

import os
import shutil
import tempfile
import time
from pathlib import Path

from paperflick.core.batch import AddPaths, BatchPhase, ClearItems
from paperflick.core.printers import SpoolerCount
from paperflick.core.settings import load
from paperflick.core.submit import SubmitScript
from paperflick.ui.main_window import MainWindow


def _wait_idle(app: MainWindow) -> None:
    deadline = time.monotonic() + 8.0
    while time.monotonic() < deadline:
        app.update()
        snap = app._session.snapshot()
        if snap.phase is BatchPhase.IDLE and snap.waiting_count == 0 and snap.printing_count == 0:
            return
        time.sleep(0.02)
    snap = app._session.snapshot()
    raise AssertionError(
        f"batch still {snap.phase.value} success={snap.success_count} "
        f"failed={snap.failed_count} waiting={snap.waiting_count}"
    )


def _prove_mixed_report(app: MainWindow, root: Path, probed: list[int]) -> None:
    (root / "page.pdf").write_bytes(b"%PDF")
    (root / "note.docx").write_bytes(b"docx")
    (root / "scan.png").write_bytes(b"png")
    app._dry_var.set(True)
    app._wait_var.set(True)
    app._interval_var.set("0.05")
    app._on_interval_commit()
    assert load().dry_run is True
    assert load().wait_for_empty_queue is True
    app._session.apply(
        AddPaths(
            [
                root / "page.pdf",
                root / "note.docx",
                root / "scan.png",
                root / "gone.jpg",
            ]
        )
    )
    app._on_start()
    _wait_idle(app)
    snap = app._session.snapshot()
    assert [item.kind for item in snap.items] == ["pdf", "docx", "image", "image"]
    assert snap.success_count == 3
    assert snap.failed_count == 1
    assert snap.items[3].failure_reason == "文件不存在"
    assert app._status_label.cget("text") == "本批完成：成功 3、失败 1"
    counts = str(app._counts_label.cget("text"))
    assert "成功 3" in counts
    assert "失败 1" in counts
    assert probed == []


def _prove_queue_gate(app: MainWindow, root: Path, probed: list[int]) -> None:
    app._session.apply(ClearItems())
    app._dry_var.set(False)
    app._wait_var.set(True)
    app._interval_var.set("0.05")
    app._on_interval_commit()
    assert load().dry_run is False
    assert load().wait_for_empty_queue is True
    app._session.apply(AddPaths([root / "page.pdf", root / "scan.png"]))
    app._on_start()
    _wait_idle(app)
    snap = app._session.snapshot()
    assert snap.success_count == 2
    assert snap.failed_count == 0
    assert app._status_label.cget("text") == "本批完成：成功 2、失败 0"
    assert probed == [1, 0]


def _write_log(probed: list[int], status: str, counts: str) -> None:
    folder = Path(__file__).resolve().parent / "artifacts" / "batch-end-report"
    folder.mkdir(parents=True, exist_ok=True)
    lines = [
        "batch-end-report",
        f"status={status}",
        f"counts={counts}",
        "probes=" + ",".join(str(count) for count in probed),
    ]
    (folder / "log.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    appdata = Path(tempfile.mkdtemp(prefix="paperflick-report-appdata-"))
    os.environ["PAPERFLICK_APPDATA"] = str(appdata)
    root = Path(tempfile.mkdtemp(prefix="paperflick-report-files-"))
    probed: list[int] = []
    remaining = iter((SpoolerCount(1), SpoolerCount(0)))

    def probe(printer: str | None) -> SpoolerCount:
        del printer
        observed = next(remaining)
        probed.append(observed.jobs)
        return observed

    app = MainWindow(submit_script=SubmitScript(()), spooler=probe)
    try:
        app.update_idletasks()
        _prove_mixed_report(app, root, probed)
        _prove_queue_gate(app, root, probed)
        status = str(app._status_label.cget("text"))
        counts = str(app._counts_label.cget("text"))
    finally:
        app.destroy()
        shutil.rmtree(appdata, ignore_errors=True)
        shutil.rmtree(root, ignore_errors=True)
    _write_log(probed, status, counts)
    print("PASS batch-end-report")


if __name__ == "__main__":
    main()

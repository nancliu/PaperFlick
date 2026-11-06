from __future__ import annotations

from paperflick.core.printers import ProbeFailed, SpoolerCount, count_spooler_jobs


def test_named_printer_count_includes_only_that_queue() -> None:
    seen: list[str] = []

    def read_jobs(name: str) -> int:
        seen.append(name)
        return 4

    observed = count_spooler_jobs("HP Laser", read_jobs=read_jobs, default_printer=lambda: "Other")
    assert observed == SpoolerCount(4)
    assert seen == ["HP Laser"]


def test_blank_printer_uses_the_default_name() -> None:
    seen: list[str] = []

    def read_jobs(name: str) -> int:
        seen.append(name)
        return 0

    assert count_spooler_jobs(None, read_jobs=read_jobs, default_printer=lambda: "Default") == (
        SpoolerCount(0)
    )
    assert count_spooler_jobs("  ", read_jobs=read_jobs, default_printer=lambda: "Default") == (
        SpoolerCount(0)
    )
    assert seen == ["Default", "Default"]


def test_unreadable_queue_is_a_failed_probe() -> None:
    def boom(_name: str) -> int:
        raise OSError("spooler offline")

    failed = count_spooler_jobs("HP Laser", read_jobs=boom, default_printer=lambda: "HP Laser")
    assert isinstance(failed, ProbeFailed)
    assert failed.reason == "无法读取打印队列"
    negative = count_spooler_jobs(
        "HP Laser",
        read_jobs=lambda _name: -1,
        default_printer=lambda: "HP Laser",
    )
    assert isinstance(negative, ProbeFailed)

    def unused(_name: str) -> int:
        raise AssertionError("no printer name")

    missing = count_spooler_jobs("  ", read_jobs=unused, default_printer=lambda: "  ")
    assert isinstance(missing, ProbeFailed)

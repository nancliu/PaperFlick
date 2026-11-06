"""Settings defaults, coerce helper, and disk round-trip."""

from __future__ import annotations

import json
from pathlib import Path

from paperflick.core.settings import Settings, coerce_interval_seconds, load, save, settings_path


def test_coerce_interval_seconds() -> None:
    assert coerce_interval_seconds("5.5", 2.0) == 5.5
    assert coerce_interval_seconds("nope", 2.0) == 2.0
    assert coerce_interval_seconds("-1", 2.0) == 2.0
    assert coerce_interval_seconds(0, 2.0) == 2.0


def test_defaults_and_round_trip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PAPERFLICK_APPDATA", str(tmp_path))
    assert load() == Settings()
    assert load().interval_seconds == 2.0
    assert load().wait_for_empty_queue is False
    assert load().dry_run is False

    mutated = Settings(interval_seconds=5.5, wait_for_empty_queue=True, dry_run=True)
    save(mutated)
    assert load() == mutated
    raw = json.loads(settings_path().read_text(encoding="utf-8"))
    assert raw == {
        "interval_seconds": 5.5,
        "wait_for_empty_queue": True,
        "dry_run": True,
    }


def test_corrupt_file_returns_defaults(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PAPERFLICK_APPDATA", str(tmp_path))
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    assert load() == Settings()

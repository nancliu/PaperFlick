from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class Settings:
    interval_seconds: float = 2.0
    wait_for_empty_queue: bool = False
    dry_run: bool = False


_APP_DIR_NAME = "PaperFlick"
_SETTINGS_FILE = "settings.json"
_APPDATA_ENV = "PAPERFLICK_APPDATA"


def settings_dir() -> Path:
    override = os.environ.get(_APPDATA_ENV)
    if override:
        return Path(override)
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not set; cannot locate PaperFlick settings.")
    return Path(appdata) / _APP_DIR_NAME


def settings_path() -> Path:
    return settings_dir() / _SETTINGS_FILE


def coerce_interval_seconds(value: object, default: float = 2.0) -> float:
    """Parse a positive interval; return ``default`` when missing, invalid, or non-positive."""
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    if parsed <= 0:
        return default
    return parsed


def _coerce(raw: dict[str, Any]) -> Settings:
    defaults = Settings()
    interval = raw.get("interval_seconds", defaults.interval_seconds)
    wait = raw.get("wait_for_empty_queue", defaults.wait_for_empty_queue)
    dry = raw.get("dry_run", defaults.dry_run)
    return Settings(
        interval_seconds=coerce_interval_seconds(interval, defaults.interval_seconds),
        wait_for_empty_queue=bool(wait),
        dry_run=bool(dry),
    )


def load() -> Settings:
    path = settings_path()
    if not path.is_file():
        return Settings()
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return Settings()
    if not isinstance(data, dict):
        return Settings()
    return _coerce(data)


def save(settings: Settings) -> None:
    directory = settings_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / _SETTINGS_FILE
    payload = asdict(settings)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")

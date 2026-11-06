"""Immutable prefs captured for one Batch Start."""

from __future__ import annotations

from dataclasses import dataclass

from paperflick.core.settings import Settings


@dataclass(frozen=True, slots=True)
class BatchPrefs:
    """Prefs snapshot for one Batch run. Not a live Settings handle."""

    interval_seconds: float
    wait_for_empty_queue: bool
    dry_run: bool
    selected_printer: str | None

    @classmethod
    def from_settings(cls, settings: Settings) -> BatchPrefs:
        """Copy preference fields. selected_printer is optional until printers land."""
        selected = getattr(settings, "selected_printer", None)
        if selected is not None and not isinstance(selected, str):
            selected = None
        return cls(
            interval_seconds=settings.interval_seconds,
            wait_for_empty_queue=settings.wait_for_empty_queue,
            dry_run=settings.dry_run,
            selected_printer=selected,
        )

# BatchSession + printer catalog (wave 1)

Caller-facing surface for GitHub #2 (Dry Run Batch) and #4 (printer enum + persist).
UI owns widgets. Core owns list runtime, Batch lifecycle, and printer names.
Settings stays preferences only.

## What you import

```python
from paperflick.core.batch import (
    BatchSession,
    AddPaths,
    RemoveItems,
    ClearItems,
    StartBatch,
    PauseBatch,
    ResumeBatch,
    StopBatch,
    BatchPrefs,
    BatchSnapshot,
)
from paperflick.core.printers import list_installed_printers
from paperflick.core.settings import Settings, load, save
```

`BatchSession` is the only way to mutate Print Item list state or drive a Batch.
`list_installed_printers` is the only way to read machine printer names.
`Settings.selected_printer` is the only persisted printer choice.

## Quickstart

1. Construct one `BatchSession` per MainWindow.
2. Subscribe once; every UI refresh comes from `BatchSnapshot` or events.
3. Turn user gestures into commands via `session.apply(...)`.
4. On Start, pass a `BatchPrefs` snapshot copied from Settings (and the current selected printer name if any).
5. Dry Run is a flag on `BatchPrefs`. The session still advances statuses; it never opens a real Print Job submitter.
6. Enumerate printers for the sidebar separately. Missing or empty selection must not block Dry Run Start.

## Call site 1 — MainWindow boot and list edits (#2)

```python
# ui/main_window.py (orchestration only)

class MainWindow(ctk.CTk):
    def __init__(self, settings: Settings | None = None) -> None:
        ...
        self._settings = settings if settings is not None else load()
        self._session = BatchSession()
        self._session.subscribe(self._on_batch_event)
        self._bind_list(self._session.snapshot())

    def _on_add_files(self, paths: list[Path]) -> None:
        self._session.apply(AddPaths(paths))

    def _on_remove_selected(self, item_ids: list[ItemId]) -> None:
        self._session.apply(RemoveItems(item_ids))

    def _on_batch_event(self, event: BatchEvent) -> None:
        # Rebind rows / counts from snapshot; do not poke item fields by hand.
        self._bind_list(self._session.snapshot())
```

## Call site 2 — Start / Pause / Stop with Dry Run (#2)

```python
def _on_start(self) -> None:
    prefs = BatchPrefs.from_settings(self._settings)
    # Dry Run may start with selected_printer is None.
    self._session.apply(StartBatch(prefs=prefs))

def _on_pause(self) -> None:
    self._session.apply(PauseBatch())

def _on_resume(self) -> None:
    self._session.apply(ResumeBatch())

def _on_stop(self) -> None:
    self._session.apply(StopBatch())
```

`StartBatch` captures the prefs snapshot. Later checkbox toggles do not mutate a live Batch mid-flight unless the product later adds an explicit command for that.

## Call site 3 — Printer sidebar persist (#4)

```python
def _refresh_printer_sidebar(self) -> None:
    names = list_installed_printers()
    self._printer_menu.configure(values=[n.value for n in names])
    chosen = self._settings.selected_printer
    if chosen and any(n.value == chosen for n in names):
        self._printer_menu.set(chosen)
    elif names:
        # Show first installed name in the control; persist only on explicit pick
        # or keep prior settings value until the user chooses.
        self._printer_menu.set(chosen or names[0].value)

def _on_printer_picked(self, name: str) -> None:
    self._settings = Settings(
        interval_seconds=self._settings.interval_seconds,
        wait_for_empty_queue=self._settings.wait_for_empty_queue,
        dry_run=self._settings.dry_run,
        selected_printer=name,
    )
    save(self._settings)
```

Printer catalog never writes list/Batch state. Batch never writes Settings.

## Parallel branch write map

| Branch | Owns (disjoint writes) |
| --- | --- |
| #2 Dry Run Batch | `core/batch/**`, `core/submit/**`, list/toolbar widgets, Start/Pause/Stop wiring |
| #4 printers | `core/printers.py`, `Settings.selected_printer` field + coerce/load/save, sidebar printer control |
| Shared conflict surface | `ui/main_window.py` layout composition only |

No shared write of Print Item rows, reducer state, or submit ports.

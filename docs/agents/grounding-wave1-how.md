# Grounding: wave 1 (#2 Dry Run + #4 printers)

Source: how explainer on main @ bff5988.

## Current system

- Boot: `python -m paperflick` → `ui/main_window.run` → `MainWindow` + `core/settings` load/save.
- Settings fields today: `interval_seconds`, `wait_for_empty_queue`, `dry_run`.
- No Print Item list, Batch runner, or printer enum yet.

## Domain (GLOSSARY)

- Print Item: row with path, type, Orientation, status (Waiting / Printing / Success / Failed …).
- Batch: one Start covers ordered items; failures do not stop the batch.
- Dry Run: same scheduler/state machine; no real Print Job at the submit boundary.
- Settings: user preferences only. Not list runtime state.

## Issue acceptance

### #2

- Add/remove files or folders populates Print Item list.
- Dry Run Batch advances statuses serially at interval with pause/stop.
- No Print Job to a real printer.

### #4

- Sidebar enumerates installed printers.
- Selected printer persists in settings across restart.

## Seam rules from how

1. Settings = preferences (`selected_printer` to add). Not Print Item list.
2. List state in models + UI bind; schedule clock in `queue_runner`; printer names in `printers` + one Settings field.
3. MainWindow orchestrates only. Start passes list snapshot + Settings snapshot to runner.
4. #2 and #4 conflict surface should be only `main_window.py` layout + Settings field extend.
5. Dry Run must still advance states; divert only at Print Job submit.
6. Missing printer must not block Dry Run Start.

## Planned paths (product plan §9)

- `core/models.py`, `core/queue_runner.py`, `core/printers.py`
- UI list/sidebar widgets; handlers later for real print

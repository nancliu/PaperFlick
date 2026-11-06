# Wave 1 synthesis (#2 + #4)

## Rubric

1. Dry Run divert only at Print Job submit, encoded in types/structure
2. #2 / #4 disjoint core file writes; conflict only `main_window` (+ Settings field)
3. Deep public surface; MainWindow orchestrates only
4. Settings = preferences; no list runtime in AppData
5. Print Item status machine is domain-owned, not UI timers
6. Real sinks can land later without rewriting Start

## Cross-judge

Skipped. `arena cross-judge pool` is `auto` (same family as parent). Parent scored alone.

## Base

**Candidate B** (`BatchSession` + commands/events/pure `reduce` + `PrintSubmitPort`).

Why: one writer of Batch state; MainWindow speaks `apply` / `snapshot` / `subscribe` only; submit divert is a port. Candidate A’s dual `PrintList` + `BatchRuntime` + event-merge is correct concurrency thinking but gives agents two mutation paths and a freeze protocol to keep in sync.

## Grafts from candidate A

1. **Sink chosen at Start, not re-checked in the tick loop.** Keep B’s `PrintSubmitPort`; at Start, wave 1 always binds `DryRunSubmit`. If `settings.dry_run` is false, refuse Start with a clear UI message (no real sink yet). Do not scatter `if dry_run` inside reduce.
2. **`PrinterCatalog`-style boundary.** Implement `list_installed_printers()` in `core/printers.py` and a thin `brand`/`resolve` helper so Settings stores raw `str | None` only.
3. **`PathIntake` (or equivalent) at AddPaths.** Folder expansion and kind sniff stay behind the session command, not in the button callback.
4. **Parallel write map (final):**

| Branch | Owns |
| --- | --- |
| #2 | `core/batch/**`, `core/submit/**`, list/toolbar UI, Start/Pause/Stop wiring |
| #4 | `core/printers.py`, `Settings.selected_printer` + coerce, printer sidebar control |
| Shared | `ui/main_window.py` layout composition only |

## Rejected from A

- Separate idle `PrintList` writer vs runtime writer (extra freeze/merge surface).
- Public `BatchPrefs` omitting `dry_run` while still reading the checkbox: keep `BatchPrefs.dry_run` for the snapshot/audit, but Start still selects the port once.

## Operator defaults (Never Block)

- `wait_for_empty_queue` during Dry Run: no-op (preference still persisted).
- Second Start while RUNNING: no-op.
- Stale selected printer after restart: keep Settings string; sidebar shows no forced match until user picks.
- Clock: session-owned with an injectable tick for tests; UI may drive ticks via `after`.

## Next

Implement #2 and #4 in parallel worktrees against this contract. Open PRs when each verifies.

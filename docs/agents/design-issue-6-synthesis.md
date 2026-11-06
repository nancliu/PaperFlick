# Issue #6 synthesis

Grounding is from the worktree on `feat/issue-6-pdf-print`. Arena runners were not spawned. This delegate cannot spawn subagents, so the two shapes below were compared here.

## How

### Overview

A Batch walks Print Items one at a time. `BatchSession` is the only writer. It waits `interval_seconds` between items, calls `PrintSubmitPort.submit` once per item, and stores `SubmitOk` as success or `SubmitFailed.reason` as `failure_reason`. Dry Run and real print share that loop. ADR 0002 says the no-op happens only at the submit boundary.

Today the boundary is still a wall. `BatchSession.apply` raises `StartNeedsDryRunError` when Dry Run is off, and `choose_submit_port` raises the same error. No Sumatra command exists. Orientation is already a policy on the Print Item (`Orientation` plus a page `shape`) resolved by `resolve_facing` to `Facing` or None. The list UI already prints `failure_reason`.

### Key Concepts

- **Print Item.** One row. Kind, orientation policy, page shape, status, optional failure reason.
- **Print Job.** One handoff to a print engine. For PDF that engine is SumatraPDF.
- **PrintSubmitPort.** `submit(SubmitRequest) -> SubmitOk | SubmitFailed`. Dry Run and real print both implement it.
- **Facing.** The direction Sumatra is allowed to force. None means leave the printer's current default alone.

### How It Works

Start and reprint build a `BatchPrefs` snapshot and `apply` it. On the idle-to-running edge the session asks the factory for a port and immediately submits the first waiting item. Later items wait for the manual clock or Tk `after`. A failed submit marks that row and still schedules the next tick. Pause cancels the tick. Stop returns to idle and drops the port.

`DryRunSubmit` runs `preflight` (missing or unreadable file) then an optional `SubmitScript`. It never starts a process. `choose_submit_port` returns that port only when `prefs.dry_run` is true.

### Where Things Live

- `src/paperflick/core/submit/port.py` owns the request and the two results.
- `src/paperflick/core/submit/dry_run.py` owns Dry Run.
- `src/paperflick/core/submit/preflight.py` owns file checks shared by every port.
- `src/paperflick/core/batch/session.py` owns the interval loop and the Dry Run wall.
- `src/paperflick/core/batch/types.py` owns `resolve_facing`.
- `src/paperflick/ui/main_window.py` catches `StartNeedsDryRunError` and shows a dialog.

### Gotchas

- Default settings have Dry Run off. The wall is the only thing preventing a real submit.
- `wait_for_empty_queue` is stored and still does nothing. Issue #6 does not ask for the spooler gate.
- There is no command yet to change a row's orientation policy (#5). Auto still resolves from the page shape measured at add time.
- DOCX and images are #7 and #8. This PR must not print them.

## Candidates

### A. One PDF port behind the existing seam

`SumatraJob` is the print command (executable, document, printer name or default, facing or none). `sumatra_argv` is a pure function from that job to Sumatra's silent-print vector. `find_sumatra` resolves an executable. `PdfSumatraSubmit.submit` preflights, rejects non-PDF with `SubmitFailed`, rejects a missing executable with `SubmitFailed`, then runs one process. `choose_submit_port` returns `DryRunSubmit` or `PdfSumatraSubmit`. Delete the start wall.

### B. Format handler registry

A registry maps `DocKind` to a handler. PDF is the Sumatra handler. DOCX and image handlers return "not supported" until later issues. Session still only sees `PrintSubmitPort`.

## Screen

A hides the command line, the search, and the process behind one `submit` call. Callers do not learn Sumatra flags. B adds a registry, a handler interface, and two stub handlers for formats this PR must not implement. The next agent can copy either the stub or a second print path. That is two ways to say "not yet", and a shallow module around one real command.

## Synthesis decision

Ship A. Graft one idea from B. A non-PDF row is `SubmitFailed("该格式暂不支持打印")` so a mixed list still finishes. Do not add the registry.

`PAPERFLICK_SUMATRA`, when set, is the only candidate. A missing override does not fall through to an installed SumatraPDF, so a verify fake cannot print on a machine that has the real program.

PrinterDefault omits `portrait` and `landscape`. No selected printer uses `-print-to-default`. Process timeout is 120 seconds and fails that item. `等队列清空` stays a no-op.

## Operator defaults

- Non-PDF fails the item instead of refusing the whole Start.
- An explicit Sumatra path that is missing fails closed.
- Direction is Sumatra's `portrait` / `landscape` token, or omitted.
- The wave-1 `StartNeedsDryRunError` wall is removed in the same change as its callers.

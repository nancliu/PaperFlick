# Candidate A: reprint as one composed command, Dry Run fails on real preconditions

## Problem

Issue #9 asks that a failed Print Item keep its reason while the Batch continues, that the user can select only failed items, reprint them, and clear succeeded rows, and that Dry Run can produce a failure without a printer. `BatchSession._on_interval_tick` already marks FAILED with `failure_reason` and moves on. Dry Run never reaches that branch because `DryRunSubmit` always returns ok. The list row does not show the reason. Constraints from grounding: `BatchSession` stays the single writer, Dry Run diverts only at `PrintSubmitPort`, reprint reuses `StartBatch` instead of a second scheduler, and the UI must not be able to apply half a reprint. Today `apply` recognizes a start by `isinstance(command, StartBatch)`, so any new starting command either bypasses the Dry Run guard and first tick or copies that check.

## Usage (caller's view)

See `USAGE.md`. The UI issues `ReprintFailed(StartBatch(prefs))` and `ClearSucceeded()`, reads `snapshot.ids_with(ItemStatus.FAILED)` for selection, and calls `ItemListPanel.check_only(ids)`. An agent injects a Dry Run failure by renaming a file after adding it, and restores it to prove reprint succeeds.

## Shape

**Commands.** `ReprintFailed` holds a `StartBatch`, not bare prefs. `starting_batch(command)` is the one function that says which commands start a Batch. The session's Dry Run guard calls it, and reduce's `_reprint_failed` delegates to the existing `_start` with the embedded command. Reset and start happen inside one reduce call, so there is no intermediate state a listener or a raising guard can leave behind. The guard runs before reduce, so a refused start resets nothing (per make-operations-idempotent and type-system-discipline).

**Session reacts to transitions.** `apply` creates the submitter and fires the first tick when reduce moved the phase from IDLE to RUNNING, reading prefs from `state.prefs`. The command type no longer matters after the guard. This is the change that lets reprint reuse the whole start path with zero session code specific to reprint (per redesign-from-first-principles).

**Reprint preconditions.** `ReprintFailed` is a no-op unless the Batch is IDLE and at least one item is FAILED. The cursor only moves forward, so resetting rows during a RUNNING Batch would leave them behind the cursor. Refusing is simpler and honest. A second click while running hits the duplicate-start no-op `_start` already has.

**One removal path.** `ClearSucceeded`, `ClearItems`, and `RemoveItems` all go through `_retain(state, keep)`, which remaps the cursor to the count of kept rows before it (per subtract-before-you-add). `ClearSucceeded` never removes PRINTING rows, so it is safe in any phase.

**Submit result as a union.** `SubmitResult` becomes `SubmitOk | SubmitFailed(reason: str)`. Today `SubmitResult(ok=False)` with no reason type-checks, which would produce a FAILED row with no reason and break acceptance item one. The union makes that unrepresentable. Only `session.py` and `dry_run.py` construct or read it, and no tests reference it.

**Dry Run failure is real, not scripted.** `preflight(request)` checks that the file exists and is readable. `DryRunSubmit` runs it, and the future real submit runs it first too. Dry Run then fails exactly where real print would, with the same reason text. There is no fault-injection flag, env var, or test-only port in the shipped app. Unit tests that need arbitrary failures pass a fake port through the existing `submit_factory`.

**Selection stays in the view.** Checkbox state never enters `BatchState`. "只勾选失败项" reads the snapshot and calls `check_only`. Reprint calls it after a successful apply, with ids captured beforehand.

**Interface depth.** The public surface grows by two commands, one snapshot query, and one panel method. Behind it sit the atomic reset-and-start, the guard, the cursor remap, and the first-tick scheduling. The UI never sequences more than one `apply` per button.

## Synthesis decision

TBD by arena.

## Tradeoffs accepted

- We accept that reprint also runs any WAITING rows left by an earlier Stop, in exchange for reusing `StartBatch` unchanged. Running only the reset rows would need a run scope on `BatchState`, which is a second notion of "what this Batch prints".
- We accept that reprint is unavailable while RUNNING or PAUSED, in exchange for not touching the forward-only cursor. The user stops or waits for the Batch to finish.
- We accept that injecting a Dry Run failure means touching the filesystem, in exchange for no test-only knob in the product and a Dry Run that exercises a real failure path.
- We accept a behavior change in `RemoveItems` while RUNNING (cursor remap instead of clamp), in exchange for one removal path. Today removing a row before the cursor skips the next Waiting item. This looks like scope creep. It is the cost of not adding a third removal function.

## Alternatives considered

- **UI orchestrates reprint** with `RemoveItems`-style resets then `StartBatch` as two applies. Lost because the guard can raise after the reset lands, leaving reset rows and no Batch. That is the half-apply the constraints forbid.
- **Fault-injecting port** (`DryRunSubmit(fail_matching="*bad*")` from an env var or setting). Lost on depth and honesty. It adds a knob that exists only for agents, and a pattern-matched failure fails again on reprint unless it also counts attempts per path, which means mutable state that must outlive the per-Batch submitter.
- **Selection in `BatchState`** with `SelectOnlyFailed` as a session command. Lost because it makes the single writer own view state and emits domain events for checkbox clicks, while no domain rule reads selection.

## Open questions and risks

- After Stop, should 重新打印失败项 also print the leftover WAITING rows? Candidate A says yes. The product plan's "仅这些项再跑一轮" could be read as no.
- Should 清除已成功 be disabled while RUNNING, or is removing finished rows mid-Batch acceptable? Candidate A allows it.
- Is the `RemoveItems` cursor remap acceptable inside this issue, or should it ship as its own PR first?
- `preflight` reads the file to prove readability. Is opening a large file on each submit acceptable, or should it only check existence?

## Next implementation step

Write `test_batch_reprint.py` against a scripted failing port: two items, one fails, Batch finishes with one SUCCESS and one FAILED with a reason, then `ReprintFailed` leaves zero FAILED.

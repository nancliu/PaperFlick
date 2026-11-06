# Issue #9 synthesis

## Rubric

1. Failed items stay with a non-empty reason; Batch continues
2. Select-only-failed / reprint-failed / clear-succeeded work
3. Dry Run can inject a failure for agent verification (no real printer)
4. `BatchSession` single writer; divert at `PrintSubmitPort`
5. Reprint reuses Start path; UI cannot half-apply reset without start
6. Small blast radius vs #3 worktree (`PrintItem.shape` landing in parallel)

## Cross-judge

Skipped. Parent scored alone.

## Base

**Candidate A** ([84e2b11c](84e2b11c-aca5-4aca-b02a-0e06bf0d64bc)): `ReprintFailed(StartBatch)` atomic command, session starts on IDLE→RUNNING transition, `ClearSucceeded`, selection stays in UI, `SubmitResult` as `SubmitOk | SubmitFailed(reason)`.

Why: atomic reprint beats B’s multi-`apply` loop for the half-apply constraint. Keeps `ItemStatus` so merge with #3’s `shape` field stays a field add, not an outcome rewrite.

## Grafts from candidate B ([1a2aa77c](1a2aa77c-110c-425b-9c42-432e830ee3ec))

1. **`SubmitScript` on `DryRunSubmit`** for agent injection (`Rejected` then `Submitted`). Product default empty script → always ok. Wire `MainWindow(submit_script=...)` / `BatchSession(submit_factory=...)` for verify-paperflick. Keep A’s file preflight as an additional real failure path (missing file).
2. **Row label shows reason** (`失败 · reason` or ` [失败]  reason`).
3. Document that after a finished Batch, reprint only re-runs former failures (leftover WAITING after Stop also run; accept and note).

## Rejected from B

- Replacing `ItemStatus` + `failure_reason` with `ItemOutcome` union in this PR (correct direction, too much merge risk with #3).
- Multi-command `commands_for_reprint` + separate `RequeueFailed` without an atomic compose (half-apply risk if a later guard appears).

## Operator defaults (Never Block)

- Reprint only when IDLE (A). User stops or waits.
- ClearSucceeded allowed while RUNNING; keeps WAITING/PRINTING/FAILED.
- RemoveItems cursor remap via shared `_retain`: include if tests stay green; otherwise leave a follow-up note.
- No Settings field for fail injection.

## Next

Implement in `printer-advance-wt-9`. Open PR linking Fixes #9. Extend verify-paperflick with Dry Run inject + reprint path when the feature lands.

## Problem

Issue 9 keeps a failed Print Item on the list, shows its reason, and lets the Batch continue. The operator can check only the failed rows, reset those rows and start again, and remove the succeeded rows. An agent needs one Dry Run failure without a printer.

`BatchSession` already records a rejected submit and keeps scanning. `DryRunSubmit` always returns success, so Dry Run never hits that branch. The list shows a status word and hides the reason. `PrintItem` stores `ItemStatus` beside an optional `failure_reason`, so a success can carry a reason and a failure can omit one.

Three constraints fix the shape. `BatchSession` stays the only writer of the list. Injection stays on the submit port. Reprint reuses `StartBatch`.

## Usage (caller's view)

`USAGE.md` is the caller spec. The snippets below match it. `sketch.py` defines the names they import.

The reprint button persists settings, asks `commands_for_reprint` for existing commands, and applies them in order. A refused Start leaves the failed rows alone.

```python
def _on_reprint_failed(self) -> None:
    self._persist()
    prefs = BatchPrefs.from_settings(self._settings)
    snapshot = self._session.snapshot()
    try:
        commands = commands_for_reprint(snapshot, prefs)
    except StartNeedsDryRunError as exc:
        self._status_label.configure(text=str(exc))
        messagebox.showinfo("无法开始", str(exc), parent=self)
        return
    if not commands:
        return
    self._item_list.select_only_failed(snapshot)
    for command in commands:
        self._session.apply(command)
```

The agent shares one script across every `DryRunSubmit` that session builds.

```python
script = SubmitScript((Rejected("injected jam"),))
session = BatchSession(submit_factory=lambda prefs: DryRunSubmit(script))
```

The window takes the same script only when an agent passes it.

```python
MainWindow(submit_script=SubmitScript((Rejected("injected jam"),)))
```

**只勾选失败项** calls `select_only_failed`. **清除已成功** calls `apply(ClearSucceeded())`. Both are in `USAGE.md`.

## Shape

Each Print Item has one outcome. The variants are `Waiting`, `Printing`, `Succeeded`, and `Failed`. `Failed` stores a reason `parse_reason` has accepted. `ItemStatus` and `failure_reason` are deleted in the same change, per migrate-callers-then-delete-legacy-apis and type-system-discipline. The outcome is the lifecycle, per model-the-domain. The pair is replaced as if the reason had always belonged only to `Failed`, per redesign-from-first-principles. The outcome union and the script are fixed before the button handlers, per foundational-thinking.

`RequeueFailed` turns every `Failed` into `Waiting`. The scanner starts at `cursor`, and a requeued row can sit before that index. When a row changes, the reducer sets `cursor` to 0 so the row is seen. A second apply finds no `Failed` and leaves `cursor` alone, per make-operations-idempotent. That cursor rule stays inside this reducer, per minimize-reader-load.

`ClearSucceeded` removes `Succeeded` rows and sets `cursor` to the count of kept rows that stood before the old cursor. `Waiting` and `Printing` stay. On a finished Batch the list is the failed rows, which is the case in 产品规划 §5.

The reprint button has no reducer of its own. `commands_for_reprint` reads the snapshot and returns commands the session already knows. When nothing has failed, the function returns an empty tuple. `IDLE` with Dry Run off raises `StartNeedsDryRunError` before any requeue. `IDLE` with Dry Run on returns `RequeueFailed` and `StartBatch`. `PAUSED` returns `RequeueFailed` and `ResumeBatch`, on the port the original Start created. `RUNNING` returns `RequeueFailed` only, and the live tick sees `cursor` 0. That is the existing scheduler, per laziness-protocol.

`select_only_failed` writes checkboxes. It does not call `apply`. The session writes items, the list writes checks, and the script writes its own index, per separate-before-serializing-shared-state.

Dry Run injection is a `SubmitScript` held by `DryRunSubmit`. Each `submit` reads one step and then advances. Past the last step the result is `Submitted`. `choose_submit_port` still builds `DryRunSubmit()` with an empty script, so the product window keeps succeeding. An agent closes one script over the factory. The next Start, including reprint, continues that script. `BatchPrefs` has no fail index. `apply_submit_result` maps `Submitted` to `Succeeded` and `Rejected` to `Failed`, and the tick then looks for the next `Waiting`. The port is the boundary, per boundary-discipline. The product window has no control that forces a failure, per experience-first. One reprint click selects, resets, and starts.

`count_outcomes` and `outcome_label` key off the outcome type. An unknown type raises `KeyError`, per encode-lessons-in-structure.

On interface depth, callers use two commands, `commands_for_reprint`, one checkbox method, and one script. They do not set `cursor`, clear a reason on success, or branch the tick. The public interface stays that small because the outcome type and the script hold those rules.

## Synthesis decision

TBD. Arena writes this section when it picks a base. This file does not.

## Tradeoffs accepted

- We accept updating every `ItemStatus` caller in this change, in exchange for a row that cannot pair a success with a reason.
- We accept that reprint after **停止** also submits rows that are still `Waiting`, in exchange for `StartBatch` and one scanner. A finished Batch has no `Waiting` rows, so that pass submits only the former failures.
- We accept that the product window has no injection control, in exchange for keeping a fail index out of Settings. Agents pass `SubmitScript`.
- We accept the shared label `失败 · reason`, in exchange for leaving the row layout alone.
- We accept `ClearSucceeded` while the Batch is `RUNNING`, in exchange for one command with no phase gate.

## Alternatives considered

Three new commands plus a fail-nth field on `BatchPrefs`. A select command would copy checkbox state into the Batch. A reprint command would start the clock itself. The field would put a verification number on the prefs snapshot. Callers would learn three commands and a numeric policy. This shape gives them `commands_for_reprint` over commands that already exist, and a script the port owns. The public interface is smaller, and the cursor rule stays hidden.

Keep `ItemStatus` and add only `RequeueFailed` and `ClearSucceeded`. The diff is smaller. Every transition still has to remember the optional string, and a success can still carry a reason. The fields look familiar and hide less.

A new outcome for rows the scanner should skip, so reprint can leave them out. That is a second queue in the item list. `StartBatch` would stop meaning "scan `Waiting`". The plan's "only these items" already holds for a finished Batch, which is the path 产品规划 §5 draws.

## Open questions and risks

Should `ClearSucceeded` also remove `Waiting` rows while a Batch is still running, so the list is only failed rows in that case too? This design keeps `Waiting`.

`SubmitScript` advances inside `submit`. The tick submits once per claim. A later retry has to take one result for that claim, or the next step is skipped.

## Next implementation step

Replace `ItemStatus` and `failure_reason` with `ItemOutcome` and the `SubmitResult` union, and map the tick through `apply_submit_result` before adding the commands.

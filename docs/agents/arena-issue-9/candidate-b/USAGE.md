# Handle a failed Print Item

Wire three list actions and one Dry Run script. The Batch keeps running after a failed submit. The failed row stays, and its reason shows on that row.

`BatchSession` remains the only writer of the list. Reprint calls `StartBatch` or `ResumeBatch`. Dry Run injection stays inside `DryRunSubmit`.

## Show the reason and keep going

The tick already claims the next Waiting row after a rejected submit. Point that result at `apply_submit_result`. `Submitted` becomes `Succeeded`. `Rejected` becomes `Failed` with the same reason. Then the tick calls `_find_next_waiting` as it does today.

The row label comes from `outcome_label`. A failed file `a.pdf` with reason `injected jam` reads `a.pdf  [失败 · injected jam]`.

New rows from `expand_paths` use `Waiting()`. Delete `ItemStatus` and `failure_reason` in the same change. Events use `ItemOutcomeChanged`.

## Select only the failed rows

Add a list-toolbar button **只勾选失败项**. It only changes checkboxes.

```python
def _on_select_only_failed(self) -> None:
    self._item_list.select_only_failed(self._session.snapshot())
```

`select_only_failed` checks each row whose outcome is `Failed` and clears the other checks. The write is the checkbox set. `selected_ids` then returns those ids, and **移除所选** already removes them.

## Reprint the failed rows

Add **重新打印失败项** on the same toolbar. The handler persists settings, builds `BatchPrefs` the way **开始** does, and asks `commands_for_reprint` for the commands.

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

Check the boxes before `apply`. The snapshot still has `Failed` rows at that moment. The later rebind keeps those checks.

`commands_for_reprint` reads `snapshot.failed_count` and `snapshot.phase`.

- When `failed_count` is 0, it returns an empty tuple. The handler returns and does not start the Batch.
- When the phase is `IDLE` and `prefs.dry_run` is false, it raises `StartNeedsDryRunError` and leaves every `Failed` row in place.
- When the phase is `IDLE` and Dry Run is on, it returns `RequeueFailed` and then `StartBatch(prefs)`.
- When the phase is `PAUSED`, it returns `RequeueFailed` and then `ResumeBatch`. The port from the original Start stays. The checkbox is not read again.
- When the phase is `RUNNING`, it returns `RequeueFailed` only.

`RequeueFailed` turns every `Failed` into `Waiting`. `commands_for_reprint` ignores checkboxes. One click reprints every failed row.

`StartBatch` from `IDLE` is the same command as **开始**. The first submit still happens inside that `apply`. `ResumeBatch` waits for the interval, the same as **继续**. A paused reprint waits one interval.

`StartBatch` scans every `Waiting` row. After a finished Batch, the only `Waiting` rows are the ones `RequeueFailed` just reset. That pass submits only former failures. After **停止**, rows that were still `Waiting` are submitted too.

## Clear the succeeded rows

Add **清除已成功** on the same toolbar.

```python
def _on_clear_succeeded(self) -> None:
    self._session.apply(ClearSucceeded())
```

`ClearSucceeded` removes `Succeeded` rows. `Failed`, `Waiting`, and `Printing` stay. On a finished Batch the list is the failed rows. `ClearItems` still removes every row. The two commands stay different.

## Inject one Dry Run failure

`choose_submit_port` still returns `DryRunSubmit()` with an empty script. The product window keeps succeeding, and `run()` still calls `MainWindow()` with no script.

An agent that needs one failure shares one `SubmitScript` across Starts. The first submit is `Rejected`. Later submits, including the reprint, are `Submitted` because the script is past its last step.

```python
script = SubmitScript((Rejected("injected jam"),))
session = BatchSession(submit_factory=lambda prefs: DryRunSubmit(script))
session.apply(AddPaths([path_a, path_b]))
session.apply(StartBatch(prefs))
clock = session.manual_clock
assert clock is not None
clock.drain()
snap = session.snapshot()
for command in commands_for_reprint(snap, prefs):
    session.apply(command)
```

`StartBatch` submits `path_a` immediately. After `drain`, `path_a` is `Failed` with reason `injected jam`. `path_b` is `Succeeded`. The phase is `IDLE`. The reprint `StartBatch` submits `path_a` again through the same script object. That step is `Submitted`, so `path_a` becomes `Succeeded`. The Batch reaches `IDLE` with no printer.

To see the same failure in the window, pass the script at construction. The product launch keeps calling `MainWindow()` with no script.

```python
MainWindow(submit_script=SubmitScript((Rejected("injected jam"),)))
```

That keyword installs `submit_factory=lambda prefs: DryRunSubmit(script)`. Settings stays unchanged. The toolbar has no injection control. The factory returns `DryRunSubmit`, which is the product port.

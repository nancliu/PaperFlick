# Candidate A usage: failed Print Items, reprint, Dry Run preflight

Candidate A adds two Batch commands and one submit-boundary check. Selection stays a view concern.

## Batch commands

```python
from paperflick.core.batch import (
    BatchSession,
    ClearSucceeded,
    ItemStatus,
    ReprintFailed,
    StartBatch,
)

session.apply(StartBatch(prefs))

# Reset every FAILED item to WAITING and start, in one reduce.
# The Dry Run guard runs on the embedded StartBatch before anything resets.
session.apply(ReprintFailed(StartBatch(prefs)))

# Drop SUCCESS rows. FAILED, WAITING, and PRINTING rows stay.
session.apply(ClearSucceeded())

failed = session.snapshot().ids_with(ItemStatus.FAILED)
```

`ReprintFailed` is a no-op unless the Batch is IDLE and at least one item is FAILED. It never resets without starting, and never starts without resetting.

## Dry Run failure, no printer

Dry Run runs the same preflight a real submit will run: the Print Item's file must still exist and be readable. To inject a failure, make the file disappear after adding it. To verify reprint, put it back.

```python
session.apply(AddPaths([good, bad]))
bad.rename(bad.with_suffix(".hidden"))
session.apply(StartBatch(prefs))           # bad -> FAILED "文件不存在", good -> SUCCESS
snap = session.snapshot()
assert snap.failed_count == 1 and snap.success_count == 1

bad.with_suffix(".hidden").rename(bad)
session.apply(ReprintFailed(StartBatch(prefs)))
assert session.snapshot().failed_count == 0
```

## Call sites

`ui/main_window.py`, failure toolbar:

```python
def _on_select_only_failed(self) -> None:
    self._item_list.check_only(self._session.snapshot().ids_with(ItemStatus.FAILED))

def _on_reprint_failed(self) -> None:
    self._persist()
    failed = self._session.snapshot().ids_with(ItemStatus.FAILED)
    try:
        self._session.apply(ReprintFailed(StartBatch(BatchPrefs.from_settings(self._settings))))
    except StartNeedsDryRunError as exc:
        self._show_start_error(exc)
        return
    self._item_list.check_only(failed)

def _on_clear_succeeded(self) -> None:
    self._session.apply(ClearSucceeded())
```

`ui/item_list.py`, row label carries the reason:

```python
ctk.CTkLabel(row, text=_row_text(item), anchor="w")
# "bad.pdf  [失败]  文件不存在"
```

`tests/test_batch_reprint.py`, failure driven by a fake port:

```python
session = BatchSession(submit_factory=lambda _p: ScriptedSubmit({bad_id: "卡纸"}))
```

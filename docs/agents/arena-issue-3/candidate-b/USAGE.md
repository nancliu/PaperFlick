# Show the first-page shape on add

A new Print Item still enters through `BatchSession.apply`. Its Orientation stays Auto. The list text shows the first-page shape, `横向` or `纵向`. A file added later stays Auto when an earlier row already carries an Orientation override.

## What you import

```python
from paperflick.core.batch import AddPaths, BatchSession, BatchSnapshot, ListRow
```

`AddPaths` has one field, `paths`. `BatchSnapshot.rows` is what the widget binds. `ListRow.geometry_label` is `横向` or `纵向`.

Settings, `BatchPrefs`, and Dry Run submit keep their current fields.

The widget imports `AddPaths` and the snapshot types from `paperflick.core.batch`. Tests that want the reading import `read_first_page` from `paperflick.core.batch.geometry`.

## Quickstart

1. Keep one `BatchSession` on the window.
2. On add, call `apply(AddPaths(paths))`.
3. On `ItemsChanged`, read `session.snapshot().rows`.
4. Draw `row.name`, `row.geometry_label`, and the existing status word.
5. Leave the next add on the same `AddPaths(paths)` call. That call carries paths only.

A failed read logs one warning and the row label is `纵向`. The widget draws that label from the snapshot.

## Call site 1. MainWindow add

```python
# ui/main_window.py

def _on_add_files(self) -> None:
    paths = filedialog.askopenfilenames(parent=self, title="选择文件")
    if not paths:
        return
    self._session.apply(AddPaths([Path(p) for p in paths]))


def _on_add_folder(self) -> None:
    folder = filedialog.askdirectory(parent=self, title="选择文件夹")
    if not folder:
        return
    self._session.apply(AddPaths([Path(folder)]))


def _on_batch_event(self, _event: BatchEvent) -> None:
    self._bind_list(self._session.snapshot())
```

`AddPaths` receives paths only. The window passes those paths through.

## Call site 2. ItemListPanel.bind_snapshot

```python
# ui/item_list.py

def bind_snapshot(self, snapshot: BatchSnapshot) -> None:
    previous = {item_id for item_id, var in self._row_vars.items() if var.get()}
    # ... clear existing row widgets ...
    if not snapshot.rows:
        # empty label: 尚未添加打印项
        return
    for row in snapshot.rows:
        checked = row.id in previous
        status = _STATUS_LABEL.get(row.status, row.status.value)
        text = f"{row.name}  {row.geometry_label}  [{status}]"
        # checkbox bound to row.id, label text as above
```

A wide first page comes back as `deck.pdf  横向  [等待]`. A tall first page, a square page, or a file that could not be read comes back as `scan.png  纵向  [等待]`. `ListRow` carries the id, the name, the status, and `geometry_label`.

## Call site 3. reduce on AddPaths

```python
# core/batch/reduce.py

def _add_paths(
    state: BatchState, command: AddPaths
) -> tuple[BatchState, list[BatchEvent]]:
    births = intake_paths(command.paths)
    if not births:
        return state, []
    state.rows.append_births(births)
    items = list(state.rows.items())
    return state, [ItemsChanged(), _counts_event(items)]
```

`intake_paths` takes paths and returns births. `append_births` appends those births and leaves the Orientation of stored rows unread. A second `AddPaths`, after an earlier row was overridden, still goes through this function, and the new Print Item is Auto.

Issue 5 will add a command that calls `BatchRows.override_policy` for existing ids. This change leaves that command off `apply`. `override_policy` stores no default for `intake_paths` or `append_births` to read.

# Candidate A usage: Page Shape is a fact, Orientation is a policy

Every Print Item carries two orthogonal things.

- `orientation: Orientation` is the user's **policy** (Auto / Landscape / Portrait / PrinterDefault). It is born `AUTO` and only an explicit per-item command may change it.
- `shape: PageShape` is a **fact** about the file, read once at AddPaths. It is either `Measured(width, height)` or `Unread(reason)`.

The only way to turn the two into a page direction is `resolve_facing(policy, shape) -> Facing | None`. `Facing` has exactly two members (`LANDSCAPE`, `PORTRAIT`), so a resolved direction can never be stored back into the policy field by mistake. `None` means "leave it to the printer".

## Call site 1. AddPaths intake (core)

`path_intake` stops guessing kinds itself. It asks the format registry once per file and builds the row through the only constructor that exists for new rows.

```python
from paperflick.core.batch.formats import probe
from paperflick.core.batch.types import PrintItem

def _append_file(path: Path, seen: set[Path], items: list[PrintItem]) -> None:
    ...dedupe by resolved path...
    items.append(PrintItem.added(path, probe(path)))
```

`PrintItem.added` has no `orientation` parameter. A new row is `AUTO` + `WAITING` by construction, so no session-level "last bulk Orientation" can leak into it. `probe` never raises. A missing, corrupt, `.doc`, or unknown file comes back as `Unread(reason)`, and `probe` writes one `logging.warning` naming the path and reason.

## Call site 2. List row label (UI)

```python
from paperflick.core.batch import Facing, Orientation, resolve_facing

_FACING_LABEL = {Facing.LANDSCAPE: "横向", Facing.PORTRAIT: "纵向"}

def orientation_label(item: PrintItem) -> str:
    facing = resolve_facing(item.orientation, item.shape)
    if item.orientation is Orientation.AUTO:
        return f"自动·{_FACING_LABEL[facing]}"
    if facing is None:
        return "打印机"
    return _FACING_LABEL[facing]

# row text
ctk.CTkLabel(row, text=f"{name}  {orientation_label(item)}  [{status}]", ...)
```

An Auto PDF whose first page is 842×595 shows `a.pdf  自动·横向  [等待]`. An unreadable file shows `自动·纵向` and the warning lives in the log.

## Call site 3. Real submit and the #5 hook (future, not built here)

```python
# Real submit port (later wave) asks the same resolver, never reads shape directly.
facing = resolve_facing(request.item.orientation, request.item.shape)
devmode.Orientation = {Facing.LANDSCAPE: 2, Facing.PORTRAIT: 1}.get(facing)  # None -> untouched

# #5 preview apply lands as a per-id command that rewrites policy on existing rows only.
session.apply(SetOrientation(item_ids=[...], orientation=Orientation.LANDSCAPE))
session.apply(AddPaths([Path("new.pdf")]))  # new row is still AUTO
```

`SetOrientation` is not part of this issue. The hook is structural. `BatchState` has no Orientation field, `expand_paths` takes no Orientation, and `PrintItem.added` takes no Orientation. #5 can only reach policy through `dataclasses.replace` on rows it names.

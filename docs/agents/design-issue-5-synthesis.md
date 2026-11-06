# Issue #5 synthesis

## Problem

The user sets Landscape, Portrait, or PrinterDefault from a preview and applies it to this Print Item, the same DocKind, or every row. All requires a confirm. List marks update. Dry Run must not need a printer.

The list already stores `PrintItem.orientation` separately from `shape`. `BatchSession.apply` is the only mutator. `PrintItem.added` always stamps Auto. A design that puts the same-kind rule in the window, or that remembers the last override for the next add, fights those constraints.

## Usage (caller's view)

The main window checks that exactly one row is checked, opens the preview, and on apply sends one command:

```python
session.apply(
    SetOrientation(
        anchor=item.id,
        orientation=Orientation.LANDSCAPE,
        scope=ApplyScope.SAME_KIND,
    )
)
```

The preview calls that only after the user picks a radio. For `ApplyScope.ALL` it asks `messagebox` first and skips the command on cancel. A later add is still:

```python
session.apply(AddPaths([new_file]))
```

That new row is Auto. Callers do not pass an inherited orientation.

## Shape

```python
class ApplyScope(Enum):
    THIS = "this"
    SAME_KIND = "same_kind"
    ALL = "all"

@dataclass(frozen=True, slots=True)
class SetOrientation:
    anchor: ItemId
    orientation: Orientation
    scope: ApplyScope
```

`reduce` finds the anchor, selects rows, and `replace`s `orientation` when it differs. `THIS` and `SAME_KIND` no-op if the anchor is gone. `ALL` updates every current row even if the anchor is gone, because the policy sits on the command. A second apply of the same policy emits no event.

The public surface is one command. It hides DocKind equality, the missing-anchor rule, and the idempotent write. The window keeps the confirm, the radio parse, and the image-or-fallback page. That split is per boundary-discipline: the dialog is a UI boundary, the match is domain data.

`Orientation` stays the one policy type, per type-system-discipline and laziness-protocol. A second three-value enum would be a hand-synced list. The preview simply never offers Auto. Auto remains the add-time stamp inside `PrintItem.added`, per model-the-domain.

Matching uses `assert_never` on `ApplyScope` so a new scope fails closed.

No phase gate. Dry Run does not read orientation yet, so a change during a batch only updates the row the list already shows.

## Synthesis decision

Two shapes, screened against `architect/references/design-red-flags.md`. No arena workers. This owner is not allowed to fan out and wait.

**Base: one `SetOrientation` command with `ApplyScope` matched in `reduce`.**

Why: same-kind is a fact on `PrintItem.kind`. One writer should own it. The window stays a thin boundary. Interface depth is the match policy behind three fields.

**Rejected: the window computes target ids and the command is `SetOrientation(item_ids, orientation)`.**

The reduce surface is smaller, but every caller re-implements DocKind equality. That is information leakage and a second way to decide "同类型". Modal confirm already freezes the list, so snapshotting ids does not buy a race the Tk thread can hit.

**Rejected: three command types, or a session field that the next `AddPaths` inherits.**

Three types enlarge the surface without hiding a new rule. A sticky field breaks `PrintItem.added` and issue #3.

## Tradeoffs accepted

- We accept that Auto and a forced policy with the same facing share `横向` or `纵向`, in exchange for leaving the issue #3 label contract alone.
- We accept a text fallback instead of a PDF or DOCX bitmap, in exchange for not adding a raster library. Images use Pillow. The product plan allows a preview that cannot draw the page.
- We accept that the preview cannot set a row back to Auto, in exchange for a picker that matches the issue text (Landscape, Portrait, PrinterDefault). The command type still allows `Orientation.AUTO` if a later caller sends it.
- We accept `ALL` applying to whatever rows exist at reduce time, in exchange for not copying ids into the command.

## Alternatives considered

The id-list command and the three-command split are above. A preview that writes `PrintItem` fields itself was rejected because it splits ownership of `BatchState.items`.

## Open questions and risks

- Should the picker include 自动 so an override can be cleared? Default here is no.
- Should forced Landscape on an already-wide file show a different mark than Auto? Default here is no, because issue #3 locked the words.
- Should PDF and DOCX render a first page in this issue? Default here is the text fallback.

## Next implementation step

Add `ApplyScope` and `SetOrientation`, handle them in `reduce`, then open `PreviewWindow` from a 预览 button that requires one checked row.

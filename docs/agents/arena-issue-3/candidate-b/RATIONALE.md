# Candidate B rationale

## Problem

Issue 3 adds PDF, DOCX, and image files as Print Items whose Orientation stays Auto, while the list shows the inferred first-page shape. A failed read logs a warning and shows portrait. A file added later stays Auto after an earlier row was overridden. `BatchSession.apply`, `snapshot`, and `subscribe` already own the list. Path intake already runs inside `AddPaths`. Settings and `BatchPrefs` stay preferences. List membership stays on the session. Issue 5 will later write an Orientation override onto existing ids. This sketch gives that write no stored default for the next add to read. The product plan also names the policy word `自动` on each row. The grounding note says the issue acceptance wins for Auto rows, so those rows show the inferred shape.

## Usage (caller's view)

The full sites are in `USAGE.md`. They agree with the signatures in `sketch.py`.

The window imports `AddPaths`, `BatchSession`, `BatchSnapshot`, and `ListRow`. Add stays `session.apply(AddPaths(paths))`. The panel walks `snapshot.rows` and draws `f"{row.name}  {row.geometry_label}  [{status}]"`. A wide page is `deck.pdf  横向  [等待]`. A tall page, a square page, or a failed read is `scan.png  纵向  [等待]`.

Reduce calls `intake_paths(command.paths)` and then `state.rows.append_births(births)`. The signature is paths in, births out. The same call is how a later add stays Auto.

## Shape

The core structure is an ordered list of pairs, `StoredRow(item, reading)`, owned by `BatchRows`. `PrintItem` stays the policy and lifecycle record. `GeometryReading` is the first-page fact. They share a list element, so remove, clear, and status updates move the pair together. The dominant walk is list order. The tick replaces one pair in place. `items()` returns a tuple copy for counts and submit, per foundational-thinking.

Three types keep the two meanings apart, per model-the-domain and type-system-discipline. `Orientation` is the stored policy, and Auto lives on that enum. `PageShape` is `PAGE_LANDSCAPE` or `PAGE_PORTRAIT`, with values `page_landscape` and `page_portrait`. `Orientation[shape.name]` and `Orientation(shape.value)` both fail. `ExplicitPolicy` is the future override payload, with Landscape, Portrait, and PrinterDefault. `as_orientation` accepts only `ExplicitPolicy`. That is the only conversion into `Orientation`, per encode-lessons-in-structure.

`Birth` carries the minted Print Item and the reading. `_mint` is the only constructor for a new Print Item, and it writes `Orientation.AUTO`. `Birth.__post_init__` requires Auto, Waiting, and an empty failure reason. `append_births` builds the pair list locally, then extends. `read_first_page` returns a reading for every path. `intake_paths` reads the paths it was given. A second add starts from Auto inside `_mint`, per make-operations-idempotent for the portrait outcome and per redesign-from-first-principles for birth.

File parsing stays inside `read_first_page`, per boundary-discipline. PDF page 0 uses pypdf mediabox width and height. DOCX uses the first python-docx section. Images use Pillow size, and the image is closed before return. `shape_from_size` is the only width rule. One private fallback logs one warning and returns portrait with `fell_back=True`. Unknown kinds, missing files, and reader errors share that fallback. `list_rows` copies `横向` or `纵向` onto `ListRow.geometry_label`. The widget prints that string.

`BatchSnapshot.rows` replaces `BatchSnapshot.items` in the same change. `expand_paths` is deleted in the same change, per migrate-callers-then-delete-legacy-apis. Package `__init__` exports `ListRow`. The reader and `BatchRows` stay in their modules.

`override_policy` is the issue 5 method. The body stays `NotImplementedError` here. `apply` gains no command for it. The method rewrites `PrintItem.orientation` on matching ids and stores nothing on `BatchRows`. `list_rows` reads `reading.shape`. Issue 5 changes that one method when an override should change the visible word. Until then every row shows the page shape, which is the issue 3 rule for Auto.

Interface depth sits on the session the UI already has. Callers still `apply`, `snapshot`, and `subscribe`. The new public field is `snapshot.rows`, a name, a status, and a two-word label. Behind that, the callee owns format dispatch, the inequality, the log, the Auto stamp, and the pair. The UI chain is the window, the snapshot, and the panel. Submit still receives a `PrintItem` and still ignores Orientation in Dry Run.

Per laziness-protocol, `PrintItem`, `AddPaths`, Settings, and `BatchPrefs` keep their current fields. Per experience-first, the row shows `横向` or `纵向`, which the user can check against the page. Per minimize-reader-load, the panel only formats `geometry_label`. Per exhaust-the-design-space, the sibling field and the side map stay rejected rather than blended into this shape.

## Synthesis decision

TBD. Arena fills this section after it compares candidates.

## Tradeoffs accepted

- We accept a `BatchRows` type and a snapshot field rename in exchange for one list of pairs and a widget row of id, name, status, and `geometry_label`.
- We accept that issue 5 edits `list_rows` before an override changes the visible word. Until that edit, the word is the page shape.
- We accept `纵向` for squares, unknown kinds, and unreadable files. `fell_back` stays on the reading. The warning is the operator-visible signal.
- We accept that the PDF Rotate entry is ignored until the product rule names it.
- We accept geometry reads on the `AddPaths` path. Folder expansion already reads the filesystem there.
- We accept pypdf, python-docx, and Pillow as runtime dependencies.
- We accept that a second add of the same path still appends another row. That matches today's `AddPaths`.
- We accept a direct import of `paperflick.core.batch.geometry` from tests. The widget is shown the package export list and the snapshot type.

## Alternatives considered

A `PrintItem` field such as `inferred: PageShape` looks smaller and hides the file readers if intake fills it. It loses on interface depth because every `PrintItem` consumer, including the tick and submit, then sees policy and shape as siblings. An agent can print `orientation.value`, or copy the previous item's Orientation into the next constructor. The confusion the issue has to prevent stays representable.

A dict from `ItemId` to `GeometryReading` beside `list[PrintItem]` hides the reading from `PrintItem`. It loses because remove, clear, and status replace become two writes. An agent who edits one list comprehension updates one of them. `StoredRow` makes that split unrepresentable. The public session functions stay just as small either way, so the pair list is the deeper module.

Reading inside `ItemListPanel.bind_snapshot` would keep `PrintItem` untouched. It loses because the widget would take the three libraries, log again on every rebind, and hold knowledge that belongs to path intake. A second read on each rebind could disagree with the stored birth.

## Open questions and risks

- Should the PDF Rotate entry change the shape, or does mediabox width versus height stand alone? This sketch uses the box alone.
- For an Auto row, is the visible text `横向` or `纵向` alone? This sketch follows the issue acceptance and prints the inferred mark.
- Is a warning log enough when a measured portrait page and a failed read look the same in the list? `fell_back` is on the reading if a later issue wants it in the row.
- If `sniff_kind` gains a kind string that `_SIZE_READERS` lacks, that kind falls back to portrait. A test that locks `pdf`, `docx`, and `image` to the registry would catch the drift.

## Next implementation step

Add pypdf, python-docx, and Pillow with mamba, then implement `shape_from_size` and `read_first_page` against fixture files before changing `BatchSession`.

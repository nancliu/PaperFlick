# Candidate A rationale: fact on the row, policy on the row, one resolver

## Problem

Issue #3 needs a newly added PDF, DOCX, or image to sit in the list as Orientation Auto while the row shows the inferred Landscape or Portrait. A failed read falls back to Portrait and writes a log line. A new row never inherits an earlier bulk override. The shape is non-obvious because the word "Orientation" already names a four-state policy (`types.Orientation`), and the acceptance text asks the list to show a two-state result. If both live in one field or one enum, the next agent will write `item.orientation = Orientation.LANDSCAPE` to "record the inference" and silently turn Auto into a forced override, which is exactly the sticky behaviour #5 must avoid. Constraints from grounding. `BatchSession` stays apply / snapshot / subscribe. Intake stays at `AddPaths` through `path_intake`. Settings never hold list state. The existing `kind == "pdf"` test and the direct `PrintItem(...)` construction in `test_batch_dry_run.py` are callers to migrate.

## Usage (caller's view)

See `USAGE.md`. Three call sites. Intake calls `PrintItem.added(path, probe(path))`. The list calls `orientation_label(item)`, which calls `resolve_facing(item.orientation, item.shape)`. A later real submit port and #5 `SetOrientation` call the same resolver and never read `shape` directly.

## Shape

Data first. `PrintItem` gains `shape: PageShape`, where `PageShape = Measured(width, height) | Unread(reason)`. That is the raw fact, captured once at AddPaths. `orientation: Orientation` stays the policy. A new two-member enum `Facing` is the only type a resolved direction can have. `resolve_facing(policy, shape) -> Facing | None` is the single pure rule, and nothing stores its output. Per type-system-discipline, `Facing` and `Orientation` are different types, so assigning an inferred direction into the policy field is a type error rather than a code-review catch. Per model-the-domain, the Portrait fallback for `Unread` and the "square is Portrait" tie-break live in one match, not in the UI and the submit port separately.

Format knowledge moves into one registry, `formats._FORMATS`, where each row binds a `DocKind`, its suffix set, and its first-page size reader. Today `path_intake` keeps three suffix sets and `sniff_kind` branches over them. A second dispatch for readers would be a hand-synced list (design-red-flags). The registry makes "add a format" one row. `probe(path) -> Probe(kind, shape)` is the module's whole public surface. Per boundary-discipline it is the boundary for untrusted files. It catches every reader exception, rejects non-positive sizes, maps a missing file or unknown suffix to `Unread`, logs once, and never raises. Everything downstream trusts `PageShape`. `sniff_kind` is deleted, not kept beside `probe` (migrate-callers-then-delete).

Readers apply display transforms before returning a size. PDF swaps width and height for `/Rotate` 90 or 270. Images swap for EXIF orientation 5 to 8. Without these, a scanned portrait page saved rotated, or any phone photo, infers the wrong direction, and the user sees it on the list immediately.

No-inherit is structural. `PrintItem.added` is the only constructor intake uses, and it has no orientation parameter. `expand_paths` takes no orientation. `BatchState` gains no orientation field. #5 can change policy only through a per-id command that `replace`s named rows, so a new AddPaths cannot see any prior override.

Interface depth. The public additions are `Facing`, `PageShape` (two small records), `resolve_facing`, `PrintItem.added`, `DocKind`, and `probe`. Behind them sit three third-party libraries, rotation and EXIF quirks, error mapping, logging, and the fallback rule. Callers learn one function to get a direction. `_FORMATS`, `_Format`, and the readers are private.

Deliberately not done. No background probing, no cache, no new event type (the existing `ItemsChanged` after AddPaths already rebinds the list), no `SetOrientation` command, no change to `BatchSession`.

## Synthesis decision

TBD.

## Tradeoffs accepted

- We accept synchronous file reads inside `AddPaths` on the Tk thread in exchange for no async state, no "probing..." row state, and no new event. A folder of hundreds of large PDFs will stall the UI for the probe time (guess, unmeasured). `path_intake` already does filesystem walks on this path.
- We accept storing raw `width` and `height` in exchange for a single derivation point. Storing a precomputed `Facing` would be smaller but would split "what the file is" from "how Auto reads it" and invite a second inference rule elsewhere.
- We accept a required `shape` field on `PrintItem`, which breaks the one test that constructs `PrintItem(...)` directly, in exchange for no `shape: PageShape | None` that is always set in practice. That test moves to `PrintItem.added` or passes an explicit `Measured`.
- We accept `kind` becoming `DocKind(StrEnum)` in exchange for one registry owning kind and reader together. String comparisons keep working.
- We accept that a probe snapshot can go stale if the file changes after add, in exchange for a row whose label does not flicker. Re-add refreshes it.

## Alternatives considered

- Store only `inferred: Facing` on the row and drop the measured size. Smaller row, but the Portrait fallback rule then lives at intake while forced-policy resolution lives at submit, two places that both decide direction. Lost on single source of truth.
- Keep `PrintItem` unchanged and compute geometry lazily in the UI via a cached `infer(path)` helper. Smallest diff, but the UI, the preview (#5), and the real submit port would each call it, file I/O would move into widget rebinds, and the cache becomes hidden shared state. Lost on boundary discipline and split ownership.
- Fold inference into policy by adding `AUTO_LANDSCAPE` / `AUTO_PORTRAIT` members to `Orientation`. Exhaustive and compact, but it doubles every match on policy, makes "is this Auto?" a two-member check that agents will get wrong, and makes `PrintItem.added` choose a policy based on file content. Lost on making the policy/fact confusion representable, which is the exact bug to prevent.

## Open questions and risks

- Is `自动·横向` the right Auto label, or should Auto rows show only `横向` / `纵向` as the acceptance text literally says? The plan's label table also lists a bare `自动`. The candidate keeps the policy visible so a forced Landscape and an inferred Landscape look different.
- Should `Facing` enter `GLOSSARY.md` as a term next to Orientation, so later issues use the same word for "resolved direction"?
- Should unreadable rows carry a visible hint (tooltip or suffix) beyond the log, given the user cannot see the log in the app today? There is no logging configuration in `src/` yet. Who wires `logging.basicConfig` or a file handler?
- `.doc` files will always probe as `Unread` because python-docx cannot open them. Is a Portrait label for every `.doc` acceptable until Word COM lands?
- Does pypdf on encrypted PDFs raise or return a page? The candidate treats any exception as `Unread`. An implementer should confirm with a real encrypted sample.

## Next implementation step

Write `formats.py` with `probe` and its three readers, plus a pytest that probes a generated landscape PDF, a rotated portrait PDF, a landscape PNG, an EXIF-rotated JPEG, a DOCX with swapped section size, and a corrupt file, asserting `resolve_facing(Orientation.AUTO, probe(p).shape)` for each.

# Issue #3 synthesis

## Rubric

1. Policy (`Orientation`) and inferred geometry cannot be collapsed into one field/enum
2. New Print Items always Auto; no sticky bulk inherit surface
3. Fits `BatchSession` apply/snapshot/subscribe; intake at `AddPaths`
4. Deep public surface; UI stays thin
5. Portrait fallback + one log on read failure
6. Small blast radius vs existing `items` / Dry Run / #9 worktree

## Cross-judge

Skipped. Parent family unknown / same-pool risk; parent scored alone against the rubric.

## Base

**Candidate A** ([b74e8352](b74e8352-95db-4829-bc1e-2749f51e6a35)): `shape` on `PrintItem`, `Facing`, `resolve_facing`, `formats.probe` registry, `PrintItem.added`.

Why: same policy/fact split as B, without replacing `BatchState.items` / `BatchSnapshot.items` with `BatchRows`. Keeps #9’s worktree surface stable. Interface depth concentrates on `probe` + `resolve_facing`.

## Grafts from candidate B ([cce8283d](cce8283d-cc72-4e91-b184-971acf28d655))

1. **Auto row label is bare `横向` / `纵向`.** Acceptance asks for inferred Landscape/Portrait. Forced policies (later #5) still use policy words via `orientation_label`.
2. Keep B’s reminder that `list_rows` must not read policy for Auto display; A’s `orientation_label` already branches on policy.

## Rejected from B

- `BatchRows` / `StoredRow` / `snapshot.rows` rename (too much churn for #3; pairs with #9 risk).
- `ExplicitPolicy` / `override_policy` bodies beyond a documented hook (`SetOrientation` later).
- Ignoring PDF `/Rotate` and image EXIF (A’s readers are product-correct; graft A).

## Operator defaults (Never Block)

- Auto list mark: bare inferred facing (acceptance over plan’s bare `自动`).
- `.doc`: Unread → Portrait + log (python-docx cannot open).
- Logging: stdlib `logging.getLogger("paperflick.formats")`; no app-wide handler required for #3 (pytest / console capture enough for agents).
- Square pages: Portrait (`宽 > 高` only).

## Next

Implement against this contract in `printer-advance-wt-3`. Open PR when verify-paperflick passes.

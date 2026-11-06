# Grounding: issue #3 Orientation on add

Source: parent how + code on `feat/issue-3-orientation` @ origin/main tip.

## Overview

AddPaths already creates Print Items with `orientation=Orientation.AUTO` via `path_intake.expand_paths`. The list UI (`item_list.py`) shows only `name [status]`. No inference of page geometry. No bulk Orientation override state yet (#5 owns apply-from-preview).

## Key Concepts

- **Orientation** policy enum: Auto / Landscape / Portrait / PrinterDefault (`types.Orientation`).
- **Inferred geometry** (product plan §4): width > height → Landscape, else Portrait. PDF pypdf page 0 mediabox; DOCX python-docx section; image Pillow size; read failure → Portrait + log.
- **List display** (issue acceptance): show inferred Landscape/Portrait (not only the Auto policy word). Product plan also names policy labels; for Auto rows, acceptance wins: show the inferred mark.
- **No inherit bulk**: new items always Auto at add. There is no session-level last-bulk Orientation today; keep it that way (no global sticky override).

## How It Works

1. UI Add → `AddPaths` → `reduce._add_paths` → `expand_paths` → `PrintItem(..., orientation=AUTO)`.
2. `BatchSession` emits `ItemsChanged`; `ItemListPanel.bind_snapshot` rebuilds rows.
3. Submit path ignores Orientation in Dry Run.

## Where Things Live

| Concern | Path |
| --- | --- |
| PrintItem + Orientation | `src/paperflick/core/batch/types.py` |
| Add/folder expand | `src/paperflick/core/batch/path_intake.py` |
| List row text | `src/paperflick/ui/item_list.py` |
| Deps | `pyproject.toml` / `environment.yml` (no pypdf/Pillow/python-docx yet) |

## Gotchas

- Deps missing for inference libraries; must add for real formats. No logger module in `src/paperflick` yet.
- #5 will mutate Orientation from preview; #3 must leave a clean place for overrides without sticky defaults on new adds.
- Accept criteria want inferred L/P on the list while policy stays Auto. Writing inference into `orientation` collapses Auto and breaks “new rows stay Auto”. Keep policy vs geometry separate.
- Equal width and height → Portrait (`宽 > 高` only).
- Dedup is per `AddPaths` call; re-adding the same path creates another Auto row.
- `.doc` sniffs as `docx`. `unknown` still gets Auto; infer must decide those deliberately.
- Settings must stay preferences. Never persist a last bulk override there.

## How explainer (37ec18be)

Confirmed: Auto stamp already in `path_intake._append_file`; list shows name+status only; no bulk override state. Hook display at `ItemListPanel.bind_snapshot` (or a pure label helper it calls).

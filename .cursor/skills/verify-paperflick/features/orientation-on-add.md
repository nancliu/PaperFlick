# Orientation on add

Prove issue #3: new Print Items stay Auto; the list shows inferred 横向/纵向; unread files fall back to 纵向 with one warning.

## Setup

Disposable `PAPERFLICK_APPDATA`. Launch via skill Launch steps (or construct `MainWindow` headless).

## Drive

1. Create a landscape PNG (`width > height`) and a corrupt `.pdf` under a temp folder.
2. `session.apply(AddPaths([landscape, broken]))` (or use the Add files dialog).
3. Read `snapshot.items` and `orientation_label(item)`.

## Expect

- Every new item has `orientation is Orientation.AUTO`.
- Landscape file label is `横向`.
- Corrupt PDF label is `纵向`; logger `paperflick.formats` emits one WARNING containing the path.
- A second add after manually replacing an earlier item's orientation still births Auto (no sticky override).

## Evidence

Copy of labels + optional `settings.json` under `artifacts/<run-id>/`. Note headless vs live window.

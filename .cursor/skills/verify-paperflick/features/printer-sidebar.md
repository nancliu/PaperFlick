# Printer sidebar and selection persistence

The main window sidebar lists installed printers. Choosing one writes `selected_printer` into settings and restores that choice after restart when the name is still installed. When nothing is stored, the sidebar selects the Windows default printer if it is installed and persists that name on boot.

The left pane is a horizontal split. It opens near 280px and can be dragged from 200px to half the window width, in the same units as the 780×640 window geometry (high-DPI scaling follows the rest of the window). That sash position lasts for the process only and is not written to settings. Hovering a row shows the full real printer name. The system default's visible label is that real name plus 「（默认）」; the radio value and `selected_printer` stay the real name.

## Sub-features

- `printer-list` shows branded names from `list_installed_printers()` (empty list is safe).
- `printer-select-persist` saves the chosen name via the same `_persist` path as other settings.
- `printer-system-default` selects `GetDefaultPrinter` when `selected_printer` is unset and that name is installed.
- `printer-default-suffix` shows the system default as `real name（默认）`. Hover text, the radio value, and `selected_printer` omit that suffix.
- `printer-hover` shows the full real printer name while the pointer is on a row.
- `printer-sash` opens the left pane near 280px, clamps dragging to 200px .. half the window width, and remembers the sash for this process only.
- `printer-stale` keeps a missing saved name in settings and does not force a sidebar match.

## How to get to it (user POV)

- Launch PaperFlick. The left sidebar lists printers and is about 280px wide.
- Drag the split. It stops at 200px and at half the window width. Quit and launch again: the width is back near 280px.
- Hover a long name. The tooltip is the full real name.
- The system default row reads `name（默认）`. Choosing it stores `name`.

## Driving it with MainWindow

Preconditions:

- `paperflick` env installed editable.
- `PAPERFLICK_APPDATA` points at an empty disposable directory.
- Optionally patch `list_installed_printers` to return known names when no real printers are needed.
- From the worktree, with `src` ahead of any installed checkout: `$env:PYTHONPATH = "src"; mamba run -n paperflick python .cursor\skills\verify-paperflick\_run_printer_sidebar.py`

- **List.** Open `MainWindow`. Sidebar shows the patched or live names, or the empty placeholder.
- **Select.** Call the sidebar selection path (or click a radio). `load().selected_printer` equals the chosen real name, with no 「（默认）」 suffix.
- **Suffix and hover.** The system-default radio text ends with 「（默认）」. `hover_text` and the popup equal the real name.
- **Sash.** After `update()`, the sash is about 280px and no session width is stored yet. Press, drag, and release the sash: the left pane stays between 200px and half the window width, and the released width is remembered in the process. `settings.json` gains no sash field.
- **Stale.** Save a name that is not in the list. Reopen. Sidebar has no forced match. `load().selected_printer` still holds the stale name after `_persist`.
- **Proof.** `artifacts/issue-39-printer-sidebar/log.txt` and `settings.json` from `_run_printer_sidebar.py`. Note headless versus a live window.

## Gotchas

- Missing printer must not block a future Dry Run Start (owned by issue #2).
- Live enum needs `pywin32` in the `paperflick` env (`environment.yml`). Without it, the sidebar shows the empty placeholder.
- Unit tests mock `win32print.EnumPrinters`; they do not require a physical printer.
- The sash is process memory. A new process starts near 280px again. Do not add it to `Settings`.

# Printer sidebar and selection persistence

The main window sidebar lists installed printers. Choosing one writes `selected_printer` into settings and restores that choice after restart when the name is still installed.

## Sub-features

- `printer-list` shows branded names from `list_installed_printers()` (empty list is safe).
- `printer-select-persist` saves the chosen name via the same `_persist` path as other settings.
- `printer-stale` keeps a missing saved name in settings and does not force a sidebar match.

## How to get to it (user POV)

- Launch PaperFlick. The left sidebar lists printers.
- Click a printer. Close and reopen. That printer stays selected when still installed.

## Driving it with MainWindow

Preconditions:

- `paperflick` env installed editable.
- `PAPERFLICK_APPDATA` points at an empty disposable directory.
- Optionally patch `list_installed_printers` to return known names when no real printers are needed.

- **List.** Open `MainWindow`. Sidebar shows the patched or live names, or the empty placeholder.
- **Select.** Call the sidebar selection path (or click a radio). `load().selected_printer` equals the chosen name.
- **Stale.** Save a name that is not in the list. Reopen. Sidebar has no forced match. `load().selected_printer` still holds the stale name after `_persist`.
- **Proof.** Copy `settings.json` into `artifacts/<run-id>/printer-sidebar/`.

## Gotchas

- Missing printer must not block a future Dry Run Start (owned by issue #2).
- Live enum needs `pywin32` in the `paperflick` env (`environment.yml`). Without it, the sidebar shows the empty placeholder.
- Unit tests mock `win32print.EnumPrinters`; they do not require a physical printer.

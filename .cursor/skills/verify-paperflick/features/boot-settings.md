# Boot window and settings

PaperFlick opens a main window and loads or creates settings under the AppData (or `PAPERFLICK_APPDATA`) directory with defaults interval 2s, wait-for-empty-queue off, Dry Run off.

## Sub-features

- `boot-launch` opens the CustomTkinter main window via `python -m paperflick` or `MainWindow()`.
- `boot-defaults` shows default control values matching `Settings()`.
- `boot-doctor` confirms imports and default `Settings` before driving.

## How to get to it (user POV)

- From a shell in the repo: activate `paperflick`, run `python -m paperflick`.
- Agent headless path: construct `MainWindow` in-process.

## Driving it with MainWindow / module launch

Preconditions:

- `paperflick` env installed editable.
- `PAPERFLICK_APPDATA` points at an empty disposable directory.

- **Doctor.** Import `Settings` and `load`. Defaults equal `Settings()`.
- **Launch.** Start `MainWindow` or `python -m paperflick`. Window title is `PaperFlick`.
- **Defaults visible.** 「设置 ▾」 is collapsed. Open it: interval field shows `2.0` (or `2`); wait and 演练 unchecked. Close it again; that open/closed choice is not in `settings.json`.
- **Proof.** Copy `settings.json` after first close/persist (may be created on first save) into `artifacts/<run-id>/boot-settings/`. Optional window screenshot when display is available.

## Gotchas

- Without `PAPERFLICK_APPDATA`, the run writes the developer's real `%APPDATA%\PaperFlick\`. Always isolate for agent runs.
- Multi-line `python -c` under PowerShell fails; use pytest or a `.py` file.

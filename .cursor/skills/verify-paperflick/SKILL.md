---
name: verify-paperflick
description: Drive the PaperFlick Windows desktop app (CustomTkinter) to prove boot, settings, Dry Run batch, orientation-on-add, preview orientation apply, fail-and-reprint, and printer-sidebar behavior. Use when verifying PaperFlick changes or AppData settings persistence.
---

# Verify PaperFlick

Agent-facing recipe for proving PaperFlick on a real Windows desktop surface. Prefer this over disposable `_verify_*.py` scripts.

## Launch

```powershell
mamba activate paperflick
cd <repo-root>
pip install -e .
$env:PAPERFLICK_APPDATA = Join-Path $env:TEMP ("paperflick-verify-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $env:PAPERFLICK_APPDATA | Out-Null
python -m paperflick
```

Ready: a window titled `PaperFlick` appears with interval / wait-queue / Dry Run controls.

Teardown: close the window (WM_DELETE_WINDOW persists settings), then remove the temp `PAPERFLICK_APPDATA` directory if this run created it. Keep proof artifacts under `.cursor/skills/verify-paperflick/artifacts/<run-id>/`.

For headless proof in the same process (CI / agent without staring at the window), construct `MainWindow`, call `update_idletasks()`, exercise controls, then `destroy()`. That path is accepted when a live display is unavailable; note it in the evidence.

## Doctor

Read-only health check before driving (script file; do not use `python -c` under PowerShell):

```powershell
mamba run -n paperflick python .cursor\skills\verify-paperflick\_doctor.py
```

Require: import succeeds; `Settings()` defaults are `interval_seconds=2.0`, `wait_for_empty_queue=False`, `dry_run=False`. If `PAPERFLICK_APPDATA` is set, `load()` must read/write only under that directory.

Refuse to drive a PaperFlick window the agent did not start in this run (shared user AppData session risk).

## Drive

Harness: in-process CustomTkinter (`MainWindow`) plus filesystem reads of `settings.json`. Stable handles are widget variables and the settings file, not pixel coordinates.

Typical flow:

1. Set `PAPERFLICK_APPDATA` to a disposable directory.
2. `app = MainWindow(); app.update_idletasks()`.
3. Mutate controls (`_interval_var` + `_on_interval_typed`, `_dry_var` + `_persist`, etc.).
4. `load()` and assert disk state.
5. `app.destroy()`.

See `features/` for user journeys.

## Evidence

Proof standards:

- Exercise the real settings path (load/save), not internal test doubles of `save`.
- Capture action and resulting state: control change + `settings.json` contents (and a screenshot when a live window is used).
- Side effect: file under `PAPERFLICK_APPDATA` / `%APPDATA%\PaperFlick\settings.json`.
- Store artifacts in `.cursor/skills/verify-paperflick/artifacts/<run-id>/` (`settings.json` copy, optional `window.png`, short `log.txt`). Cleanup must not delete these artifacts.

## Cleanup

Kill or destroy only windows/processes this run started. Remove disposable `PAPERFLICK_APPDATA` dirs created for the run. Leave `artifacts/` intact.

## Helpers

```powershell
mamba run -n paperflick pytest -q tests/test_settings.py tests/test_gui_boot.py
```

Pytest covers defaults, coerce, round-trip, KeyRelease persist, and boot smoke. Runtime skill drives the same surface for manual/agent proof beyond unit tests.

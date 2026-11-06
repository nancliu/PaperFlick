# Interval and Dry Run controls

Changing the send interval or Dry Run updates `settings.json` so a restart (or `load()`) sees the new values. Interval persists on a valid typed value without requiring a separate focus dance relative to checkboxes.

## Sub-features

- `interval-type` persists a positive float after KeyRelease-equivalent commit.
- `dry-run-toggle` persists when the checkbox changes.
- `interval-invalid` falls back on FocusOut/Return without writing a non-positive value as the new source of truth incorrectly.

## How to get to it (user POV)

- In the main window, edit **发送间隔（秒）** or toggle **Dry Run**.

## Driving it with MainWindow

Preconditions:

- Baseline boot with disposable `PAPERFLICK_APPDATA`.
- `MainWindow` constructed.

- **Type interval.** Set interval var to `7.5` and invoke `_on_interval_typed`. `load().interval_seconds == 7.5`.
- **Toggle Dry Run.** Set dry var true and `_persist`. `load().dry_run is True`.
- **Invalid commit.** Set interval to `bad`, `_on_interval_commit`. Prior valid interval remains on disk.
- **Proof.** Save `settings.json` and a short log of assertions under `artifacts/<run-id>/interval-and-dry-run/`.

## Gotchas

- Incomplete typing (e.g. empty string) may skip KeyRelease persist until FocusOut normalizes; that is expected.
- Do not treat pytest alone as a substitute when the bug is display-server specific; still prefer these steps on a live window when investigating UI-only failures.

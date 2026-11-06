# Dry Run Batch list

Add Print Items, enable Dry Run, Start a Batch. Statuses advance Waiting → Success at the interval with pause/stop. No real Print Job.

## Sub-features

- `add-remove` populates and edits the Print Item list from files or folders.
- `dry-run-start` advances rows serially when Dry Run is on.
- `start-refuses-without-dry-run` shows a clear message when Dry Run is off.
- `pause-stop` freezes or ends advancement without submitting Print Jobs.

## How to get to it (user POV)

- Add files/folders, tick **Dry Run**, press **开始**. Use **暂停** / **继续** / **停止** as needed.

## Driving it with MainWindow

Preconditions:

- Disposable `PAPERFLICK_APPDATA`.
- `MainWindow` constructed; prefer headless `update_idletasks` when no live display.

- **Add paths.** Call `_session.apply(AddPaths([...]))` or drive the Add buttons with real files under a temp dir.
- **Enable Dry Run.** Set `_dry_var` true and `_persist`.
- **Start.** `_on_start()`. Snapshot success count rises as Tk `after` ticks (or use a session with `ManualClock` in unit tests).
- **Refuse.** With Dry Run off, `_on_start()` leaves phase idle and surfaces the Dry Run required message.
- **Proof.** Unit: `pytest tests/test_batch_dry_run.py`. GUI smoke still covered by existing boot test.

## Gotchas

- Wave 1 has no real print sink; Start without Dry Run must refuse.
- Interval ticks use Tk `after` in the live window; core tests inject `ManualClock`.

# Dry Run Batch list

Add Print Items, enable Dry Run, Start a Batch. Statuses advance Waiting → Success at the interval with pause/stop. No real Print Job.

## Sub-features

- `add-remove` populates and edits the Print Item list from files or folders.
- `dry-run-start` advances rows serially when Dry Run is on.
- `start-with-dry-run-off` submits PDF Print Items. See [PDF real print](./pdf-real-print.md).
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
- **Dry Run off.** PDF submit is specified in [PDF real print](./pdf-real-print.md). This feature only proves the Dry Run path sends no command.
- **Proof.** Unit: `pytest tests/test_batch_dry_run.py`. GUI smoke still covered by existing boot test.

## Gotchas

- Dry Run off no longer refuses Start. It submits PDF Print Items.
- Interval ticks use Tk `after` in the live window; core tests inject `ManualClock`.

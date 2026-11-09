# Failed rows and reprint

A failed Print Item stays in the list with a reason. The Batch continues. Dry Run can fail one submit so this path can be proved without a printer.

## What the user does

- Press **重新打印失败项** while the Batch is idle and Dry Run is on. Every failed row returns to waiting and the Batch starts. Reprint does not depend on a selection.
- Press **清除已成功** to drop successful rows. Failed, waiting, and printing rows stay.
- **移除全部失败** asks, then drops every failed row. That action is proved with list preview, not with this reprint path.

## How to drive it

Preconditions.

- Disposable `PAPERFLICK_APPDATA`.
- Pass `submit_script=SubmitScript((SubmitFailed("卡纸"),))` to `MainWindow` when the run must inject one failure. The product launch omits it. An empty script accepts every readable file.
- `submit_script` forces Dry Run for every Start, even when the Dry Run checkbox is off. The product window omits the script, so Dry Run off uses SumatraPDF.

Steps.

1. Add two real files.
2. Turn Dry Run on, set a short interval, and persist.
3. Call `_on_start()`. The first submit fails with `卡纸`. The next submit succeeds. The failed row label contains that reason.
4. Call `_on_clear_succeeded()`. The success row is gone. The failed row stays.
5. Call `_on_reprint_failed()`. The same script continues at the next step, so the reset row succeeds.
   A second call while nothing is failed leaves the status line unchanged.

Deleting a file after it was added fails that row with `文件不存在`. That path needs no script.

## Gotchas

- Reprint while the Batch is running or paused does nothing and leaves the failure reason in place.
- Reprint with Dry Run off submits through the same port as Start. A missing SumatraPDF fails that row again and the Batch still finishes.
- After Stop, rows that were still waiting run again together with the rows reprint just reset.
- Proof is `pytest tests/test_batch_fail_reprint.py tests/test_gui.py`.

# Batch end report and spooler gate

After a Batch finishes, the status line shows this run's success and failure counts. The bottom census label still counts every row on the list. With Dry Run off and **等待打印队列清空后再发下一份** on, the next file waits until that printer's job count is 0. The send interval still has to elapse. Dry Run does not read the queue. Stop does not show the finish line.

## What the user does

- Add a PDF, a DOCX, and an image. Press **开始**.
- When the list has no waiting rows, the gray status line reads `本批完成：成功 N、失败 M`.
- Rows stay. The census line still shows `成功` and `失败`.
- Turn the wait checkbox on and Dry Run off to hold the next file while the selected printer's queue is not empty.

## How to drive it

Preconditions.

- Disposable `PAPERFLICK_APPDATA`.
- `MainWindow(submit_script=SubmitScript(()), spooler=probe)` so the run does not spool real jobs. The gate reads the checkbox, not the port. `submit_script` keeps the submit on Dry Run machinery while the checkbox can still be off.
- The probe returns `SpoolerCount`. It is not called while Dry Run is on.

Steps.

1. Construct the window and `update_idletasks()`.
2. Turn Dry Run on, turn the wait checkbox on, set a short interval, and persist both.
3. Add a PDF, a DOCX, a PNG, and a missing JPEG. Press start through `_on_start()`.
4. The status line is `本批完成：成功 3、失败 1`. The census line contains `成功 3` and `失败 1`. The missing row says `文件不存在`. The probe was not called.
5. Clear the list. Turn Dry Run off, leave the wait checkbox on, and persist.
6. Add the PDF and the PNG. Press start. The second row stays waiting while the probe reports one job. After the probe reports zero, the batch finishes with `本批完成：成功 2、失败 0`.

Proof.

- From the worktree, with `src` ahead of any installed checkout: `$env:PYTHONPATH = "src"; mamba run -n paperflick python .cursor\skills\verify-paperflick\_run_batch_report.py`
- `mamba run -n paperflick pytest -q tests/test_batch_report.py tests/test_spooler_count.py tests/test_gui.py`

## Gotchas

- The finish line counts rows this Start handed off. It is not the census. A second Start with older SUCCESS rows still on the list reports only the new rows.
- Stop leaves the status line empty of `本批完成`. Leftover rows stay waiting.
- The first file does not wait for an empty queue. Later files do, and only when Dry Run is off.
- A queue that never returns to 0 holds until **停止**. There is no separate timeout field.
- `SubmitOk` is still handoff. The finish line can appear while the last job is still in the spooler.
- These files are accepted by suffix. This run does not start SumatraPDF, Word, or a Windows printer. Real print of each kind stays in the PDF, image, and DOCX features.

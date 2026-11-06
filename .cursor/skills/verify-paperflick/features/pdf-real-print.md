# PDF print with Dry Run off

A PDF Print Item is handed to SumatraPDF when Dry Run is off. The Batch still waits out the interval. The resolved direction becomes Sumatra's `portrait` or `landscape` print setting, and PrinterDefault omits that setting. A missing SumatraPDF fails that Print Item with `未找到 SumatraPDF` and the Batch continues. DOCX and images fail the item with `该格式暂不支持打印`. They are not printed here.

## What the user does

- Add PDFs. Leave **Dry Run** off. Press **开始**.
- A wide first page is sent as landscape. A tall first page is sent as portrait.
- The next item waits for **发送间隔（秒）**.

## How to drive it

Preconditions.

- Disposable `PAPERFLICK_APPDATA`.
- Do not point this run at an installed SumatraPDF. Pass `sumatra_executable` to a stand-in file and `sumatra_run` to a function that records the argument vector and returns exit code 0.
- `PAPERFLICK_SUMATRA` set to a missing file also fails closed and does not fall through to a real install.

Steps.

1. Construct `MainWindow(sumatra_executable=exe, sumatra_run=run)` and `update_idletasks()`.
2. With Dry Run on, start one PDF. The runner is not called. The row succeeds.
3. Clear the list. Turn Dry Run off, set the interval, and persist. `load().dry_run` is false.
4. Add a wide PDF, a non-PDF, and a tall PDF. Press start through `_on_start()`.
5. The runner sees `-print-settings landscape`, then `-print-settings portrait`, both with `-silent`. The gap is at least the interval. The non-PDF row shows `该格式暂不支持打印`. The Batch returns to idle.

Proof.

- From the worktree, with `src` ahead of any installed checkout: `$env:PYTHONPATH = "src"; mamba run -n paperflick python .cursor\skills\verify-paperflick\_run_pdf_print.py`
- `mamba run -n paperflick pytest -q tests/test_pdf_print.py`

## Gotchas

- `submit_script` still forces Dry Run for every Start. Omit it when the run must hit Sumatra.
- No selected printer uses `-print-to-default`.
- `等待打印队列清空后再发下一份` is still stored and does not gate the next PDF.
- The stand-in executable is never spawned when `sumatra_run` is passed. The real `run_sumatra_process` path is covered by `test_run_sumatra_process_returns_the_exit_code`.

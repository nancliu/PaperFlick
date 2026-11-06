# DOCX print with Dry Run off

A DOCX Print Item uses Word when Dry Run is off. If Word fails, the same item uses OnlyOffice. The log names the engine that printed. If both fail, that Print Item is failed and the Batch continues. Dry Run does not call either engine.

## What the user does

- Add DOCX files. Leave **Dry Run** off. Press **开始**.
- A wide first page is landscape. A tall first page is portrait.
- The next item waits for **发送间隔（秒）**.

## How to drive it

Preconditions.

- Disposable `PAPERFLICK_APPDATA`.
- Do not start the installed Word or OnlyOffice. Pass `docx_submit` whose engines record the job and return success or a failed reason.
- `PAPERFLICK_ONLYOFFICE` set to a missing file fails closed and does not fall through to an installed converter.

Steps.

1. Construct `MainWindow(docx_submit=port)` and `update_idletasks()`.
2. With Dry Run on, start one DOCX. Neither engine is called. The row succeeds.
3. Clear the list. Turn Dry Run off, set the interval, and persist. `load().dry_run` is false.
4. Add a wide DOCX, a tall DOCX, and another DOCX. Press start through `_on_start()`.
5. Word prints the wide file and is not followed by OnlyOffice. Word fails the tall file and OnlyOffice prints it. Both fail the third file. The third row names Word and OnlyOffice. The gap is at least the interval. The Batch returns to idle.

Proof.

- From the worktree, with `src` ahead of any installed checkout: `$env:PYTHONPATH = "src"; mamba run -n paperflick python .cursor\skills\verify-paperflick\_run_docx_print.py`
- `mamba run -n paperflick pytest -q tests/test_docx_print.py`

## Gotchas

- `submit_script` still forces Dry Run for every Start. Omit it when the run must hit the DOCX port.
- OnlyOffice has no silent-print flag. The production fallback converts with `x2t` and spools that PDF through the Sumatra port. This run injects the engines, so it does not convert or spool.
- `等待打印队列清空后再发下一份` gates the next file when Dry Run is off. This run leaves it off. See [Batch end report and spooler gate](./batch-end-report.md).
- Images still fail with `该格式暂不支持打印`.

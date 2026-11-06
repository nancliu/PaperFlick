# Image print with Dry Run off

An image Print Item is handed to Pillow and Windows printing when Dry Run is off. The Batch still waits out the interval. The resolved direction selects portrait or landscape for that job, and PrinterDefault leaves the printer's current direction unchanged. A missing printer or a file Pillow cannot open fails that Print Item and the Batch continues. DOCX still fails the item with `该格式暂不支持打印`. This feature does not print DOCX.

## What the user does

- Add images. Leave **Dry Run** off. Press **开始**.
- A wide image is sent as landscape. A tall image is sent as portrait.
- The next item waits for **发送间隔（秒）**.
- A bad image shows a short reason on its row. The following image still prints.

## How to drive it

Preconditions.

- Disposable `PAPERFLICK_APPDATA`.
- Do not draw on a real printer. Pass `image_devices` so each page is recorded and no document is started.
- Pass `sumatra_executable` pointing at a missing file so a PDF in the list cannot reach an installed SumatraPDF.

Steps.

1. Construct `MainWindow(sumatra_executable=missing, image_devices=devices)` and `update_idletasks()`.
2. With Dry Run on, start one image. The device factory is not called. The row succeeds.
3. Clear the list. Turn Dry Run off, set the interval, and persist. `load().dry_run` is false.
4. Add a wide PNG, a corrupt PNG, a DOCX, and a tall PNG. Press start through `_on_start()`.
5. The device sees landscape, then portrait. The gap is at least the interval. The corrupt row shows `图片无法打开`. The DOCX row shows `该格式暂不支持打印`. The Batch returns to idle.

Proof.

- From the worktree, with `src` ahead of any installed checkout: `$env:PYTHONPATH = "src"; mamba run -n paperflick python .cursor\skills\verify-paperflick\_run_image_print.py`
- `mamba run -n paperflick pytest -q tests/test_image_print.py`

## Gotchas

- `submit_script` still forces Dry Run for every Start. Omit it when the run must hit the image device.
- No selected printer uses the Windows default printer. The injected device receives that name.
- `等待打印队列清空后再发下一份` gates the next file when Dry Run is off. This run leaves it off. See [Batch end report and spooler gate](./batch-end-report.md).
- The stand-in device never calls StartDoc. A missing printer name is covered by `test_unknown_printer_records_a_reason_without_raising`.

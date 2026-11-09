# List preview and remove

Prove issue #38 and #41. A row click opens that Print Item's preview. The inline 移除 button removes that row without asking. 移除全部失败 asks, then removes every failed row. Start still prints every Waiting item. Removals work while the Batch is running or paused. The preview window shows its summary, orientation choices, and actions before thumbnail decode; a failed decode keeps the text fallback and the window is lifted.

## Setup

Disposable `PAPERFLICK_APPDATA`. Construct `MainWindow` headless. Turn Dry Run on before Start. No installed printer is required.

## Drive

1. Confirm the add toolbar has 添加文件 / 添加文件夹, and has neither 移除所选, 预览, nor 只勾选失败项. 移除全部失败 / 重新打印失败项 / 清除已成功 exist but stay unmapped until a row has failed; then they sit below the list and above 开始. The list has no checkboxes.
2. Add two PNGs. Each row shows 移除 at the end.
3. Click the first row's name, not 移除. The preview exists with the file name, 横向 / 纵向 / 打印机, and 应用到此项 before any thumbnail call. After the window is mapped, the thumbnail runs. The window was mapped when decode started, and lift/focus ran again after it.
4. Click the second row. The first preview is gone. One preview is open. A thumbnail that returns nothing shows the text fallback.
5. Open again with a thumbnail that raises. The same text fallback shows, and the window was lifted.
6. Click 移除 on one row. That row is gone. No confirm dialog. Preview does not open.
7. Add another waiting file and 开始. Both waiting rows succeed.
8. Add a file, delete it from disk, add a keeper, and 开始. 移除全部失败 with the dialog declined leaves the failed row. Accepting removes only failed rows. Clicking it again with no failures does not ask.
9. With a long interval, 开始, then 移除 a waiting row while RUNNING. 暂停, then 移除 another waiting row. Both removals skip the confirm dialog and leave the phase unchanged.

## Expect

- Row body opens preview. 移除 does not.
- At most one preview window exists.
- Start does not depend on a checked row.
- Single-row remove never asks. 移除全部失败 asks once per click when a failed row exists.
- Preview chrome is visible before raster. Raster failure stays on the text fallback.

## Evidence

`artifacts/list-preview/log.txt` from `_run_list_preview.py`. Note headless versus a live window.

Proof: `mamba run -n paperflick pytest -q tests/test_list_preview_window.py tests/test_gui.py tests/test_batch_dry_run.py`

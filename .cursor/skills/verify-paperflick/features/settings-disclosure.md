# Settings disclosure and 演练 label

Prove issues #40 and #42. The title row has an inline 「设置 ▾」 disclosure. It starts collapsed on every launch. Open or closed lasts for this process only and is not a `settings.json` field. Folded inside are 发送间隔、等待队列清空、and 演练（不送打印机）. The printer sidebar stays on the left. `dry_run` behavior and the settings key stay as they are.

When Dry Run is on and the Batch is idle with no other status message, the status line reads `演练（不送打印机）`. While the Batch is running or paused, that line is prefixed with `演练 · `. The batch-end line `本批完成：成功 N、失败 M` stays unprefixed.

The failure actions (移除全部失败, 重新打印失败项, 清除已成功) are shown only when `failed_count > 0`. They sit below the list and above 开始 / 暂停 / 继续 / 停止.

## Setup

Disposable `PAPERFLICK_APPDATA`. Construct `MainWindow` headless. A `submit_script` may inject one Dry Run failure. No installed printer is required.

## Drive

1. Title is `PaperFlick`. 「设置 ▾」 is collapsed. 发送间隔 is not mapped. The printer sidebar is mapped and to the left of the list. The status line is empty when `dry_run` is false. The failure bar is not mapped.
2. Open 设置. The interval, wait-queue, and 演练（不送打印机） controls are mapped, and the disclosure reads 「设置 ▴」. Close it. `settings.json` still has only `interval_seconds`, `wait_for_empty_queue`, `dry_run`, and `selected_printer`.
3. Turn 演练 on and persist. The idle status line is `演练（不送打印机）` even while 设置 is collapsed. `load().dry_run is True`.
4. Add two files, set a long interval, and 开始. The status line is `演练 · ` while the Batch is running. After the injected failure, the failure bar is mapped below the list and above 开始.
5. 停止. The status line returns to `演练（不送打印机）`. Shorten the interval and 开始 again. When the Batch finishes, the status line is `本批完成：成功 N、失败 M` with no 演练 prefix. The failure bar stays while a failed row remains.

## Evidence

`artifacts/settings-about/log.txt` and `settings.json` from `_run_settings_about.py`. Note headless versus a live window.

Proof: `mamba run -n paperflick pytest -q tests/test_drill_status.py tests/test_settings.py tests/test_gui.py tests/test_settings_about_window.py`

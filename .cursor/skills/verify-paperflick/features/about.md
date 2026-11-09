# About and version

Prove issue #43. The status row shows counts and the status line on the left, and a clickable `vX.Y.Z` on the right. The badge reads `paperflick.__version__`. That string matches `[project].version` in `pyproject.toml`. The window title stays `PaperFlick`. There is no version badge on the add toolbar, no auto-update, and no in-app changelog.

Clicking the badge opens About. The dialog shows `纸闪 PaperFlick`, `版本 X.Y.Z`, `个人向 Windows 批量打印工具`, the link `https://github.com/nancliu/PaperFlick`, and 「关闭」. The link opens in the system browser. A second click lifts the same dialog. About is not reached through 设置.

## Setup

Disposable `PAPERFLICK_APPDATA`. Construct `MainWindow` headless. Patch `webbrowser.open` so the proof does not launch a browser.

## Drive

1. The version button text is `v` plus `paperflick.__version__`, and it sits to the right of the status line.
2. Invoke the version button. About contains the four lines above and 「关闭」. The main window title is still `PaperFlick`.
3. Invoke the link. The patched browser opener receives `https://github.com/nancliu/PaperFlick`.
4. Invoke the version button again. The same About window is reused. 「关闭」 destroys it.

## Evidence

`artifacts/settings-about/log.txt` from `_run_settings_about.py`.

Proof: `mamba run -n paperflick pytest -q tests/test_version.py tests/test_about_info.py tests/test_settings_about_window.py`

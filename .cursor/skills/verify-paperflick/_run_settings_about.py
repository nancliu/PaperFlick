"""Headless proof for folded settings, the 演练 status, and About."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from pathlib import Path

import customtkinter as ctk

import paperflick.ui.about as about_module
import paperflick.ui.main_window as main_window_module
import paperflick.ui.printer_sidebar as printer_sidebar_module
from paperflick import __version__
from paperflick.core.batch import AddPaths, BatchPhase
from paperflick.core.settings import load, settings_path
from paperflick.core.submit import SubmitFailed, SubmitScript
from paperflick.ui.main_window import MainWindow
from paperflick.ui.sidebar_split import reset_sidebar_split_session

_SETTINGS_KEYS = {
    "interval_seconds",
    "wait_for_empty_queue",
    "dry_run",
    "selected_printer",
}


def _install_fake_printers() -> None:
    """Keep the sidebar off the machine's real printer list."""

    def _names() -> list[str]:
        return ["Front Desk", "Back Office"]

    main_window_module.list_installed_printers = _names
    printer_sidebar_module.system_default_printer = lambda: "Front Desk"


def _walk(widget: object) -> list[object]:
    """Return ``widget`` and every descendant."""
    found = [widget]
    children = getattr(widget, "winfo_children", None)
    if children is None:
        return found
    for child in children():
        found.extend(_walk(child))
    return found


def _texts(widget: object) -> list[str]:
    """Captions on labels, buttons, and checkboxes."""
    texts: list[str] = []
    for node in _walk(widget):
        if isinstance(node, (ctk.CTkLabel, ctk.CTkButton, ctk.CTkCheckBox)):
            text = str(node.cget("text"))
            if text:
                texts.append(text)
    return texts


def _button(app: MainWindow, caption: str) -> ctk.CTkButton:
    """Return the single button whose caption is ``caption``."""
    matches = [
        node
        for node in _walk(app)
        if isinstance(node, ctk.CTkButton) and str(node.cget("text")) == caption
    ]
    if len(matches) != 1:
        raise AssertionError(f"{caption}: {len(matches)}")
    button = matches[0]
    if not isinstance(button, ctk.CTkButton):
        raise AssertionError(caption)
    return button


def _wait_idle(app: MainWindow) -> None:
    """Pump Tk until the Batch is idle."""
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        app.update()
        snap = app._session.snapshot()
        if snap.phase is BatchPhase.IDLE and snap.waiting_count == 0 and snap.printing_count == 0:
            return
        time.sleep(0.02)
    raise AssertionError(app._session.snapshot().phase)


def _prove_boot(app: MainWindow, lines: list[str]) -> None:
    """Collapsed 设置, printer still on the left, version on the right, no drill hint yet."""
    assert app.title() == "PaperFlick"
    assert app._settings_toggle.cget("text") == "设置 ▾"
    assert not app._prefs.winfo_ismapped()
    assert not app._fail_toolbar.winfo_ismapped()
    assert app._status_label.cget("text") == ""
    assert app._version_button.cget("text") == f"v{__version__}"
    assert app._printer_sidebar.winfo_ismapped()
    assert app._printer_sidebar.winfo_rootx() < app._drop_area.winfo_rootx()
    label_right = app._status_label.winfo_rootx() + app._status_label.winfo_width()
    assert app._version_button.winfo_rootx() >= label_right - 8
    assert "演练（不送打印机）" in _texts(app._prefs)
    assert all("Dry Run" not in text for text in _texts(app))
    lines.append("boot collapsed settings; version on the status row; printer stays left")


def _prove_disclosure(app: MainWindow, lines: list[str]) -> None:
    """Open and close 设置 without writing that choice to settings.json."""
    app._settings_toggle.invoke()
    app.update_idletasks()
    assert app._prefs.winfo_ismapped()
    assert app._settings_toggle.cget("text") == "设置 ▴"
    assert "发送间隔（秒）" in _texts(app._prefs)
    assert "等待打印队列清空后再发下一份" in _texts(app._prefs)
    app._settings_toggle.invoke()
    app.update_idletasks()
    assert not app._prefs.winfo_ismapped()
    app._persist()
    raw = json.loads(settings_path().read_text(encoding="utf-8"))
    assert set(raw) == _SETTINGS_KEYS
    assert "settings_open" not in raw
    lines.append("disclosure is session-only")


def _prove_drill_and_failures(app: MainWindow, lines: list[str], root: Path) -> None:
    """Idle hint, in-batch prefix, unprefixed finish line, and the failure bar placement."""
    first = root / "a.pdf"
    second = root / "b.pdf"
    first.write_bytes(b"a")
    second.write_bytes(b"b")
    app._dry_var.set(True)
    app._interval_var.set("30")
    app._persist()
    assert load().dry_run is True
    assert app._status_label.cget("text") == "演练（不送打印机）"
    app._session.apply(AddPaths([first, second]))
    app._on_start()
    app.update()
    running = app._session.snapshot()
    assert running.phase is BatchPhase.RUNNING
    assert running.failed_count == 1
    assert app._status_label.cget("text") == "演练 · "
    assert app._fail_toolbar.winfo_ismapped()
    start = _button(app, "开始")
    list_bottom = app._item_list.winfo_rooty() + app._item_list.winfo_height()
    assert list_bottom <= app._fail_toolbar.winfo_rooty() + 4
    assert app._fail_toolbar.winfo_rooty() < start.winfo_rooty()
    lines.append("dry-run idle hint; batch prefix; fail bar under the list")

    app._on_stop()
    app.update_idletasks()
    assert app._session.snapshot().phase is BatchPhase.IDLE
    assert app._status_label.cget("text") == "演练（不送打印机）"
    app._interval_var.set("0.05")
    app._persist()
    app._on_start()
    _wait_idle(app)
    assert app._status_label.cget("text") == "本批完成：成功 1、失败 0"
    assert app._fail_toolbar.winfo_ismapped()
    lines.append("finish line stays unprefixed; fail bar remains while a row is failed")


def _prove_about(app: MainWindow, lines: list[str]) -> None:
    """The version badge opens About and the link uses the system browser."""
    opened: list[str] = []

    def _open(url: str) -> bool:
        opened.append(url)
        return True

    about_module.webbrowser.open = _open
    app._version_button.invoke()
    app.update_idletasks()
    about = app._about
    assert about is not None and about.winfo_exists()
    body = _texts(about)
    assert "纸闪 PaperFlick" in body
    assert f"版本 {__version__}" in body
    assert "个人向 Windows 批量打印工具" in body
    assert "https://github.com/nancliu/PaperFlick" in body
    assert "关闭" in body
    about._link.invoke()
    assert opened == ["https://github.com/nancliu/PaperFlick"]
    app._version_button.invoke()
    assert app._about is about
    _button(about, "关闭").invoke()
    app.update_idletasks()
    assert not about.winfo_exists()
    assert app.title() == "PaperFlick"
    lines.append("about from the version badge; window title stays PaperFlick")


def main() -> None:
    """Open one MainWindow and prove settings disclosure, 演练, and About."""
    appdata = Path(tempfile.mkdtemp(prefix="paperflick-settings-about-"))
    os.environ["PAPERFLICK_APPDATA"] = str(appdata)
    files = Path(tempfile.mkdtemp(prefix="paperflick-settings-about-files-"))
    artifact = Path(__file__).resolve().parent / "artifacts" / "settings-about"
    artifact.mkdir(parents=True, exist_ok=True)
    lines = ["headless MainWindow"]
    _install_fake_printers()
    reset_sidebar_split_session()
    app = MainWindow(submit_script=SubmitScript((SubmitFailed("卡纸"),)))
    try:
        app.update_idletasks()
        app.update()
        _prove_boot(app, lines)
        _prove_disclosure(app, lines)
        _prove_drill_and_failures(app, lines, files)
        _prove_about(app, lines)
        raw = json.loads(settings_path().read_text(encoding="utf-8"))
        assert set(raw) == _SETTINGS_KEYS
        (artifact / "settings.json").write_text(
            settings_path().read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        lines.append("PASS settings-about")
        (artifact / "log.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("PASS settings-about")
    finally:
        if app.winfo_exists():
            app.destroy()
        shutil.rmtree(appdata, ignore_errors=True)
        shutil.rmtree(files, ignore_errors=True)


if __name__ == "__main__":
    main()

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from paperflick.core.batch import (
    AddPaths,
    ApplyScope,
    BatchEvent,
    BatchPhase,
    BatchPrefs,
    BatchSession,
    BatchSnapshot,
    ClearSucceeded,
    ItemId,
    ItemStatus,
    Orientation,
    PauseBatch,
    RemoveItems,
    ReprintFailed,
    ResumeBatch,
    SetOrientation,
    StartBatch,
    StopBatch,
)
from paperflick.core.printers import list_installed_printers, selected_printer_for_persist
from paperflick.core.settings import Settings, coerce_interval_seconds, load, save
from paperflick.core.submit import (
    DryRunSubmit,
    PrintSubmitPort,
    StartNeedsDryRunError,
    SubmitScript,
)
from paperflick.ui.item_list import ItemListPanel
from paperflick.ui.preview_window import PreviewWindow
from paperflick.ui.printer_sidebar import PrinterSidebar


def _dry_run_factory(script: SubmitScript) -> Callable[[BatchPrefs], PrintSubmitPort]:
    """Reuse one script for every Start this window makes."""

    def factory(_prefs: BatchPrefs) -> PrintSubmitPort:
        return DryRunSubmit(script)

    return factory


class MainWindow(ctk.CTk):
    def __init__(
        self,
        settings: Settings | None = None,
        submit_script: SubmitScript | None = None,
    ) -> None:
        super().__init__()
        self.title("PaperFlick")
        self.geometry("780x520")
        self.minsize(640, 420)

        self._settings = settings if settings is not None else load()
        submit_factory = _dry_run_factory(submit_script) if submit_script is not None else None
        self._session = BatchSession(
            submit_factory=submit_factory,
            schedule_after=self._tk_schedule,
            cancel_after=self._tk_cancel,
        )
        self._session.subscribe(self._on_batch_event)
        self._after_handles: set[str] = set()
        self._preview: PreviewWindow | None = None

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=12)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        printers = list_installed_printers()
        self._printer_sidebar = PrinterSidebar(
            body,
            printers=printers,
            selected=self._settings.selected_printer,
            on_select=self._on_printer_selected,
            width=200,
        )
        self._printer_sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, 12))

        root = ctk.CTkFrame(body, fg_color="transparent")
        root.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(root, text="纸闪 PaperFlick", font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor="w", pady=(0, 12)
        )

        prefs = ctk.CTkFrame(root, fg_color="transparent")
        prefs.pack(fill="x", pady=(0, 8))

        interval_row = ctk.CTkFrame(prefs, fg_color="transparent")
        interval_row.pack(fill="x", pady=4)
        ctk.CTkLabel(interval_row, text="发送间隔（秒）").pack(side="left")
        self._interval_var = ctk.StringVar(value=str(self._settings.interval_seconds))
        self._interval_entry = ctk.CTkEntry(interval_row, textvariable=self._interval_var, width=80)
        self._interval_entry.pack(side="right")
        self._interval_entry.bind("<KeyRelease>", self._on_interval_typed)
        self._interval_entry.bind("<FocusOut>", self._on_interval_commit)
        self._interval_entry.bind("<Return>", self._on_interval_commit)

        self._wait_var = ctk.BooleanVar(value=self._settings.wait_for_empty_queue)
        ctk.CTkCheckBox(
            prefs,
            text="等待打印队列清空后再发下一份",
            variable=self._wait_var,
            command=self._persist,
        ).pack(anchor="w", pady=4)

        self._dry_var = ctk.BooleanVar(value=self._settings.dry_run)
        ctk.CTkCheckBox(
            prefs,
            text="Dry Run（只走流程，不真正打印）",
            variable=self._dry_var,
            command=self._persist,
        ).pack(anchor="w", pady=4)

        list_toolbar = ctk.CTkFrame(root, fg_color="transparent")
        list_toolbar.pack(fill="x", pady=(8, 4))
        ctk.CTkButton(list_toolbar, text="添加文件", width=90, command=self._on_add_files).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(list_toolbar, text="添加文件夹", width=90, command=self._on_add_folder).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(
            list_toolbar, text="移除所选", width=90, command=self._on_remove_selected
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(list_toolbar, text="预览", width=70, command=self._on_preview).pack(
            side="left"
        )

        fail_toolbar = ctk.CTkFrame(root, fg_color="transparent")
        fail_toolbar.pack(fill="x", pady=(0, 4))
        ctk.CTkButton(
            fail_toolbar, text="只勾选失败项", width=120, command=self._on_select_only_failed
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            fail_toolbar, text="重新打印失败项", width=130, command=self._on_reprint_failed
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            fail_toolbar, text="清除已成功", width=110, command=self._on_clear_succeeded
        ).pack(side="left")

        self._item_list = ItemListPanel(root)
        self._item_list.pack(fill="both", expand=True, pady=4)

        batch_bar = ctk.CTkFrame(root, fg_color="transparent")
        batch_bar.pack(fill="x", pady=(8, 4))
        ctk.CTkButton(batch_bar, text="开始", width=80, command=self._on_start).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(batch_bar, text="暂停", width=80, command=self._on_pause).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(batch_bar, text="继续", width=80, command=self._on_resume).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(batch_bar, text="停止", width=80, command=self._on_stop).pack(side="left")

        self._counts_label = ctk.CTkLabel(root, text="", anchor="w")
        self._counts_label.pack(fill="x", pady=(4, 0))
        self._status_label = ctk.CTkLabel(root, text="", anchor="w", text_color="gray")
        self._status_label.pack(fill="x")

        self._bind_list(self._session.snapshot())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _tk_schedule(self, delay_seconds: float, callback: object) -> str:
        ms = max(0, int(delay_seconds * 1000))
        handle = self.after(ms, callback)  # type: ignore[arg-type]
        self._after_handles.add(handle)
        return handle

    def _tk_cancel(self, handle: str) -> None:
        try:
            self.after_cancel(handle)
        except Exception:
            pass
        self._after_handles.discard(handle)

    def _on_add_files(self) -> None:
        paths = filedialog.askopenfilenames(parent=self, title="选择文件")
        if not paths:
            return
        self._session.apply(AddPaths([Path(p) for p in paths]))

    def _on_add_folder(self) -> None:
        folder = filedialog.askdirectory(parent=self, title="选择文件夹")
        if not folder:
            return
        self._session.apply(AddPaths([Path(folder)]))

    def _on_remove_selected(self) -> None:
        ids = self._item_list.selected_ids()
        if not ids:
            return
        self._session.apply(RemoveItems(ids))

    def _on_preview(self) -> None:
        """Open a preview for the single checked Print Item."""
        ids = self._item_list.selected_ids()
        if len(ids) != 1:
            self._status_label.configure(text="请只勾选一个打印项再预览")
            return
        anchor = ids[0]
        item = next((row for row in self._session.snapshot().items if row.id == anchor), None)
        if item is None:
            self._status_label.configure(text="请只勾选一个打印项再预览")
            return
        self._close_preview()
        self._preview = PreviewWindow(self, item, self._apply_orientation)
        self._status_label.configure(text="")

    def _apply_orientation(
        self, anchor: ItemId, orientation: Orientation, scope: ApplyScope
    ) -> bool:
        """Apply a preview command. Refuse this-item and same-kind when the row is gone.

        A no-op SetOrientation (same policy already on every targeted row) returns
        False so the preview stays open and status text is left alone.
        """
        if scope is not ApplyScope.ALL:
            present = any(row.id == anchor for row in self._session.snapshot().items)
            if not present:
                self._status_label.configure(text="预览的打印项已不在列表中")
                return False
        before = {row.id: row.orientation for row in self._session.snapshot().items}
        self._session.apply(SetOrientation(anchor=anchor, orientation=orientation, scope=scope))
        after = {row.id: row.orientation for row in self._session.snapshot().items}
        if before == after:
            return False
        self._status_label.configure(text="")
        return True

    def _close_preview(self) -> None:
        """Destroy an open preview, if any."""
        preview = self._preview
        if preview is not None and preview.winfo_exists():
            preview.destroy()
        self._preview = None

    def _on_select_only_failed(self) -> None:
        failed = self._session.snapshot().ids_with(ItemStatus.FAILED)
        self._item_list.check_only(failed)

    def _on_reprint_failed(self) -> None:
        self._persist()
        before = self._session.snapshot()
        if before.phase is not BatchPhase.IDLE or before.failed_count == 0:
            return
        failed = before.ids_with(ItemStatus.FAILED)
        prefs = BatchPrefs.from_settings(self._settings)
        try:
            self._session.apply(ReprintFailed(StartBatch(prefs=prefs)))
        except StartNeedsDryRunError as exc:
            self._show_start_error(exc)
            return
        self._item_list.check_only(failed)
        self._status_label.configure(text="")

    def _on_clear_succeeded(self) -> None:
        self._session.apply(ClearSucceeded())

    def _on_start(self) -> None:
        self._persist()
        prefs = BatchPrefs.from_settings(self._settings)
        try:
            self._session.apply(StartBatch(prefs=prefs))
        except StartNeedsDryRunError as exc:
            self._show_start_error(exc)
            return
        self._status_label.configure(text="")

    def _show_start_error(self, exc: Exception) -> None:
        self._status_label.configure(text=str(exc))
        messagebox.showinfo("无法开始", str(exc), parent=self)

    def _on_pause(self) -> None:
        self._session.apply(PauseBatch())

    def _on_resume(self) -> None:
        self._session.apply(ResumeBatch())

    def _on_stop(self) -> None:
        self._session.apply(StopBatch())

    def _on_batch_event(self, _event: BatchEvent) -> None:
        self._bind_list(self._session.snapshot())

    def _bind_list(self, snapshot: BatchSnapshot) -> None:
        self._item_list.bind_snapshot(snapshot)
        self._counts_label.configure(
            text=(
                f"成功 {snapshot.success_count}  ·  失败 {snapshot.failed_count}  ·  "
                f"等待 {snapshot.waiting_count}  ·  打印中 {snapshot.printing_count}  ·  "
                f"状态 {snapshot.phase.value}"
            )
        )

    def _on_printer_selected(self, name: str) -> None:
        self._printer_sidebar.apply_selection(name)
        self._persist()

    def _selected_printer_for_persist(self) -> str | None:
        return selected_printer_for_persist(
            self._printer_sidebar.selected_name(),
            self._settings.selected_printer,
        )

    def _on_interval_typed(self, _event: object | None = None) -> None:
        raw = self._interval_var.get().strip()
        try:
            value = float(raw)
        except ValueError:
            return
        if value <= 0:
            return
        self._settings = Settings(
            interval_seconds=value,
            wait_for_empty_queue=bool(self._wait_var.get()),
            dry_run=bool(self._dry_var.get()),
            selected_printer=self._selected_printer_for_persist(),
        )
        save(self._settings)

    def _on_interval_commit(self, _event: object | None = None) -> None:
        value = coerce_interval_seconds(
            self._interval_var.get().strip(),
            self._settings.interval_seconds,
        )
        self._interval_var.set(str(value))
        self._persist()

    def _persist(self) -> None:
        self._settings = Settings(
            interval_seconds=coerce_interval_seconds(
                self._interval_var.get().strip(),
                self._settings.interval_seconds,
            ),
            wait_for_empty_queue=bool(self._wait_var.get()),
            dry_run=bool(self._dry_var.get()),
            selected_printer=self._selected_printer_for_persist(),
        )
        save(self._settings)

    def _on_close(self) -> None:
        self._session.apply(StopBatch())
        for handle in list(self._after_handles):
            self._tk_cancel(handle)
        self._persist()
        self.destroy()


def run() -> None:
    app = MainWindow()
    app.mainloop()

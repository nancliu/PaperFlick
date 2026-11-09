from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

from paperflick import __version__
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
    RunReported,
    SetOrientation,
    StartBatch,
    StopBatch,
)
from paperflick.core.batch.drop_intake import classify_dropped_paths, parse_dnd_files_payload
from paperflick.core.batch.gate import SpoolerProbe
from paperflick.core.printers import list_installed_printers, selected_printer_for_persist
from paperflick.core.settings import Settings, coerce_interval_seconds, load, save
from paperflick.core.submit import (
    DeviceFactory,
    DryRunSubmit,
    PrintSubmitPort,
    SubmitScript,
    SumatraRunner,
    choose_submit_port,
)
from paperflick.ui.about import AboutWindow
from paperflick.ui.about_info import version_badge
from paperflick.ui.drill_status import DRILL_UI_LABEL, format_status_line
from paperflick.ui.item_list import ItemListPanel
from paperflick.ui.preview_window import PreviewWindow
from paperflick.ui.printer_sidebar import PrinterSidebar
from paperflick.ui.sidebar_split import (
    SIDEBAR_DEFAULT_PX,
    SIDEBAR_MIN_PX,
    clamp_sidebar_width,
    displayed_sidebar_width,
    remember_sidebar_width,
    session_sidebar_preferred_px,
)


def _dry_run_factory(script: SubmitScript) -> Callable[[BatchPrefs], PrintSubmitPort]:
    """Reuse one script for every Start this window makes."""

    def factory(_prefs: BatchPrefs) -> PrintSubmitPort:
        return DryRunSubmit(script)

    return factory


def _port_factory(
    executable: Path | None,
    run: SumatraRunner | None,
    devices: DeviceFactory | None,
    docx: PrintSubmitPort | None,
) -> Callable[[BatchPrefs], PrintSubmitPort]:
    """Build a port per Start. Dry Run still skips the live engines."""

    def factory(prefs: BatchPrefs) -> PrintSubmitPort:
        return choose_submit_port(
            prefs,
            executable=executable,
            run=run,
            devices=devices,
            docx=docx,
        )

    return factory


class MainWindow(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(
        self,
        settings: Settings | None = None,
        submit_script: SubmitScript | None = None,
        *,
        sumatra_executable: Path | None = None,
        sumatra_run: SumatraRunner | None = None,
        image_devices: DeviceFactory | None = None,
        docx_submit: PrintSubmitPort | None = None,
        spooler: SpoolerProbe | None = None,
    ) -> None:
        super().__init__()
        self.TkdndVersion = TkinterDnD.require(self)
        self.title("PaperFlick")
        self.geometry("780x640")
        self.minsize(640, 500)

        self._settings = settings if settings is not None else load()
        if submit_script is not None:
            submit_factory = _dry_run_factory(submit_script)
        elif (
            sumatra_executable is None
            and sumatra_run is None
            and image_devices is None
            and docx_submit is None
        ):
            submit_factory = None
        else:
            submit_factory = _port_factory(
                sumatra_executable,
                sumatra_run,
                image_devices,
                docx_submit,
            )
        self._session = BatchSession(
            submit_factory=submit_factory,
            schedule_after=self._tk_schedule,
            cancel_after=self._tk_cancel,
            spooler=spooler,
        )
        self._session.subscribe(self._on_batch_event)
        self._after_handles: set[str] = set()
        self._preview: PreviewWindow | None = None
        self._about: AboutWindow | None = None
        self._settings_open = False

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=12)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        root = self._build_printer_split(body)

        title_row = ctk.CTkFrame(root, fg_color="transparent")
        title_row.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            title_row, text="纸闪 PaperFlick", font=ctk.CTkFont(size=18, weight="bold")
        ).pack(side="left")
        self._settings_toggle = ctk.CTkButton(
            title_row,
            text="设置 ▾",
            width=96,
            height=28,
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            command=self._toggle_settings,
        )
        self._settings_toggle.pack(side="left", padx=(12, 0))

        self._prefs = ctk.CTkFrame(root, fg_color="transparent")

        interval_row = ctk.CTkFrame(self._prefs, fg_color="transparent")
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
            self._prefs,
            text="等待打印队列清空后再发下一份",
            variable=self._wait_var,
            command=self._persist,
        ).pack(anchor="w", pady=4)

        self._dry_var = ctk.BooleanVar(value=self._settings.dry_run)
        ctk.CTkCheckBox(
            self._prefs,
            text=DRILL_UI_LABEL,
            variable=self._dry_var,
            command=self._persist,
        ).pack(anchor="w", pady=4)

        self._drop_area = ctk.CTkFrame(root, fg_color="transparent")
        self._drop_area.pack(fill="both", expand=True)
        drop_area = self._drop_area

        list_toolbar = ctk.CTkFrame(drop_area, fg_color="transparent")
        list_toolbar.pack(fill="x", pady=(8, 4))
        ctk.CTkButton(list_toolbar, text="添加文件", width=90, command=self._on_add_files).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(list_toolbar, text="添加文件夹", width=90, command=self._on_add_folder).pack(
            side="left", padx=(0, 6)
        )

        self._item_list = ItemListPanel(
            drop_area,
            on_preview=self._on_preview_item,
            on_remove=self._on_remove_item,
        )
        self._item_list.pack(fill="both", expand=True, pady=4)

        self._fail_toolbar = ctk.CTkFrame(root, fg_color="transparent")
        ctk.CTkButton(
            self._fail_toolbar, text="移除全部失败", width=120, command=self._on_remove_all_failed
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            self._fail_toolbar, text="重新打印失败项", width=130, command=self._on_reprint_failed
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            self._fail_toolbar, text="清除已成功", width=110, command=self._on_clear_succeeded
        ).pack(side="left")

        self._batch_bar = ctk.CTkFrame(root, fg_color="transparent")
        self._batch_bar.pack(fill="x", pady=(8, 4))
        ctk.CTkButton(self._batch_bar, text="开始", width=80, command=self._on_start).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(self._batch_bar, text="暂停", width=80, command=self._on_pause).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(self._batch_bar, text="继续", width=80, command=self._on_resume).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(self._batch_bar, text="停止", width=80, command=self._on_stop).pack(
            side="left"
        )

        self._wire_drop_targets(drop_area, list_toolbar, self._fail_toolbar, self._item_list)

        status_row = ctk.CTkFrame(root, fg_color="transparent")
        status_row.pack(fill="x", pady=(4, 0))
        status_text = ctk.CTkFrame(status_row, fg_color="transparent")
        status_text.pack(side="left", fill="x", expand=True)
        self._counts_label = ctk.CTkLabel(status_text, text="", anchor="w")
        self._counts_label.pack(fill="x")
        self._status_label = ctk.CTkLabel(status_text, text="", anchor="w", text_color="gray")
        self._status_label.pack(fill="x")
        self._version_button = ctk.CTkButton(
            status_row,
            text=version_badge(__version__),
            width=72,
            height=28,
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            text_color="gray",
            command=self._open_about,
        )
        self._version_button.pack(side="right", padx=(8, 0))

        self._bind_list(self._session.snapshot())
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        if (
            self._settings.selected_printer is None
            and self._printer_sidebar.selected_name() is not None
        ):
            self._persist()

    def _build_printer_split(self, body: ctk.CTkFrame) -> ctk.CTkFrame:
        """Build the printer sidebar and the content pane around a draggable sash.

        The left pane starts near 280px in the same units as the 780×640
        geometry. Dragging stays between 200px and half the window. High-DPI
        scaling is applied at the paned window. The position lasts for this
        process only.
        """
        self._sash_dragging = False
        self._syncing_sash = False
        self._split = tk.PanedWindow(
            body,
            orient=tk.HORIZONTAL,
            sashwidth=6,
            sashrelief=tk.FLAT,
            sashcursor="sb_h_double_arrow",
            opaqueresize=True,
            bd=0,
            bg=self._paned_background(),
        )
        self._split.grid(row=0, column=0, sticky="nsew")

        initial = displayed_sidebar_width(self._layout_window_width())
        self._printer_sidebar = PrinterSidebar(
            self._split,
            printers=list_installed_printers(),
            selected=self._settings.selected_printer,
            on_select=self._on_printer_selected,
            width=initial,
        )
        minimum = self._physical_px(SIDEBAR_MIN_PX)
        self._split.add(
            self._printer_sidebar,
            minsize=minimum,
            width=self._physical_px(initial),
            stretch="never",
        )
        root = ctk.CTkFrame(self._split, fg_color="transparent")
        self._split_content = root
        self._split.add(root, minsize=minimum, stretch="always")
        self._split.bind("<ButtonPress-1>", self._on_sidebar_sash_press)
        self._split.bind("<B1-Motion>", self._on_sidebar_sash_drag)
        self._split.bind("<ButtonRelease-1>", self._on_sidebar_sash_release)
        self._split.bind("<Configure>", self._on_sidebar_split_configure)
        return root

    def _paned_background(self) -> str:
        """Match the paned sash track to the main window background."""
        applied = self._apply_appearance_mode(self.cget("fg_color"))
        if isinstance(applied, str) and applied not in {"", "transparent"}:
            return applied
        return "gray20"

    def _window_scaling(self) -> float:
        """Return the CustomTkinter window scale. 1 means geometry pixels match the screen."""
        scaling = float(self._get_window_scaling())
        if scaling <= 0:
            return 1.0
        return scaling

    def _physical_px(self, logical: int) -> int:
        """Convert a geometry pixel count into paned-window pixels."""
        return max(1, int(round(logical * self._window_scaling())))

    def _logical_px(self, physical: int) -> int:
        """Convert a paned-window pixel count into geometry pixels."""
        return int(round(physical / self._window_scaling()))

    def _layout_window_width(self) -> int:
        """Return the window width in geometry pixels, the same space as 780×640."""
        width = int(self.winfo_width())
        if width > 1:
            return max(1, self._logical_px(width))
        raw = self.geometry().split("+", 1)[0].split("x")[0]
        try:
            parsed = int(raw)
        except ValueError:
            return 780
        return parsed if parsed > 1 else 780

    def _apply_sidebar_sash(self, requested_px: int, *, remember: bool) -> int:
        """Move the left pane to ``requested_px`` geometry pixels, clamped to the drag range."""
        shown = clamp_sidebar_width(requested_px, self._layout_window_width())
        if remember:
            remember_sidebar_width(shown)
        self._place_sidebar_sash(shown)
        return shown

    def _sync_sidebar_sash(self) -> None:
        """Re-clamp the remembered sash after the window size changes."""
        if self._sash_dragging:
            return
        preferred = session_sidebar_preferred_px()
        requested = SIDEBAR_DEFAULT_PX if preferred is None else preferred
        shown = clamp_sidebar_width(requested, self._layout_window_width())
        self._place_sidebar_sash(shown)

    def _place_sidebar_sash(self, shown: int) -> None:
        """Move the sash to ``shown`` geometry pixels when it is not already there."""
        if self._syncing_sash:
            return
        physical = self._physical_px(shown)
        self._apply_pane_minsize()
        try:
            current = int(self._split.sash_coord(0)[0])
        except tk.TclError:
            return
        if abs(current - physical) <= max(1, int(round(self._window_scaling()))):
            return
        self._syncing_sash = True
        try:
            self._commit_sash(physical)
        finally:
            self._syncing_sash = False

    def _commit_sash(self, physical: int) -> None:
        """Place the sash, then place it once more if the pane's request blocked the first move."""
        tolerance = max(1, int(round(self._window_scaling())))
        try:
            self._split.sash_place(0, physical, 1)
            current = int(self._split.sash_coord(0)[0])
            if abs(current - physical) <= tolerance:
                return
            self.update_idletasks()
            self._split.sash_place(0, physical, 1)
        except tk.TclError:
            return

    def _apply_pane_minsize(self) -> None:
        """Keep both panes from shrinking below 200 geometry pixels."""
        minimum = self._physical_px(SIDEBAR_MIN_PX)
        try:
            self._split.paneconfigure(self._printer_sidebar, minsize=minimum)
        except tk.TclError:
            return
        content = getattr(self, "_split_content", None)
        if content is None:
            return
        try:
            self._split.paneconfigure(content, minsize=minimum)
        except tk.TclError:
            return

    def _on_sidebar_sash_press(self, event: tk.Event) -> str | None:
        """Start a sidebar drag when the pointer is on the sash."""
        if "sash" not in str(self._split.identify(event.x, event.y)):
            return None
        self._sash_dragging = True
        return "break"

    def _on_sidebar_sash_drag(self, event: tk.Event) -> str | None:
        """Keep a dragged sash inside 200px .. half the window."""
        if not self._sash_dragging:
            return None
        self._apply_sidebar_sash(self._logical_px(int(event.x)), remember=False)
        return "break"

    def _on_sidebar_sash_release(self, event: tk.Event) -> str | None:
        """Remember the released sash for the rest of this process."""
        if not self._sash_dragging:
            return None
        self._sash_dragging = False
        self._apply_sidebar_sash(self._logical_px(int(event.x)), remember=True)
        return "break"

    def _on_sidebar_split_configure(self, event: tk.Event) -> None:
        """Keep the sash in range when the split or the window changes size.

        The place is deferred so it runs after this turn's geometry settles.
        A wide status row would otherwise keep the left pane at its requested
        width instead of the 280px default.
        """
        if event.widget is not self._split or self._sash_dragging or self._syncing_sash:
            return
        self.after_idle(self._sync_sidebar_sash)

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

    def _wire_drop_targets(self, *widgets: ctk.CTkBaseClass) -> None:
        """Register the main content area (list + toolbars) for Explorer drops."""
        for widget in widgets:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_drop_files)

    def _toggle_settings(self) -> None:
        """Show or hide interval, wait-queue, and Dry Run. Not written to settings."""
        self._settings_open = not self._settings_open
        if self._settings_open:
            self._prefs.pack(fill="x", pady=(0, 8), before=self._drop_area)
            self._settings_toggle.configure(text="设置 ▴")
            return
        self._prefs.pack_forget()
        self._settings_toggle.configure(text="设置 ▾")

    def _open_about(self) -> None:
        """Open About from the version badge. A second click lifts the same dialog."""
        about = self._about
        if about is not None and about.winfo_exists():
            about.lift()
            about.focus_force()
            return
        self._about = AboutWindow(self)

    def _sync_fail_toolbar(self, failed_count: int) -> None:
        """Show failure actions only when a row has failed.

        The bar sits under the list and above Start / Pause / Resume / Stop.
        """
        mapped = bool(self._fail_toolbar.winfo_ismapped())
        if failed_count > 0 and not mapped:
            self._fail_toolbar.pack(fill="x", pady=(4, 4), before=self._batch_bar)
        elif failed_count <= 0 and mapped:
            self._fail_toolbar.pack_forget()

    def _apply_status(self, message: str) -> None:
        """Show ``message``, adding the Dry Run idle hint or batch prefix."""
        active = self._session.snapshot().phase is not BatchPhase.IDLE
        text = format_status_line(
            message,
            dry_run=bool(self._dry_var.get()),
            batch_active=active,
        )
        self._status_label.configure(text=text)

    def _refresh_status(self) -> None:
        """Recompute the status line from the text it already shows."""
        self._apply_status(str(self._status_label.cget("text")))

    def _on_drop_files(self, event: object) -> None:
        """Parse a DnD payload, filter UNKNOWN, then AddPaths like button intake."""
        data = getattr(event, "data", None)
        if not data:
            return
        raw_paths = parse_dnd_files_payload(str(data))
        if not raw_paths:
            return
        intake = classify_dropped_paths(raw_paths)
        if intake.paths:
            self._session.apply(AddPaths(list(intake.paths)))
        if intake.status_text:
            self._apply_status(intake.status_text)

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

    def _on_remove_item(self, item_id: ItemId) -> None:
        """Remove one Print Item. No confirm; allowed while a Batch is active."""
        self._session.apply(RemoveItems((item_id,)))

    def _on_remove_all_failed(self) -> None:
        """Confirm, then remove every FAILED Print Item."""
        failed = self._session.snapshot().ids_with(ItemStatus.FAILED)
        if not failed:
            return
        if not messagebox.askyesno(
            "移除全部失败",
            "将从列表中移除全部失败的打印项。是否继续？",
            parent=self,
        ):
            return
        self._session.apply(RemoveItems(failed))

    def _on_preview_item(self, item_id: ItemId) -> None:
        """Close any open preview, then open this Print Item."""
        item = next((row for row in self._session.snapshot().items if row.id == item_id), None)
        if item is None:
            return
        self._close_preview()
        self._preview = PreviewWindow(self, item, self._apply_orientation)
        self._apply_status("")

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
                self._apply_status("预览的打印项已不在列表中")
                return False
        before = {row.id: row.orientation for row in self._session.snapshot().items}
        self._session.apply(SetOrientation(anchor=anchor, orientation=orientation, scope=scope))
        after = {row.id: row.orientation for row in self._session.snapshot().items}
        if before == after:
            return False
        self._apply_status("")
        return True

    def _close_preview(self) -> None:
        """Destroy an open preview, if any."""
        preview = self._preview
        if preview is not None and preview.winfo_exists():
            preview.destroy()
        self._preview = None

    def _on_reprint_failed(self) -> None:
        self._persist()
        before = self._session.snapshot()
        if before.phase is not BatchPhase.IDLE or before.failed_count == 0:
            return
        self._apply_status("")
        prefs = BatchPrefs.from_settings(self._settings)
        self._session.apply(ReprintFailed(StartBatch(prefs=prefs)))

    def _on_clear_succeeded(self) -> None:
        self._session.apply(ClearSucceeded())

    def _on_start(self) -> None:
        self._persist()
        if self._session.snapshot().phase is not BatchPhase.IDLE:
            return
        self._apply_status("")
        prefs = BatchPrefs.from_settings(self._settings)
        self._session.apply(StartBatch(prefs=prefs))

    def _on_pause(self) -> None:
        self._session.apply(PauseBatch())

    def _on_resume(self) -> None:
        self._session.apply(ResumeBatch())

    def _on_stop(self) -> None:
        self._session.apply(StopBatch())

    def _on_batch_event(self, event: BatchEvent) -> None:
        self._bind_list(self._session.snapshot())
        if isinstance(event, RunReported):
            self._apply_status(event.text)

    def _bind_list(self, snapshot: BatchSnapshot) -> None:
        self._item_list.bind_snapshot(snapshot)
        self._counts_label.configure(
            text=(
                f"成功 {snapshot.success_count}  ·  失败 {snapshot.failed_count}  ·  "
                f"等待 {snapshot.waiting_count}  ·  打印中 {snapshot.printing_count}  ·  "
                f"状态 {snapshot.phase.value}"
            )
        )
        self._sync_fail_toolbar(snapshot.failed_count)
        self._refresh_status()

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
        self._refresh_status()

    def _on_close(self) -> None:
        self._session.apply(StopBatch())
        for handle in list(self._after_handles):
            self._tk_cancel(handle)
        self._persist()
        self.destroy()


def run() -> None:
    app = MainWindow()
    app.mainloop()

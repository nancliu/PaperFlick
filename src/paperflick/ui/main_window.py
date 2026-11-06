from __future__ import annotations

import customtkinter as ctk

from paperflick.core.settings import Settings, load, save


class MainWindow(ctk.CTk):
    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
        self.title("PaperFlick")
        self.geometry("420x240")
        self.minsize(360, 200)

        self._settings = settings if settings is not None else load()

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        root = ctk.CTkFrame(self, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(root, text="纸闪 PaperFlick", font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor="w", pady=(0, 16)
        )

        interval_row = ctk.CTkFrame(root, fg_color="transparent")
        interval_row.pack(fill="x", pady=4)
        ctk.CTkLabel(interval_row, text="发送间隔（秒）").pack(side="left")
        self._interval_var = ctk.StringVar(value=str(self._settings.interval_seconds))
        self._interval_entry = ctk.CTkEntry(interval_row, textvariable=self._interval_var, width=80)
        self._interval_entry.pack(side="right")
        self._interval_entry.bind("<FocusOut>", self._on_interval_commit)
        self._interval_entry.bind("<Return>", self._on_interval_commit)

        self._wait_var = ctk.BooleanVar(value=self._settings.wait_for_empty_queue)
        ctk.CTkCheckBox(
            root,
            text="等待打印队列清空后再发下一份",
            variable=self._wait_var,
            command=self._persist,
        ).pack(anchor="w", pady=8)

        self._dry_var = ctk.BooleanVar(value=self._settings.dry_run)
        ctk.CTkCheckBox(
            root,
            text="Dry Run（只走流程，不真正打印）",
            variable=self._dry_var,
            command=self._persist,
        ).pack(anchor="w", pady=4)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _read_interval(self) -> float:
        raw = self._interval_var.get().strip()
        try:
            value = float(raw)
        except ValueError:
            value = self._settings.interval_seconds
        if value <= 0:
            value = self._settings.interval_seconds
        self._interval_var.set(str(value))
        return value

    def _on_interval_commit(self, _event: object | None = None) -> None:
        self._persist()

    def _persist(self) -> None:
        self._settings = Settings(
            interval_seconds=self._read_interval(),
            wait_for_empty_queue=bool(self._wait_var.get()),
            dry_run=bool(self._dry_var.get()),
        )
        save(self._settings)

    def _on_close(self) -> None:
        self._persist()
        self.destroy()


def run() -> None:
    app = MainWindow()
    app.mainloop()

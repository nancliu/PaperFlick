"""Preview one Print Item and apply an Orientation by scope."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

from paperflick.core.batch import ApplyScope, DocKind, ItemId, Orientation, PrintItem
from paperflick.ui.item_list import orientation_label

ApplyHandler = Callable[[ItemId, Orientation, ApplyScope], bool]

_KIND_LABEL = {
    DocKind.PDF: "PDF",
    DocKind.DOCX: "DOCX",
    DocKind.IMAGE: "图片",
    DocKind.UNKNOWN: "未知",
}

_CHOICES = (
    (Orientation.LANDSCAPE, "横向"),
    (Orientation.PORTRAIT, "纵向"),
    (Orientation.PRINTER_DEFAULT, "打印机"),
)


def _page_image(path: Path) -> Image.Image | None:
    """Return a small RGB thumbnail, or None when the file cannot be drawn."""
    try:
        with Image.open(path) as source:
            frame = source.convert("RGB")
            frame.thumbnail((360, 240))
            return frame.copy()
    except OSError:
        return None


class PreviewWindow(ctk.CTkToplevel):
    """Choose Landscape, Portrait, or PrinterDefault and apply it."""

    def __init__(self, master: ctk.CTk, item: PrintItem, on_apply: ApplyHandler) -> None:
        super().__init__(master)
        self.title("预览")
        self.geometry("440x520")
        self.minsize(360, 420)
        self._anchor = item.id
        self._on_apply = on_apply
        self._photo: ctk.CTkImage | None = None
        initial = "" if item.orientation is Orientation.AUTO else item.orientation.value
        self._choice = ctk.StringVar(value=initial)

        self._build_summary(item)
        self._build_page(item)
        self._build_choices()
        self._hint = ctk.CTkLabel(self, text="", anchor="w", text_color="gray")
        self._hint.pack(fill="x", padx=16, pady=(4, 0))
        self._build_actions()

        self.transient(master)
        self.lift()
        self.focus_force()

    def _build_summary(self, item: PrintItem) -> None:
        """Show the file name, kind, and current list mark."""
        name = item.path.name or str(item.path)
        kind = _KIND_LABEL.get(item.kind, item.kind.value)
        ctk.CTkLabel(self, text=name, font=ctk.CTkFont(size=16, weight="bold"), anchor="w").pack(
            fill="x", padx=16, pady=(16, 4)
        )
        ctk.CTkLabel(
            self,
            text=f"{kind}  ·  当前 {orientation_label(item)}",
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 8))

    def _build_page(self, item: PrintItem) -> None:
        """Draw an image thumbnail. Other kinds keep a text fallback."""
        drawn = _page_image(item.path) if item.kind is DocKind.IMAGE else None
        if drawn is None:
            ctk.CTkLabel(
                self,
                text="此类型暂不绘制页面，仍可选择方向并应用",
                anchor="w",
                wraplength=380,
            ).pack(fill="x", padx=16, pady=8)
            return
        self._photo = ctk.CTkImage(light_image=drawn, size=(drawn.width, drawn.height))
        ctk.CTkLabel(self, text="", image=self._photo).pack(padx=16, pady=8)

    def _build_choices(self) -> None:
        """Radios for the three preview policies. Auto is not offered."""
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.pack(fill="x", padx=16, pady=4)
        for policy, label in _CHOICES:
            ctk.CTkRadioButton(
                box,
                text=label,
                variable=self._choice,
                value=policy.value,
            ).pack(anchor="w", pady=2)

    def _build_actions(self) -> None:
        """Apply buttons. All confirms before the command is sent."""
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=16, pady=12)
        ctk.CTkButton(bar, text="应用到此项", command=lambda: self._commit(ApplyScope.THIS)).pack(
            fill="x", pady=2
        )
        ctk.CTkButton(
            bar, text="应用到同类型", command=lambda: self._commit(ApplyScope.SAME_KIND)
        ).pack(fill="x", pady=2)
        ctk.CTkButton(bar, text="应用到全部", command=lambda: self._commit(ApplyScope.ALL)).pack(
            fill="x", pady=2
        )

    def _chosen(self) -> Orientation | None:
        """Return the selected policy, or None when the user has not chosen."""
        raw = self._choice.get()
        if not raw:
            return None
        return Orientation(raw)

    def _commit(self, scope: ApplyScope) -> None:
        """Apply ``scope`` and close when the shell accepts the command."""
        orientation = self._chosen()
        if orientation is None:
            self._hint.configure(text="请先选择方向")
            return
        if scope is ApplyScope.ALL and not messagebox.askyesno(
            "应用到全部",
            "将把所选方向应用到列表中的全部打印项。是否继续？",
            parent=self,
        ):
            return
        if self._on_apply(self._anchor, orientation, scope):
            self.destroy()

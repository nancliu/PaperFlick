"""Preview one Print Item and apply an Orientation by scope."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

from paperflick.core.batch import ApplyScope, DocKind, ItemId, Orientation, PrintItem
from paperflick.core.shell_thumbnail import ShellThumbnailPort, windows_shell_thumbnail
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


_THUMB_SIZE = (360, 240)
PAGE_FALLBACK_TEXT = "此类型暂不绘制页面，仍可选择方向并应用"


def _image_page(path: Path) -> Image.Image | None:
    """Return a small RGB thumbnail for an image file, or None on failure."""
    try:
        with Image.open(path) as source:
            frame = source.convert("RGB")
            frame.thumbnail(_THUMB_SIZE)
            return frame.copy()
    except OSError:
        return None


def _pdf_page(path: Path) -> Image.Image | None:
    """Return a small RGB thumbnail of the first PDF page, or None on failure."""
    try:
        import pymupdf
    except ImportError:
        return None
    try:
        doc = pymupdf.open(path)
    except Exception:
        return None
    try:
        if doc.page_count < 1:
            return None
        pix = doc.load_page(0).get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
        frame = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        frame.thumbnail(_THUMB_SIZE)
        return frame
    except Exception:
        return None
    finally:
        doc.close()


def _docx_page(
    path: Path,
    shell_thumbnail: ShellThumbnailPort | None = None,
) -> Image.Image | None:
    """Return a Shell first-page thumbnail for DOCX/DOC, or None on failure."""
    get_thumb = shell_thumbnail if shell_thumbnail is not None else windows_shell_thumbnail
    try:
        frame = get_thumb(path)
    except Exception:
        return None
    if frame is None:
        return None
    try:
        rgb = frame.convert("RGB")
        rgb.thumbnail(_THUMB_SIZE)
        return rgb
    except Exception:
        return None


def _page_image(
    item: PrintItem,
    *,
    shell_thumbnail: ShellThumbnailPort | None = None,
) -> Image.Image | None:
    """Return a page thumbnail for kinds that can be drawn, else None."""
    if item.kind is DocKind.IMAGE:
        return _image_page(item.path)
    if item.kind is DocKind.PDF:
        return _pdf_page(item.path)
    if item.kind is DocKind.DOCX:
        return _docx_page(item.path, shell_thumbnail)
    return None


class PreviewWindow(ctk.CTkToplevel):
    """Choose Landscape, Portrait, or PrinterDefault and apply it.

    Chrome (summary, orientation, actions) is shown before any thumbnail work.
    Raster runs on the next idle turn after the window is mapped.
    """

    def __init__(self, master: ctk.CTk, item: PrintItem, on_apply: ApplyHandler) -> None:
        super().__init__(master)
        self.title("预览")
        self.geometry("440x520")
        self.minsize(360, 420)
        self._anchor = item.id
        self._item = item
        self._on_apply = on_apply
        self._photo: ctk.CTkImage | None = None
        self._raster_queued = False
        self._raster_done = False
        initial = "" if item.orientation is Orientation.AUTO else item.orientation.value
        self._choice = ctk.StringVar(value=initial)

        self._build_summary(item)
        self._page_slot = ctk.CTkFrame(self, fg_color="transparent")
        self._page_slot.pack(fill="x", padx=16, pady=8)
        self._build_choices()
        self._hint = ctk.CTkLabel(self, text="", anchor="w", text_color="gray")
        self._hint.pack(fill="x", padx=16, pady=(4, 0))
        self._build_actions()

        self.transient(master)
        self.bind("<Map>", self._on_map, add="+")
        self.deiconify()
        self._raise_into_view()
        self.after_idle(self._kick_raster)

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

    def _on_map(self, _event: object = None) -> None:
        """Map happened. Raster on a later idle turn so this handler stays light."""
        self.after_idle(self._kick_raster)

    def _kick_raster(self) -> None:
        """Queue thumbnail work only once the window is mapped."""
        if not self.winfo_exists() or self._raster_queued or self._raster_done:
            return
        if not self.winfo_ismapped():
            self.after(10, self._kick_raster)
            return
        self._raster_queued = True
        self._raise_into_view()
        self.after_idle(self._raster_page)

    def _raster_page(self) -> None:
        """Draw a thumbnail or the text fallback. Never run this from ``__init__``."""
        if not self.winfo_exists() or self._raster_done:
            return
        self._raster_done = True
        drawn: Image.Image | None = None
        try:
            drawn = _page_image(self._item)
        except Exception:
            drawn = None
        if not self.winfo_exists():
            return
        self._show_page(drawn)
        self._raise_into_view()

    def _show_page(self, drawn: Image.Image | None) -> None:
        """Fill the page slot. ``None`` keeps the text fallback."""
        if not self._page_slot.winfo_exists():
            return
        for child in self._page_slot.winfo_children():
            child.destroy()
        if drawn is None:
            ctk.CTkLabel(
                self._page_slot,
                text=PAGE_FALLBACK_TEXT,
                anchor="w",
                wraplength=380,
            ).pack(fill="x")
            return
        self._photo = ctk.CTkImage(light_image=drawn, size=(drawn.width, drawn.height))
        ctk.CTkLabel(self._page_slot, text="", image=self._photo).pack()

    def _raise_into_view(self) -> None:
        """Lift and focus so the preview stays in front after map and raster."""
        if not self.winfo_exists():
            return
        self.lift()
        self.focus_force()

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

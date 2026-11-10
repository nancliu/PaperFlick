"""Preview one Print Item and apply an Orientation by scope."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

from paperflick.core.batch import (
    ApplyScope,
    DocKind,
    Facing,
    ItemId,
    Orientation,
    PageShape,
    PrintItem,
    resolve_facing,
)
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
_CANVAS_SIZE = (380, 260)
_PAPER_INSET = 12
_CONTENT_PAD = 8
_CANVAS_COLOR = "#C8C8C8"
_PAPER_COLOR = "#FFFFFF"
_UNFORCED_PAPER_COLOR = "#F3F3F3"

# A4 short/long edge ratio (mm). Portrait width/height == short/long.
_A4_SHORT = 210.0
_A4_LONG = 297.0

UNFORCED_COPY = "不强制朝向"
PAGE_FALLBACK_TEXT = "此类型暂不绘制页面，仍可选择方向并应用"


def draft_facing(policy: Orientation | None, shape: PageShape) -> Facing | None:
    """Resolve Preview Paper Facing from the radio draft.

    ``None`` policy is the empty radio on an Auto item: same as list Auto.
    """
    if policy is None:
        return resolve_facing(Orientation.AUTO, shape)
    return resolve_facing(policy, shape)


def facing_summary(facing: Facing | None) -> str:
    """Short copy for the draft Facing line under the file name."""
    if facing is Facing.LANDSCAPE:
        return "横向"
    if facing is Facing.PORTRAIT:
        return "纵向"
    return UNFORCED_COPY


def paper_pixel_size(
    facing: Facing | None,
    *,
    max_width: int,
    max_height: int,
) -> tuple[int, int]:
    """Return a paper sheet size that fits inside the canvas bounds.

    Landscape and Portrait use fixed A4 aspect (swapped). PrinterDefault uses a
    square unforced sheet so the UI does not invent a Facing.
    """
    if max_width < 1 or max_height < 1:
        return 1, 1
    if facing is None:
        side = min(max_width, max_height)
        return side, side
    if facing is Facing.PORTRAIT:
        ratio_w, ratio_h = _A4_SHORT, _A4_LONG
    else:
        ratio_w, ratio_h = _A4_LONG, _A4_SHORT
    scale = min(max_width / ratio_w, max_height / ratio_h)
    return max(1, int(ratio_w * scale)), max(1, int(ratio_h * scale))


def fit_inside(content_w: int, content_h: int, box_w: int, box_h: int) -> tuple[int, int]:
    """Scale content to fit inside the box without cropping (one scale mode)."""
    if content_w < 1 or content_h < 1 or box_w < 1 or box_h < 1:
        return 1, 1
    scale = min(box_w / content_w, box_h / content_h)
    return max(1, int(content_w * scale)), max(1, int(content_h * scale))


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

    Chrome (summary, Preview Paper, orientation, actions) is shown before any
    thumbnail work. Raster runs on the next idle turn after the window is mapped.
    Radio changes update the paper sheet and draft summary immediately.
    """

    def __init__(self, master: ctk.CTk, item: PrintItem, on_apply: ApplyHandler) -> None:
        super().__init__(master)
        self.title("预览")
        self.geometry("440x560")
        self.minsize(360, 460)
        self._anchor = item.id
        self._item = item
        self._on_apply = on_apply
        self._photo: ctk.CTkImage | None = None
        self._drawn: Image.Image | None = None
        self._raster_queued = False
        self._raster_done = False
        self._paper_size: tuple[int, int] = (1, 1)
        initial = "" if item.orientation is Orientation.AUTO else item.orientation.value
        self._choice = ctk.StringVar(value=initial)

        self._build_summary(item)
        self._page_slot = ctk.CTkFrame(self, fg_color="transparent")
        self._page_slot.pack(fill="x", padx=16, pady=8)
        self._canvas = ctk.CTkFrame(
            self._page_slot,
            fg_color=_CANVAS_COLOR,
            width=_CANVAS_SIZE[0],
            height=_CANVAS_SIZE[1],
        )
        self._canvas.pack(fill="x")
        self._canvas.pack_propagate(False)
        self._paper = ctk.CTkFrame(self._canvas, fg_color=_PAPER_COLOR, corner_radius=2)
        self._paper.place(relx=0.5, rely=0.5, anchor="center")
        self._paper.pack_propagate(False)
        self._paper_body = ctk.CTkFrame(self._paper, fg_color="transparent")
        self._paper_body.pack(expand=True, fill="both", padx=_CONTENT_PAD, pady=_CONTENT_PAD)
        self._build_choices()
        self._hint = ctk.CTkLabel(self, text="", anchor="w", text_color="gray")
        self._hint.pack(fill="x", padx=16, pady=(4, 0))
        self._build_actions()

        self._choice.trace_add("write", self._on_choice_write)
        self._refresh_paper()

        self.transient(master)
        self.bind("<Map>", self._on_map, add="+")
        self.deiconify()
        self._raise_into_view()
        self.after_idle(self._kick_raster)

    def paper_facing(self) -> Facing | None:
        """Facing currently expressed by Preview Paper (observable for tests)."""
        return draft_facing(self._chosen(), self._item.shape)

    def paper_pixel_size_now(self) -> tuple[int, int]:
        """Current white-sheet pixel size after the last refresh."""
        return self._paper_size

    def draft_summary_text(self) -> str:
        """Visible draft Facing / unforced copy next to the kind label."""
        return str(self._draft_label.cget("text"))

    def _build_summary(self, item: PrintItem) -> None:
        """Show the file name, kind, list mark, and draft Facing line."""
        name = item.path.name or str(item.path)
        kind = _KIND_LABEL.get(item.kind, item.kind.value)
        ctk.CTkLabel(self, text=name, font=ctk.CTkFont(size=16, weight="bold"), anchor="w").pack(
            fill="x", padx=16, pady=(16, 4)
        )
        ctk.CTkLabel(
            self,
            text=f"{kind}  ·  当前 {orientation_label(item)}",
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 2))
        self._draft_label = ctk.CTkLabel(self, text="", anchor="w")
        self._draft_label.pack(fill="x", padx=16, pady=(0, 8))

    def _on_choice_write(self, *_args: object) -> None:
        """Radio draft changed: refresh paper and summary on the next idle turn."""
        if not self.winfo_exists():
            return
        self.after_idle(self._refresh_paper)

    def _refresh_paper(self) -> None:
        """Resize the paper sheet and redraw content for the current draft Facing."""
        if not self.winfo_exists():
            return
        facing = self.paper_facing()
        self._draft_label.configure(text=f"预览  {facing_summary(facing)}")
        max_w = _CANVAS_SIZE[0] - 2 * _PAPER_INSET
        max_h = _CANVAS_SIZE[1] - 2 * _PAPER_INSET
        width, height = paper_pixel_size(facing, max_width=max_w, max_height=max_h)
        self._paper_size = (width, height)
        paper_color = _UNFORCED_PAPER_COLOR if facing is None else _PAPER_COLOR
        self._paper.configure(width=width, height=height, fg_color=paper_color)
        self._fill_paper_body()

    def _fill_paper_body(self) -> None:
        """Put the thumbnail or text fallback inside the paper sheet."""
        if not self._paper_body.winfo_exists():
            return
        for child in self._paper_body.winfo_children():
            child.destroy()
        box_w = max(1, self._paper_size[0] - 2 * _CONTENT_PAD)
        box_h = max(1, self._paper_size[1] - 2 * _CONTENT_PAD)
        drawn = self._drawn
        if drawn is None:
            wrap = max(80, box_w - 8)
            ctk.CTkLabel(
                self._paper_body,
                text=PAGE_FALLBACK_TEXT,
                anchor="center",
                justify="center",
                wraplength=wrap,
            ).pack(expand=True)
            return
        fit_w, fit_h = fit_inside(drawn.width, drawn.height, box_w, box_h)
        self._photo = ctk.CTkImage(light_image=drawn, size=(fit_w, fit_h))
        ctk.CTkLabel(self._paper_body, text="", image=self._photo).pack(expand=True)

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
        """Decode a thumbnail once. Never run this from ``__init__``."""
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
        self._drawn = drawn
        self._fill_paper_body()
        self._raise_into_view()

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

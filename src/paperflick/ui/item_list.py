"""Print Item list widget bound to BatchSnapshot."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from paperflick.core.batch import (
    BatchSnapshot,
    Facing,
    ItemId,
    ItemStatus,
    PrintItem,
    resolve_facing,
)

_STATUS_LABEL = {
    ItemStatus.WAITING: "等待",
    ItemStatus.PRINTING: "打印中",
    ItemStatus.SUCCESS: "成功",
    ItemStatus.FAILED: "失败",
}

_FACING_LABEL = {
    Facing.LANDSCAPE: "横向",
    Facing.PORTRAIT: "纵向",
}

# Okabe–Ito-inspired semantic text colors; Waiting gray tuned per appearance.
_STATUS_COLOR_LIGHT = {
    ItemStatus.WAITING: "#6C6C6C",
    ItemStatus.PRINTING: "#0072B2",
    ItemStatus.SUCCESS: "#009E73",
    ItemStatus.FAILED: "#D55E00",
}
_STATUS_COLOR_DARK = {
    ItemStatus.WAITING: "#B8B8B8",
    ItemStatus.PRINTING: "#56B4E9",
    ItemStatus.SUCCESS: "#2ECC9A",
    ItemStatus.FAILED: "#FF7A1A",
}


def orientation_label(item: PrintItem) -> str:
    """Return the orientation cell text for one Print Item.

    Auto shows the inferred facing alone, with no policy prefix. A forced
    policy uses the same facing words. Printer default names no facing.
    """
    facing = resolve_facing(item.orientation, item.shape)
    if facing is None:
        return "打印机"
    return _FACING_LABEL[facing]


def identity_text(item: PrintItem) -> str:
    """Return the uncolored name and facing segment for a row."""
    name = item.path.name or str(item.path)
    return f"{name}  {orientation_label(item)}"


def status_text(item: PrintItem) -> str:
    """Return the colored status segment, including failure reason when present."""
    status = _STATUS_LABEL.get(item.status, item.status.value)
    if item.status is ItemStatus.FAILED and item.failure_reason:
        return f"[{status}]  {item.failure_reason}"
    return f"[{status}]"


def status_text_color(status: ItemStatus, appearance_mode: str = "light") -> str:
    """Map ItemStatus to a colorblind-friendly text color for the given mode.

    ``appearance_mode`` accepts CustomTkinter values such as ``Light`` / ``Dark``
    (case-insensitive). Unknown values fall back to the light palette.
    """
    palette = (
        _STATUS_COLOR_DARK if appearance_mode.strip().lower() == "dark" else _STATUS_COLOR_LIGHT
    )
    return palette[status]


class ItemListPanel(ctk.CTkFrame):
    """Scrollable Print Item rows. A row click previews; 移除 drops that row."""

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkFrame,
        *,
        on_preview: Callable[[ItemId], None] | None = None,
        on_remove: Callable[[ItemId], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)  # type: ignore[arg-type]
        self._on_preview = on_preview
        self._on_remove = on_remove

        self._scroll = ctk.CTkScrollableFrame(self, height=180)
        self._scroll.pack(fill="both", expand=True)

        self._empty = ctk.CTkLabel(self._scroll, text="尚未添加打印项", anchor="w")
        self._empty.pack(fill="x", padx=4, pady=8)

    def bind_snapshot(self, snapshot: BatchSnapshot) -> None:
        """Rebuild rows from a BatchSnapshot."""
        for child in self._scroll.winfo_children():
            child.destroy()

        if not snapshot.items:
            self._empty = ctk.CTkLabel(self._scroll, text="尚未添加打印项", anchor="w")
            self._empty.pack(fill="x", padx=4, pady=8)
            return

        appearance = ctk.get_appearance_mode()
        for item in snapshot.items:
            self._build_row(item, appearance)

    def _build_row(self, item: PrintItem, appearance: str) -> None:
        """One row: identity and status open preview; 移除 does not."""
        row = ctk.CTkFrame(self._scroll, fg_color="transparent")
        row.pack(fill="x", pady=2)
        remove = ctk.CTkButton(
            row,
            text="移除",
            width=64,
            height=28,
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray85", "gray25"),
            command=lambda item_id=item.id: self._emit_remove(item_id),
        )
        remove.pack(side="right", padx=(4, 0))
        identity = ctk.CTkLabel(row, text=identity_text(item), anchor="w")
        identity.pack(side="left", padx=(4, 0))
        status = ctk.CTkLabel(
            row,
            text=status_text(item),
            anchor="w",
            text_color=status_text_color(item.status, appearance),
        )
        status.pack(side="left", fill="x", expand=True, padx=4)
        self._bind_preview(row, item.id)
        self._bind_preview(identity, item.id)
        self._bind_preview(status, item.id)

    def _bind_preview(self, widget: ctk.CTkBaseClass, item_id: ItemId) -> None:
        """Clicks on the row body open preview. The 移除 button is not bound."""
        widget.bind(
            "<Button-1>",
            lambda _event, item_id=item_id: self._emit_preview(item_id),
        )

    def _emit_preview(self, item_id: ItemId) -> None:
        """Forward a row click when a preview handler is set."""
        if self._on_preview is not None:
            self._on_preview(item_id)

    def _emit_remove(self, item_id: ItemId) -> None:
        """Forward 移除 when a remove handler is set."""
        if self._on_remove is not None:
            self._on_remove(item_id)

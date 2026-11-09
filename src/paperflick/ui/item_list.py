"""Print Item list widget bound to BatchSnapshot."""

from __future__ import annotations

from collections.abc import Collection

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
    """Scrollable rows for Print Items with multi-select for Remove."""

    def __init__(self, master: ctk.CTk | ctk.CTkFrame, **kwargs: object) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)  # type: ignore[arg-type]
        self._selected: set[ItemId] = set()
        self._row_vars: dict[ItemId, ctk.BooleanVar] = {}

        self._scroll = ctk.CTkScrollableFrame(self, height=180)
        self._scroll.pack(fill="both", expand=True)

        self._empty = ctk.CTkLabel(self._scroll, text="尚未添加打印项", anchor="w")
        self._empty.pack(fill="x", padx=4, pady=8)

    def selected_ids(self) -> list[ItemId]:
        """Return currently checked item ids."""
        return [item_id for item_id, var in self._row_vars.items() if var.get()]

    def check_only(self, ids: Collection[ItemId]) -> None:
        """Check exactly ``ids`` and clear every other row."""
        wanted = set(ids)
        for item_id, var in self._row_vars.items():
            var.set(item_id in wanted)

    def bind_snapshot(self, snapshot: BatchSnapshot) -> None:
        """Rebuild rows from a BatchSnapshot."""
        previous = {item_id for item_id, var in self._row_vars.items() if var.get()}
        for child in self._scroll.winfo_children():
            child.destroy()
        self._row_vars.clear()
        self._selected = set()

        if not snapshot.items:
            self._empty = ctk.CTkLabel(self._scroll, text="尚未添加打印项", anchor="w")
            self._empty.pack(fill="x", padx=4, pady=8)
            return

        appearance = ctk.get_appearance_mode()
        for item in snapshot.items:
            row = ctk.CTkFrame(self._scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            checked = item.id in previous
            var = ctk.BooleanVar(value=checked)
            self._row_vars[item.id] = var
            ctk.CTkCheckBox(row, text="", variable=var, width=24).pack(side="left")
            ctk.CTkLabel(row, text=identity_text(item), anchor="w").pack(side="left", padx=(4, 0))
            ctk.CTkLabel(
                row,
                text=status_text(item),
                anchor="w",
                text_color=status_text_color(item.status, appearance),
            ).pack(side="left", fill="x", expand=True, padx=4)

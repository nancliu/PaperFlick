"""Print Item list widget bound to BatchSnapshot."""

from __future__ import annotations

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


def orientation_label(item: PrintItem) -> str:
    """Return the orientation cell text for one Print Item.

    Auto shows the inferred facing alone, with no policy prefix. A forced
    policy uses the same facing words. Printer default names no facing.
    """
    facing = resolve_facing(item.orientation, item.shape)
    if facing is None:
        return "打印机"
    return _FACING_LABEL[facing]


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

        for item in snapshot.items:
            row = ctk.CTkFrame(self._scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            checked = item.id in previous
            var = ctk.BooleanVar(value=checked)
            self._row_vars[item.id] = var
            ctk.CTkCheckBox(row, text="", variable=var, width=24).pack(side="left")
            name = item.path.name or str(item.path)
            status = _STATUS_LABEL.get(item.status, item.status.value)
            label = orientation_label(item)
            ctk.CTkLabel(row, text=f"{name}  {label}  [{status}]", anchor="w").pack(
                side="left", fill="x", expand=True, padx=4
            )

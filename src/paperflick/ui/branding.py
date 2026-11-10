"""Resolve bundled brand assets and apply window / title chrome."""

from __future__ import annotations

import sys
from pathlib import Path

import customtkinter as ctk
from PIL import Image

_ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"


def asset_path(name: str) -> Path:
    """Return the path to a packaged asset file.

    Works for editable installs, wheels, and Nuitka standalone (assets live
    next to the ``paperflick`` package tree inside the dist folder).
    """
    candidate = _ASSET_DIR / name
    if candidate.is_file():
        return candidate
    if getattr(sys, "frozen", False):
        frozen_root = Path(sys.executable).resolve().parent
        alt = frozen_root / "paperflick" / "assets" / name
        if alt.is_file():
            return alt
    raise FileNotFoundError(name)


def apply_window_icon(window: ctk.CTk | ctk.CTkToplevel) -> None:
    """Set the window/taskbar icon from the bundled ``app.ico`` when present."""
    try:
        icon = asset_path("app.ico")
    except FileNotFoundError:
        return
    try:
        window.iconbitmap(default=str(icon))
    except Exception:
        try:
            window.iconbitmap(str(icon))
        except Exception:
            return


def title_logo_image() -> ctk.CTkImage | None:
    """Return a compact status-bar lockup (light/dark) beside the version badge."""
    return _logo_image("logo-light.png", "logo-dark.png", size_height=22)


def about_logo_image() -> ctk.CTkImage | None:
    """Return a larger light/dark logo for the About dialog, or None."""
    return _logo_image("logo-about-light.png", "logo-about-dark.png", size_height=56)


def _logo_image(light_name: str, dark_name: str, *, size_height: int) -> ctk.CTkImage | None:
    """Load a CTkImage pair scaled to ``size_height``.

    CustomTkinter requires the two source images to share the same pixel size,
    so both frames are normalized before ``CTkImage`` is built.
    """
    try:
        light = Image.open(asset_path(light_name)).convert("RGBA")
        dark = Image.open(asset_path(dark_name)).convert("RGBA")
    except (FileNotFoundError, OSError):
        return None
    max_h = max(max(light.height, dark.height), 1)
    width = max(1, round(max(light.width, dark.width) * (size_height / max_h)))
    size = (width, size_height)
    light = _fit_rgba(light, size)
    dark = _fit_rgba(dark, size)
    return ctk.CTkImage(light_image=light, dark_image=dark, size=size)


def _fit_rgba(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Return ``image`` scaled into ``size`` on a transparent canvas."""
    fitted = image.copy()
    fitted.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    offset = ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2)
    canvas.paste(fitted, offset, fitted)
    return canvas

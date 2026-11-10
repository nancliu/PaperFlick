"""Convert the PaperFlick PNG into a multi-size ICO for Nuitka/Inno."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "icons" / "PaperFlick（纸闪）软件图标设计.png"
OUT = ROOT / "icons" / "PaperFlick.ico"
SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main() -> None:
    """Write icons/PaperFlick.ico from the design PNG."""
    image = Image.open(SRC).convert("RGBA")
    frames = [image.resize(size, Image.Resampling.LANCZOS) for size in SIZES]
    frames[-1].save(OUT, format="ICO", sizes=[frame.size for frame in frames])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

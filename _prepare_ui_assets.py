"""Resize README logos into compact UI assets under src/paperflick/assets."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "src" / "paperflick" / "assets"
ICONS = ROOT / "icons"


def _fit_pair(light_src: Path, dark_src: Path, light_dest: Path, dark_dest: Path, height: int) -> None:
    """Write light/dark PNGs with identical pixel size for CTkImage."""
    light = Image.open(light_src).convert("RGBA")
    dark = Image.open(dark_src).convert("RGBA")
    width = max(
        1,
        round(max(light.width, dark.width) * (height / max(max(light.height, dark.height), 1))),
    )
    size = (width, height)

    def fit(image: Image.Image) -> Image.Image:
        fitted = image.copy()
        fitted.thumbnail(size, Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", size, (0, 0, 0, 0))
        canvas.paste(
            fitted,
            ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2),
            fitted,
        )
        return canvas

    fit(light).save(light_dest, format="PNG")
    fit(dark).save(dark_dest, format="PNG")
    print(f"wrote {light_dest.name}/{dark_dest.name} ({width}x{height})")


def main() -> None:
    """Refresh ico plus title/about logo pairs."""
    ASSETS.mkdir(parents=True, exist_ok=True)
    ico_src = ICONS / "PaperFlick.ico"
    if ico_src.is_file():
        (ASSETS / "app.ico").write_bytes(ico_src.read_bytes())
        print(f"wrote {ASSETS / 'app.ico'}")
    _fit_pair(
        ICONS / "readme-logo-light.png",
        ICONS / "readme-logo-dark.png",
        ASSETS / "logo-light.png",
        ASSETS / "logo-dark.png",
        36,
    )
    _fit_pair(
        ICONS / "readme-logo-light.png",
        ICONS / "readme-logo-dark.png",
        ASSETS / "logo-about-light.png",
        ASSETS / "logo-about-dark.png",
        72,
    )


if __name__ == "__main__":
    main()

"""Generate Home Assistant local brand assets for the RCCL integration."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BRAND_DIR = ROOT / "custom_components" / "rccl" / "brand"
NAVY = "#003b5c"
DEEP_NAVY = "#002f49"
GOLD = "#c9a23f"
WHITE = "#ffffff"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


def draw_mark(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    width = right - left
    height = bottom - top
    cx = left + width // 2
    crown_top = top + int(height * 0.17)
    crown_base = top + int(height * 0.38)

    crown = [
        (left + int(width * 0.19), crown_base),
        (left + int(width * 0.28), crown_top + int(height * 0.10)),
        (left + int(width * 0.39), crown_base - int(height * 0.08)),
        (cx, crown_top),
        (left + int(width * 0.61), crown_base - int(height * 0.08)),
        (left + int(width * 0.72), crown_top + int(height * 0.10)),
        (left + int(width * 0.81), crown_base),
    ]
    draw.polygon(crown, fill=GOLD)
    draw.rounded_rectangle(
        (left + int(width * 0.23), crown_base, left + int(width * 0.77), crown_base + int(height * 0.07)),
        radius=max(2, width // 40),
        fill=GOLD,
    )

    anchor_top = top + int(height * 0.46)
    anchor_bottom = top + int(height * 0.80)
    line_width = max(5, width // 18)
    draw.line((cx, anchor_top, cx, anchor_bottom), fill=WHITE, width=line_width)
    draw.ellipse(
        (
            cx - int(width * 0.11),
            anchor_top - int(height * 0.09),
            cx + int(width * 0.11),
            anchor_top + int(height * 0.13),
        ),
        outline=WHITE,
        width=line_width,
    )
    draw.arc(
        (
            left + int(width * 0.18),
            top + int(height * 0.55),
            left + int(width * 0.82),
            bottom - int(height * 0.03),
        ),
        start=20,
        end=160,
        fill=WHITE,
        width=line_width,
    )
    draw.line(
        (
            left + int(width * 0.26),
            top + int(height * 0.71),
            left + int(width * 0.17),
            top + int(height * 0.66),
        ),
        fill=WHITE,
        width=line_width,
    )
    draw.line(
        (
            left + int(width * 0.74),
            top + int(height * 0.71),
            left + int(width * 0.83),
            top + int(height * 0.66),
        ),
        fill=WHITE,
        width=line_width,
    )


def create_icon() -> Image.Image:
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((16, 16, 240, 240), fill=NAVY)
    draw.ellipse((26, 26, 230, 230), outline=GOLD, width=6)
    draw_mark(draw, (48, 40, 208, 214))
    return image


def create_logo() -> Image.Image:
    image = Image.new("RGBA", (800, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((18, 34, 210, 226), radius=28, fill=DEEP_NAVY)
    draw_mark(draw, (48, 50, 180, 214))
    draw.text((246, 68), "ROYAL CARIBBEAN", fill=NAVY, font=font(FONT_BOLD, 52))
    draw.text((250, 132), "Home Assistant", fill=GOLD, font=font(FONT_REGULAR, 30))
    return image


def main() -> None:
    BRAND_DIR.mkdir(parents=True, exist_ok=True)
    create_icon().save(BRAND_DIR / "icon.png")
    create_logo().save(BRAND_DIR / "logo.png")


if __name__ == "__main__":
    main()

"""Generate Home Assistant local brand assets from the Royal Caribbean SVG."""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BRAND_DIR = ROOT / "custom_components" / "rccl" / "brand"
SOURCE_URL = "https://www.royalcaribbean.com/myaccount/assets/images/royal/logo.svg"
SOURCE_SVG = BRAND_DIR / "logo.svg"
NAVY = "#003b5c"
GOLD = "#c9a23f"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


def render_svg(size: int) -> Image.Image:
    """Render the official SVG path without external SVG dependencies."""

    paths = extract_logo_paths()
    scale = size / 31
    width = round(28 * scale)
    height = round(31 * scale)
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for points in paths:
        scaled = [(round(x * scale), round(y * scale)) for x, y in points]
        draw.polygon(scaled, fill="#2B3F89")
    return image


def extract_logo_paths() -> list[list[tuple[float, float]]]:
    if not SOURCE_SVG.is_file():
        raise FileNotFoundError(f"Missing {SOURCE_SVG}. Source URL: {SOURCE_URL}")

    root = ElementTree.parse(SOURCE_SVG).getroot()
    path_data = None
    for element in root.iter():
        if element.tag.endswith("path") and element.attrib.get("d"):
            path_data = element.attrib["d"]
            break
    if not path_data:
        raise RuntimeError(f"No path data found in {SOURCE_SVG}")

    return parse_svg_path(path_data, translate=(-53, -31))


def parse_svg_path(
    path_data: str,
    translate: tuple[float, float],
) -> list[list[tuple[float, float]]]:
    tokens = re.findall(r"[MCZ]|-?\d+(?:\.\d+)?", path_data)
    paths: list[list[tuple[float, float]]] = []
    current: tuple[float, float] | None = None
    active: list[tuple[float, float]] = []
    command = ""
    index = 0

    while index < len(tokens):
        token = tokens[index]
        if token in {"M", "C", "Z"}:
            command = token
            index += 1
        if command == "M":
            if active:
                paths.append(active)
            x, y = offset_point(float(tokens[index]), float(tokens[index + 1]), translate)
            active = [(x, y)]
            current = (x, y)
            index += 2
        elif command == "C":
            if current is None:
                raise RuntimeError("SVG path curve appeared before a move command")
            x1, y1 = offset_point(float(tokens[index]), float(tokens[index + 1]), translate)
            x2, y2 = offset_point(float(tokens[index + 2]), float(tokens[index + 3]), translate)
            x3, y3 = offset_point(float(tokens[index + 4]), float(tokens[index + 5]), translate)
            active.extend(sample_cubic(current, (x1, y1), (x2, y2), (x3, y3)))
            current = (x3, y3)
            index += 6
        elif command == "Z":
            if active:
                paths.append(active)
                active = []
            current = None
            command = ""
        else:
            raise RuntimeError(f"Unsupported SVG path command near {token!r}")

    if active:
        paths.append(active)
    return paths


def offset_point(
    x: float,
    y: float,
    translate: tuple[float, float],
) -> tuple[float, float]:
    return x + translate[0], y + translate[1]


def sample_cubic(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    steps: int = 16,
) -> list[tuple[float, float]]:
    points = []
    for step in range(1, steps + 1):
        t = step / steps
        mt = 1 - t
        x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
        y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
        points.append((x, y))
    return points


def fit_on_canvas(image: Image.Image, size: tuple[int, int], padding: int) -> Image.Image:
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    max_width = size[0] - padding * 2
    max_height = size[1] - padding * 2
    fitted = image.copy()
    fitted.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    left = (size[0] - fitted.width) // 2
    top = (size[1] - fitted.height) // 2
    canvas.alpha_composite(fitted, (left, top))
    return canvas


def create_icon() -> Image.Image:
    return fit_on_canvas(render_svg(768), (256, 256), 22)


def create_logo() -> Image.Image:
    image = Image.new("RGBA", (800, 256), (0, 0, 0, 0))
    mark = fit_on_canvas(render_svg(768), (164, 180), 0)
    image.alpha_composite(mark, (54, 38))
    draw = ImageDraw.Draw(image)
    draw.text((258, 70), "ROYAL CARIBBEAN", fill=NAVY, font=font(FONT_BOLD, 54))
    draw.line((260, 142, 690, 142), fill=GOLD, width=5)
    return image


def main() -> None:
    BRAND_DIR.mkdir(parents=True, exist_ok=True)
    create_icon().save(BRAND_DIR / "icon.png")
    create_logo().save(BRAND_DIR / "logo.png")


if __name__ == "__main__":
    main()

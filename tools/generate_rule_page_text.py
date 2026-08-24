#!/usr/bin/env python3
"""Render translated body text into existing transparent rule-page sprites."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> str:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        current: list[str] = []
        for word in paragraph.split():
            candidate = " ".join((*current, word))
            box = draw.textbbox((0, 0), candidate, font=font)
            if current and box[2] - box[0] > width:
                lines.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            lines.append(" ".join(current))
        elif paragraph == "":
            lines.append("")
    return "\n".join(lines)


def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: Path,
    width: int,
    height: int,
    max_font_size: int,
) -> tuple[str, ImageFont.FreeTypeFont]:
    for size in range(max_font_size, 6, -1):
        font = ImageFont.truetype(str(font_path), size)
        wrapped = wrap_text(draw, text, font, width)
        box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=0)
        if box[2] - box[0] <= width and box[3] - box[1] <= height:
            return wrapped, font
    raise ValueError("Rule-page text does not fit at the minimum font size")


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=project_root / "assets" / "rule_page_text.json")
    parser.add_argument("--font", type=Path, default=project_root / "assets" / "source" / "BubbleSans-Regular.otf")
    parser.add_argument("--images", type=Path, default=project_root / "assets" / "images")
    args = parser.parse_args()

    pages = json.loads(args.config.read_text(encoding="utf-8"))
    for name, settings in pages.items():
        path = args.images / f"{name}.png"
        with Image.open(path) as source:
            image = source.convert("RGBA")

        rendered_sizes: list[int] = []
        for region in settings["regions"]:
            clear_box = tuple(region.get("clear_box", region["box"]))
            image.paste((0, 0, 0, 0), clear_box)
            left, top, right, bottom = region["box"]
            width = right - left
            height = bottom - top
            layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(layer)
            wrapped, font = fit_text(
                draw,
                region["text"],
                args.font,
                width,
                height,
                region.get("max_font_size", 13),
            )
            text_box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=0)
            y = (height - (text_box[3] - text_box[1])) / 2 - text_box[1]
            draw.multiline_text((0, y), wrapped, font=font, fill=(255, 255, 255, 255), spacing=0)
            angle = region.get("angle", 0)
            if angle:
                layer = layer.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False)
            image.alpha_composite(layer, (left, top))
            rendered_sizes.append(font.size)
        image.save(path, optimize=True)
        print(f"Generated {path.name} at {rendered_sizes}px")


if __name__ == "__main__":
    main()

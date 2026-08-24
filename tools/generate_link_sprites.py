#!/usr/bin/env python3
"""Generate Russian rulebook table-of-contents link sprites."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


CANVAS_SIZE = (136, 43)
TEXT_BOX = (10, 1, 126, 42)


def fit_font(draw: ImageDraw.ImageDraw, text: str, font_path: Path) -> ImageFont.FreeTypeFont:
    max_width = TEXT_BOX[2] - TEXT_BOX[0] - 2
    max_height = TEXT_BOX[3] - TEXT_BOX[1] - 2
    for size in range(12, 6, -1):
        font = ImageFont.truetype(str(font_path), size)
        box = draw.multiline_textbbox((0, 0), text, font=font, spacing=0, align="center")
        if box[2] - box[0] <= max_width and box[3] - box[1] <= max_height:
            return font
    return ImageFont.truetype(str(font_path), 7)


def render(source: Path, destination: Path, text: str | None, font_path: Path) -> None:
    if text is None:
        shutil.copyfile(source, destination)
        return

    with Image.open(source) as input_image:
        image = input_image.convert("RGBA")
    if image.size != CANVAS_SIZE:
        raise ValueError(f"Unexpected source size for {source}: {image.size}")

    image.paste((0, 0, 0, 0), TEXT_BOX)
    draw = ImageDraw.Draw(image)
    font = fit_font(draw, text, font_path)
    box = draw.multiline_textbbox((0, 0), text, font=font, spacing=0, align="center")
    width = box[2] - box[0]
    height = box[3] - box[1]
    position = ((CANVAS_SIZE[0] - width) / 2 - box[0], (CANVAS_SIZE[1] - height) / 2 - box[1])
    draw.multiline_text(position, text, font=font, fill=(245, 245, 245, 255), spacing=0, align="center")
    image.save(destination, optimize=True)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, default=project_root / "assets" / "link_labels.json")
    parser.add_argument("--source", type=Path, default=project_root / "assets" / "source" / "link_sprites")
    parser.add_argument("--font", type=Path, default=project_root / "assets" / "source" / "BubbleSans-Regular.otf")
    parser.add_argument("--output", type=Path, default=project_root / "assets" / "images")
    args = parser.parse_args()

    labels = json.loads(args.labels.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    generated = 0
    for key, text in labels.items():
        for side in ("l", "r"):
            name = f"{key}_{side}.png"
            source = args.source / name
            if not source.exists():
                raise FileNotFoundError(source)
            render(source, args.output / name, text, args.font)
            generated += 1
    print(f"Generated {generated} link sprites in {args.output}")


if __name__ == "__main__":
    main()

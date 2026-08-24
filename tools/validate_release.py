#!/usr/bin/env python3
"""Validate translation and image files included in a release."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=project_root)
    args = parser.parse_args()

    errors: list[str] = []
    mapping: dict[str, str] = {}
    mapping_path = args.project / "image_mapping.txt"
    for line_number, raw_line in enumerate(mapping_path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw_line or raw_line.startswith("#"):
            continue
        if "=" not in raw_line:
            errors.append(f"Malformed image mapping line {line_number}")
            continue
        source, file_name = raw_line.split("=", 1)
        if source in mapping:
            errors.append(f"Duplicate image mapping key: {source}")
        mapping[source] = file_name

    image_directory = args.project / "assets" / "images"
    image_files = {path.name: path for path in image_directory.glob("*.png")}
    for source, file_name in mapping.items():
        if file_name not in image_files:
            errors.append(f"Missing mapped image: {source} -> {file_name}")

    unreferenced = sorted(set(image_files) - set(mapping.values()))
    if unreferenced:
        errors.append("Unreferenced images: " + ", ".join(unreferenced))

    source_link_directory = args.project / "assets" / "source" / "link_sprites"
    source_link_names = {path.stem for path in source_link_directory.glob("link_*.png")}
    missing_link_mappings = sorted(source_link_names - set(mapping))
    if missing_link_mappings:
        errors.append("Missing source link mappings: " + ", ".join(missing_link_mappings))

    for file_name, path in sorted(image_files.items()):
        with Image.open(path) as image:
            expected_size = (136, 43) if file_name.startswith("link_") else (320, 320)
            if image.size != expected_size:
                errors.append(f"Unexpected size for {file_name}: {image.size}, expected {expected_size}")
            if image.mode not in ("RGBA", "LA", "P") and "transparency" not in image.info:
                errors.append(f"Image has no alpha/transparency channel: {file_name} ({image.mode})")

    translations: dict[str, int] = {}
    translation_path = args.project / "translation.txt"
    for line_number, raw_line in enumerate(translation_path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw_line or raw_line.startswith("#"):
            continue
        if "=" not in raw_line:
            errors.append(f"Malformed translation line {line_number}")
            continue
        source = raw_line.split("=", 1)[0]
        if source in translations:
            errors.append(f"Duplicate translation key on lines {translations[source]} and {line_number}: {source}")
        translations[source] = line_number

    required_files = (
        "alagard-unicode-tmp",
        "CHANGELOG.md",
        "LICENSE",
        "NOTICE",
        "README.md",
        "RussianTranslationMod.csproj",
        "THIRD_PARTY_NOTICES.md",
        "build.ps1",
    )
    for file_name in required_files:
        if not (args.project / file_name).is_file():
            errors.append(f"Required release source file is missing: {file_name}")

    license_path = args.project / "LICENSE"
    if license_path.is_file():
        license_text = license_path.read_text(encoding="utf-8-sig")
        if "Apache License" not in license_text or "END OF TERMS AND CONDITIONS" not in license_text:
            errors.append("LICENSE does not contain the complete Apache License 2.0 text")

    license_files = (
        "BepInEx-MIT.txt",
        "CC-BY-3.0.txt",
        "OFL-1.1.txt",
    )
    for file_name in license_files:
        if not (args.project / "LICENSES" / file_name).is_file():
            errors.append(f"Required third-party license is missing: LICENSES/{file_name}")

    page_config_path = args.project / "assets" / "rule_page_text.json"
    if not page_config_path.is_file():
        errors.append("Missing assets/rule_page_text.json")
    else:
        page_config = json.loads(page_config_path.read_text(encoding="utf-8"))
        for page_name, settings in page_config.items():
            if f"{page_name}.png" not in image_files:
                errors.append(f"Configured rule page has no output image: {page_name}.png")
            regions = settings.get("regions", [])
            if not regions:
                errors.append(f"Configured rule page has no text regions: {page_name}")
            for index, region in enumerate(regions):
                box = region.get("box")
                if not isinstance(box, list) or len(box) != 4:
                    errors.append(f"Invalid text box for {page_name} region {index}")
                    continue
                left, top, right, bottom = box
                if not (0 <= left < right <= 320 and 0 <= top < bottom <= 320):
                    errors.append(f"Out-of-bounds text box for {page_name} region {index}: {box}")
                if not region.get("text"):
                    errors.append(f"Empty text for {page_name} region {index}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)

    print(
        f"Release data valid: {len(translations)} translations, "
        f"{len(mapping)} mapped images, {len(image_files)} PNG files."
    )


if __name__ == "__main__":
    main()

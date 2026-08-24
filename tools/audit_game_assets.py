#!/usr/bin/env python3
"""Audit King of the Bridge localization bundles and prepared artwork."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import UnityPy
from PIL import Image
from psd_tools import PSDImage


def iter_named_objects(bundle_path: Path):
    environment = UnityPy.load(str(bundle_path))
    for obj in environment.objects:
        data = obj.read()
        name = getattr(data, "m_Name", getattr(data, "name", ""))
        yield obj, obj.type.name, name, data


def audit_bundles(game_path: Path, include_typetrees: bool = False) -> dict:
    bundle_dir = game_path / "King of the Bridge_Data" / "StreamingAssets" / "aa" / "StandaloneWindows64"
    result: dict[str, list[dict[str, str]]] = {}
    patterns = (
        "localization-string-tables-*.bundle",
        "localization-asset-tables-*.bundle",
        "localization-assets-*.bundle",
        "localization-locales_*.bundle",
    )
    for pattern in patterns:
        for bundle in sorted(bundle_dir.glob(pattern)):
            objects = []
            for obj, object_type, name, _ in iter_named_objects(bundle):
                entry = {"type": object_type, "name": name}
                if include_typetrees and object_type == "MonoBehaviour":
                    try:
                        entry["typetree"] = obj.read_typetree()
                    except Exception as exc:  # UnityPy cannot decode every custom script.
                        entry["typetree_error"] = str(exc)
                elif include_typetrees and object_type == "Texture2D":
                    try:
                        tree = obj.read_typetree()
                        settings = tree.get("m_TextureSettings", {})
                        entry["texture_settings"] = {
                            "width": tree.get("m_Width"),
                            "height": tree.get("m_Height"),
                            "filter_mode": settings.get("m_FilterMode"),
                            "aniso": settings.get("m_Aniso"),
                            "mip_bias": settings.get("m_MipBias"),
                            "wrap_u": settings.get("m_WrapU"),
                            "wrap_v": settings.get("m_WrapV"),
                        }
                    except Exception as exc:
                        entry["texture_settings_error"] = str(exc)
                objects.append(entry)
            result[bundle.name] = objects
    return result


def extract_localized_images(game_path: Path, output_path: Path) -> None:
    bundle_dir = game_path / "King of the Bridge_Data" / "StreamingAssets" / "aa" / "StandaloneWindows64"
    for bundle in sorted(bundle_dir.glob("localization-assets-*.bundle")):
        locale_dir = output_path / bundle.stem
        locale_dir.mkdir(parents=True, exist_ok=True)
        for _, object_type, name, data in iter_named_objects(bundle):
            if object_type != "Texture2D":
                continue
            data.image.save(locale_dir / f"{name}.png")


def audit_serialized_sprites(game_path: Path, output_path: Path | None = None) -> list[dict]:
    data_path = game_path / "King of the Bridge_Data"
    asset_files = [data_path / "resources.assets"]
    asset_files.extend(sorted(data_path.glob("sharedassets*.assets")))
    asset_files.extend(sorted(data_path.glob("level*")))
    records = []
    seen = set()
    for asset_file in asset_files:
        environment = UnityPy.load(str(asset_file))
        for obj in environment.objects:
            if obj.type.name != "Sprite":
                continue
            data = obj.read()
            name = getattr(data, "m_Name", getattr(data, "name", ""))
            key = (name, obj.path_id)
            if key in seen:
                continue
            seen.add(key)
            record = {"source": asset_file.name, "name": name, "path_id": obj.path_id}
            try:
                image = data.image
                record.update({"width": image.width, "height": image.height})
                if output_path:
                    output_path.mkdir(parents=True, exist_ok=True)
                    safe_name = "".join(character if character.isalnum() or character in "-_." else "_" for character in name)
                    image.save(output_path / f"{safe_name}__{obj.path_id}.png")
            except Exception as exc:
                record["image_error"] = str(exc)
            records.append(record)
    return records


def audit_artwork(artwork_path: Path) -> dict:
    png_files = sorted(artwork_path.rglob("*.png"))
    psd_files = sorted(artwork_path.rglob("*.psd"))
    dimensions = Counter()
    pngs = []
    for path in png_files:
        with Image.open(path) as image:
            dimensions[f"{image.width}x{image.height}"] += 1
            pngs.append(
                {
                    "path": str(path.relative_to(artwork_path)),
                    "width": image.width,
                    "height": image.height,
                    "mode": image.mode,
                }
            )

    psds = []
    for path in psd_files:
        document = PSDImage.open(path)
        psds.append(
            {
                "path": str(path.relative_to(artwork_path)),
                "width": document.width,
                "height": document.height,
                "layers": [
                    {
                        "name": layer.name,
                        "kind": layer.kind,
                        "visible": layer.visible,
                    }
                    for layer in document
                ],
            }
        )

    return {
        "png_count": len(pngs),
        "psd_count": len(psds),
        "dimensions": dict(sorted(dimensions.items())),
        "pngs": pngs,
        "psds": psds,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--artwork", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--include-typetrees", action="store_true")
    parser.add_argument("--extract-assets", type=Path)
    parser.add_argument("--audit-game-sprites", action="store_true")
    parser.add_argument("--extract-game-sprites", type=Path)
    args = parser.parse_args()

    report = {"bundles": audit_bundles(args.game, args.include_typetrees)}
    if args.artwork:
        report["artwork"] = audit_artwork(args.artwork)
    if args.extract_assets:
        extract_localized_images(args.game, args.extract_assets)
    if args.audit_game_sprites or args.extract_game_sprites:
        report["game_sprites"] = audit_serialized_sprites(args.game, args.extract_game_sprites)

    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()

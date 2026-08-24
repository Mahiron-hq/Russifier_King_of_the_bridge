#!/usr/bin/env python3
"""List render-related objects in serialized Unity scenes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import UnityPy


RENDER_TYPES = {"SpriteMask", "SpriteRenderer", "Animator", "CanvasRenderer"}


def safe_read(pointer):
    try:
        return pointer.read()
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    data_path = args.game / "King of the Bridge_Data"
    records = []
    for scene_path in sorted(data_path.glob("level*")):
        environment = UnityPy.load(str(scene_path))
        for obj in environment.objects:
            if obj.type.name not in RENDER_TYPES:
                continue
            data = obj.read()
            game_object = safe_read(data.m_GameObject)
            game_object_name = getattr(game_object, "m_Name", getattr(game_object, "name", ""))
            sprite_name = ""
            if obj.type.name in {"SpriteMask", "SpriteRenderer"}:
                sprite = safe_read(data.m_Sprite)
                sprite_name = getattr(sprite, "m_Name", getattr(sprite, "name", ""))
            records.append(
                {
                    "scene": scene_path.name,
                    "type": obj.type.name,
                    "game_object": game_object_name,
                    "sprite": sprite_name,
                    "path_id": obj.path_id,
                    "enabled": getattr(data, "m_Enabled", None),
                    "sorting_layer": getattr(data, "m_SortingLayer", None),
                    "sorting_order": getattr(data, "m_SortingOrder", None),
                    "mask_interaction": getattr(data, "m_MaskInteraction", None),
                }
            )

    output = json.dumps(records, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()

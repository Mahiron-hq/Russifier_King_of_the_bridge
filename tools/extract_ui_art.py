"""Takes the installer's header and logo from the game, so no game art has to live in the repository.

Usage: extract_ui_art.py <game_dir> <out_dir>
"""
import os
import sys

import UnityPy

SHARED = os.path.join("King of the Bridge_Data", "sharedassets0.assets")
# The top of the title-screen banner: sun, castle and hilltop; the dark hill blends into the window.
HEADER_CROP = (0, 10, 400, 100)
HEADER_SCALE = 2


def main(game, out):
    textures = {o.read().m_Name: o.read() for o in UnityPy.load(os.path.join(game, SHARED)).objects
                if o.type.name == "Texture2D"}
    os.makedirs(out, exist_ok=True)
    header = textures["banner"].image.convert("RGBA").crop(HEADER_CROP)
    header = header.resize((header.width * HEADER_SCALE, header.height * HEADER_SCALE), 0)
    header.save(os.path.join(out, "header.png"))
    textures["Logo32"].image.convert("RGBA").save(os.path.join(out, "logo.png"))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])

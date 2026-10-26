"""Replace the game's static `alagard SDF` font asset with the Cyrillic `alagard-unicode-TMP` one.

The replacement happens in place, so every text component that references `alagard SDF` keeps working.
"""
import copy

import UnityPy

ELLIPSIS = 0x2026
PERIOD = 0x2E
MATERIAL_FLOATS = ("_GradientScale", "_TextureWidth", "_TextureHeight",
                   "_ScaleRatioA", "_ScaleRatioB", "_ScaleRatioC")
FONT_FIELDS = ("m_FaceInfo", "m_GlyphTable", "m_CharacterTable", "m_UsedGlyphRects", "m_FreeGlyphRects",
               "m_AtlasWidth", "m_AtlasHeight", "m_AtlasPadding", "m_AtlasRenderMode",
               "m_CreationSettings", "m_FontFeatureTable", "m_KerningTable")


def load_source_font(path):
    env = UnityPy.load(path)
    font = material = atlas = None
    for o in env.objects:
        if o.type.name == "MonoBehaviour":
            tt = o.read_typetree()
            if "m_CharacterTable" in tt:
                font = tt
        elif o.type.name == "Material":
            material = o.read_typetree()
        elif o.type.name == "Texture2D":
            atlas = o.read()
    if not (font and material and atlas):
        raise RuntimeError(f"{path}: font, material or atlas missing")
    if atlas.m_TextureFormat != 1:
        raise RuntimeError("expected an Alpha8 SDF atlas")
    return font, material, atlas.m_Width, atlas.m_Height, bytearray(atlas.get_image_data())


def _take_free_rect(font, w, h):
    """Reserve a w*h area from the free-rect list (guillotine split) and return its origin."""
    free = sorted(font["m_FreeGlyphRects"], key=lambda r: r["m_Width"] * r["m_Height"])
    for r in free:
        if r["m_Width"] >= w and r["m_Height"] >= h:
            font["m_FreeGlyphRects"].remove(r)
            x, y = r["m_X"], r["m_Y"]
            right = {"m_X": x + w, "m_Y": y, "m_Width": r["m_Width"] - w, "m_Height": h}
            top = {"m_X": x, "m_Y": y + h, "m_Width": r["m_Width"], "m_Height": r["m_Height"] - h}
            font["m_FreeGlyphRects"] += [q for q in (right, top) if q["m_Width"] > 0 and q["m_Height"] > 0]
            font["m_UsedGlyphRects"].append({"m_X": x, "m_Y": y, "m_Width": w, "m_Height": h})
            return x, y
    raise RuntimeError(f"no free {w}x{h} area in the atlas")


def add_ellipsis(font, atlas, width):
    """Compose U+2026 from three copies of the font's own period glyph."""
    if any(c["m_Unicode"] == ELLIPSIS for c in font["m_CharacterTable"]):
        return False
    pad = font["m_AtlasPadding"]
    char = next(c for c in font["m_CharacterTable"] if c["m_Unicode"] == PERIOD)
    glyph = next(g for g in font["m_GlyphTable"] if g["m_Index"] == char["m_GlyphIndex"])
    r, m = glyph["m_GlyphRect"], glyph["m_Metrics"]
    step = round(m["m_HorizontalAdvance"])
    src_w, src_h = r["m_Width"] + 2 * pad, r["m_Height"] + 2 * pad
    dst_w = src_w + 2 * step
    ox, oy = _take_free_rect(font, dst_w + 1, src_h + 1)

    for k in range(3):
        for row in range(src_h):
            s = (r["m_Y"] - pad + row) * width + (r["m_X"] - pad)
            d = (oy + row) * width + ox + k * step
            for col in range(src_w):
                # Union of distance fields: the larger value is nearer the inside of either shape.
                atlas[d + col] = max(atlas[d + col], atlas[s + col])

    new = copy.deepcopy(glyph)
    new["m_Index"] = max(g["m_Index"] for g in font["m_GlyphTable"]) + 1
    new["m_GlyphRect"] = {"m_X": ox + pad, "m_Y": oy + pad,
                          "m_Width": r["m_Width"] + 2 * step, "m_Height": r["m_Height"]}
    new["m_Metrics"] = dict(m, m_Width=m["m_Width"] + 2 * step, m_HorizontalAdvance=m["m_HorizontalAdvance"] * 3)
    font["m_GlyphTable"].append(new)
    font["m_CharacterTable"].append({"m_ElementType": char["m_ElementType"], "m_Unicode": ELLIPSIS,
                                     "m_GlyphIndex": new["m_Index"], "m_Scale": char["m_Scale"]})
    return True


# Alagard is a 16px pixel font sampled at 94pt, so one design pixel is 94/16 atlas texels.
PIXEL = 5.875
# Measured on the font's own glyphs: the edge sits at 128 and the value changes ~12.75 per texel.
SDF_EDGE, SDF_SLOPE = 128.0, 12.75

# Pixel art for the missing glyphs, top row first, drawn in the font's style
# (thin upper strokes, heavier lower strokes, hyphen with a shortened top row).
PIXEL_GLYPHS = {
    0x2013: dict(rows=["#########.", "##########"], top=6, advance=11),            # en dash
    0x2014: dict(rows=["#############.", "##############"], top=6, advance=15),    # em dash
    0x00AB: dict(rows=["...#...#", "..#...#.", ".#...#..", "#...#...", "##..##..", ".##..##.", "..##..##"],
                 top=8, advance=9),                                                # «
    0x00BB: dict(rows=["#...#...", ".#...#..", "..#...#.", "...#...#", "..##..##", ".##..##.", "##..##.."],
                 top=8, advance=9),                                                # »
}


def _pixel_sdf(rows):
    """Signed distance (in texels, positive inside) for a pixel bitmap scaled by PIXEL."""
    h = len(rows)
    filled = {(x, h - 1 - y) for y, row in enumerate(rows) for x, c in enumerate(row) if c == "#"}
    segments = []
    for x, y in filled:
        x0, y0, x1, y1 = x * PIXEL, y * PIXEL, (x + 1) * PIXEL, (y + 1) * PIXEL
        if (x - 1, y) not in filled:
            segments.append((x0, y0, x0, y1))
        if (x + 1, y) not in filled:
            segments.append((x1, y0, x1, y1))
        if (x, y - 1) not in filled:
            segments.append((x0, y0, x1, y0))
        if (x, y + 1) not in filled:
            segments.append((x0, y1, x1, y1))

    def dist(px, py):
        best = float("inf")
        for ax, ay, bx, by in segments:
            cx, cy = min(max(px, min(ax, bx)), max(ax, bx)), min(max(py, min(ay, by)), max(ay, by))
            best = min(best, (px - cx) ** 2 + (py - cy) ** 2)
        inside = (int(px // PIXEL), int(py // PIXEL)) in filled and px >= 0 and py >= 0
        return best ** 0.5 if inside else -(best ** 0.5)

    return dist


def add_pixel_glyph(font, atlas, width, unicode, rows, top, advance):
    """Draw a glyph from pixel art: `top` is the height of its top edge above the baseline in pixels."""
    if any(c["m_Unicode"] == unicode for c in font["m_CharacterTable"]):
        return False
    pad = font["m_AtlasPadding"]
    gw, gh = len(rows[0]) * PIXEL, len(rows) * PIXEL
    rw, rh = int(-(-gw // 1)), int(-(-gh // 1))
    ox, oy = _take_free_rect(font, rw + 2 * pad + 1, rh + 2 * pad + 1)
    dist = _pixel_sdf(rows)
    for ty in range(rh + 2 * pad):
        for tx in range(rw + 2 * pad):
            d = dist(tx - pad + 0.5, ty - pad + 0.5)
            atlas[(oy + ty) * width + ox + tx] = max(0, min(255, round(SDF_EDGE + SDF_SLOPE * d)))
    template = font["m_GlyphTable"][0]
    index = max(g["m_Index"] for g in font["m_GlyphTable"]) + 1
    glyph = copy.deepcopy(template)
    glyph.update(m_Index=index,
                 m_GlyphRect={"m_X": ox + pad, "m_Y": oy + pad, "m_Width": rw, "m_Height": rh},
                 m_Metrics={"m_Width": gw, "m_Height": gh, "m_HorizontalBearingX": 0.0,
                            "m_HorizontalBearingY": top * PIXEL, "m_HorizontalAdvance": advance * PIXEL})
    font["m_GlyphTable"].append(glyph)
    period = next(c for c in font["m_CharacterTable"] if c["m_Unicode"] == PERIOD)
    font["m_CharacterTable"].append({"m_ElementType": period["m_ElementType"], "m_Unicode": unicode,
                                     "m_GlyphIndex": index, "m_Scale": period["m_Scale"]})
    return True


def font_characters(source_path):
    """Every character the patched font can draw, including the glyphs composed by this module."""
    src = load_source_font(source_path)[0]
    return {chr(c["m_Unicode"]) for c in src["m_CharacterTable"]} | {chr(ELLIPSIS)} | {chr(c) for c in PIXEL_GLYPHS}


def patch_game_font(env, font_path_id, material_path_id, atlas_path_id, source_path):
    """Apply the source font to the font, material and atlas objects inside an already loaded env."""
    src, src_mat, w, h, atlas = load_source_font(source_path)
    added = add_ellipsis(src, atlas, w)
    for code, spec in PIXEL_GLYPHS.items():
        add_pixel_glyph(src, atlas, w, code, **spec)

    objs = {o.path_id: o for o in env.objects}
    font = objs[font_path_id].read_typetree()
    if font.get("m_Name") != "alagard SDF":
        raise RuntimeError("unexpected font object")
    for key in FONT_FIELDS:
        font[key] = src[key]
    objs[font_path_id].save_typetree(font)

    mat = objs[material_path_id].read_typetree()
    src_floats = dict(src_mat["m_SavedProperties"]["m_Floats"])
    mat["m_SavedProperties"]["m_Floats"] = [(k, src_floats[k] if k in MATERIAL_FLOATS else v)
                                            for k, v in mat["m_SavedProperties"]["m_Floats"]]
    objs[material_path_id].save_typetree(mat)

    tex = objs[atlas_path_id].read()
    tex.m_Width, tex.m_Height = w, h
    tex.image_data = bytes(atlas)
    tex.m_CompleteImageSize = len(atlas)
    tex.m_StreamData.path, tex.m_StreamData.offset, tex.m_StreamData.size = "", 0, 0
    tex.save()
    return len(src["m_CharacterTable"]), added

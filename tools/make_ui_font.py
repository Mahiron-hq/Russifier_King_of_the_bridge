"""Rebuilds the Cyrillic Alagard pixel font as a TrueType file for the installer window.

The font is only available as a TextMeshPro SDF atlas. Alagard is drawn on a 16-pixel em, and the atlas renders one
font pixel as PointSize / 16 atlas pixels, so sampling the distance field at the centre of every font pixel recovers
the original bitmap exactly. Each lit pixel becomes a square outline, which keeps the font crisp at multiples of 16 px.

Usage: make_ui_font.py <output.ttf>
"""
import os
import sys

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from font_patch import ELLIPSIS, PERIOD, PIXEL_GLYPHS, load_source_font

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(REPO, "assets", "fonts", "alagard-unicode-tmp")
EM_PIXELS = 16
UNIT = 64
THRESHOLD = 128
FAMILY = "Alagard Cyrillic"


def glyph_bitmap(glyph, atlas, width, cell):
    """Rows of lit font pixels, top row first, sampled at the cell centres of the glyph rect."""
    m, r = glyph["m_Metrics"], glyph["m_GlyphRect"]
    cols, rows = round(m["m_Width"] / cell), round(m["m_Height"] / cell)
    bitmap = []
    for row in range(rows):
        # Atlas rows run bottom-up, so the glyph's top row sits at the highest y.
        y = int(r["m_Y"] + (rows - row - 0.5) * cell)
        bitmap.append([atlas[y * width + int(r["m_X"] + (col + 0.5) * cell)] >= THRESHOLD for col in range(cols)])
    return bitmap


def draw(bitmap, left, top):
    """Outline of a bitmap traced along the pixel borders.

    Every lit pixel contributes its four clockwise edges; edges shared by two lit pixels cancel, so only the
    outer borders and the borders of holes remain and the glyph has no internal seams that antialiasing could
    show as hairlines.
    """
    edges = {}
    for row, pixels in enumerate(bitmap):
        y0 = top - row - 1
        for col, lit in enumerate(pixels):
            if not lit:
                continue
            x = left + col
            for start, end in (((x, y0), (x, y0 + 1)), ((x, y0 + 1), (x + 1, y0 + 1)),
                               ((x + 1, y0 + 1), (x + 1, y0)), ((x + 1, y0), (x, y0))):
                if (end, start) in edges:
                    del edges[(end, start)]
                else:
                    edges[(start, end)] = True
    outgoing = {}
    for start, end in edges:
        outgoing.setdefault(start, []).append(end)

    def turn(prev, here, options):
        # Where two contours touch at a corner, keep to the sharpest right turn so they stay separate.
        dx, dy = here[0] - prev[0], here[1] - prev[1]
        right = (dy, -dx)
        for d in (right, (dx, dy), (-dy, dx)):
            nxt = (here[0] + d[0], here[1] + d[1])
            if nxt in options:
                return nxt
        return options[0]

    pen = TTGlyphPen(None)
    while outgoing:
        start = next(iter(outgoing))
        loop, prev, here = [start], None, start
        while True:
            options = outgoing[here]
            nxt = options[0] if prev is None or len(options) == 1 else turn(prev, here, options)
            options.remove(nxt)
            if not options:
                del outgoing[here]
            if nxt == start:
                break
            loop.append(nxt)
            prev, here = here, nxt
        # Drop the points in the middle of straight runs.
        corners = [p for i, p in enumerate(loop)
                   if (p[0] - loop[i - 1][0]) * (loop[(i + 1) % len(loop)][1] - p[1])
                   != (p[1] - loop[i - 1][1]) * (loop[(i + 1) % len(loop)][0] - p[0])]
        pen.moveTo((corners[0][0] * UNIT, corners[0][1] * UNIT))
        for x, y in corners[1:]:
            pen.lineTo((x * UNIT, y * UNIT))
        pen.closePath()
    return pen.glyph()


def main(out):
    font, _, width, _, atlas = load_source_font(SOURCE)
    face = font["m_FaceInfo"]
    cell = face["m_PointSize"] / EM_PIXELS
    glyphs = {g["m_Index"]: g for g in font["m_GlyphTable"]}

    order, cmap, outlines, metrics = [".notdef"], {}, {".notdef": TTGlyphPen(None).glyph()}, {".notdef": (8 * UNIT, 0)}
    for char in sorted(font["m_CharacterTable"], key=lambda c: c["m_Unicode"]):
        glyph = glyphs[char["m_GlyphIndex"]]
        m = glyph["m_Metrics"]
        name = "uni%04X" % char["m_Unicode"]
        left = round(m["m_HorizontalBearingX"] / cell)
        top = round(m["m_HorizontalBearingY"] / cell)
        outlines[name] = draw(glyph_bitmap(glyph, atlas, width, cell), left, top)
        metrics[name] = (round(m["m_HorizontalAdvance"] / cell) * UNIT, left * UNIT)
        order.append(name)
        cmap[char["m_Unicode"]] = name

    for unicode, spec in PIXEL_GLYPHS.items():
        name = "uni%04X" % unicode
        bitmap = [[c == "#" for c in row] for row in spec["rows"]]
        outlines[name] = draw(bitmap, 0, spec["top"])
        metrics[name] = (spec["advance"] * UNIT, 0)
        order.append(name)
        cmap[unicode] = name

    period = glyphs[next(c["m_GlyphIndex"] for c in font["m_CharacterTable"] if c["m_Unicode"] == PERIOD)]
    dot = glyph_bitmap(period, atlas, width, cell)
    step = round(period["m_Metrics"]["m_HorizontalAdvance"] / cell)
    dots = [sum(([*r] + [False] * (step - len(r)) for _ in range(3)), []) for r in dot]
    outlines["uni2026"] = draw(dots, 0, round(period["m_Metrics"]["m_HorizontalBearingY"] / cell))
    metrics["uni2026"] = (3 * step * UNIT, 0)
    order.append("uni2026")
    cmap[ELLIPSIS] = "uni2026"

    ascent = round(face["m_AscentLine"] / cell) * UNIT
    descent = round(face["m_DescentLine"] / cell) * UNIT
    builder = FontBuilder(EM_PIXELS * UNIT, isTTF=True)
    builder.setupGlyphOrder(order)
    builder.setupCharacterMap(cmap)
    builder.setupGlyf(outlines)
    builder.setupHorizontalMetrics(metrics)
    builder.setupHorizontalHeader(ascent=ascent, descent=descent)
    builder.setupNameTable({"familyName": FAMILY, "styleName": "Regular"})
    builder.setupOS2(sTypoAscender=ascent, sTypoDescender=descent, usWinAscent=ascent, usWinDescent=-descent)
    builder.setupPost()
    builder.save(out)
    print("%s: %d glyphs" % (out, len(cmap)))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])

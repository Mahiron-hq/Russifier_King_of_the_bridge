"""Builds the Russian sprites that replace English words drawn into images.

Table-of-contents links: the English handwriting is erased, the two bracket strokes are kept, and the Russian
caption is typeset in BubbleSans (the font of the translated rulebook pages). Letters are placed by their ink width
with an even gap, sit on a smoothed copy of the English line's baseline and tilt with it, so the Russian keeps the
waves of the handwriting.
Bridge tile "tutorial5": the pixel-art "OR" is repainted as "ИЛИ" from hand-drawn strokes in the same moss colour.
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from toc_baselines import Baseline, components, split_lines

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(REPO, "reference", "toc_en")
OUT_DIR = os.path.join(REPO, "assets", "sprites_ru")
FONT = os.path.join(REPO, "assets", "fonts", "BubbleSans-Regular.otf")

SCALE = 8
STROKE = 0.12
# Right end of a line: just before the right bracket where they share rows, a little past it elsewhere.
BRACKET_CLEARANCE = 2.5
FREE_RIGHT = 140
MAX_CAP = 8.5
MIN_CAP = 6.0
# Gaps between letter ink in sprite pixels, tried widest first. Narrower letters are preferred over smaller
# gaps: the English handwriting itself is narrow, while touching letters stop being readable.
LETTER_GAPS = (1.6, 1.4, 1.2)
CONDENSE_STEPS = (1.0, 0.9, 0.82, 0.76)
WORD_GAP = 4.2
DOT_GAP = 1.1

# Lines in "~~...~~" are drawn struck through, like the corrected word in the English caption 17.
CAPTIONS = {
    "e1": ("...ЭПИЛОГ...", ""),
    "r0": ("00 ...ПОЙМАЕТЕ", "ОБМАН...В ОТВЕТ..."),
    "r1": ("01 ...ЛОЖНО...", "...ПРОПУСТИТЕ ХОД..."),
    "r2": ("02 ...ТОЛЬКО ФИГУРЫ", "СВОЕГО... ЦВЕТА..."),
    "r3": ("03 ...ДВИГАТЬ ФЕРЗЕЙ...", "ДРУГОГО... ЦВЕТА..."),
    "r4": ("04 ...ПЕШКИ ХОДЯТ...", "МАЛЕНЬКИЕ МОЗГИ..."),
    "r5": ("05 ...ПЕШКИ...", "МЕТАФОРА..."),
    "r6": ("06 ...ПЕШКИ...", "ХОДИТЬ НАЗАД..."),
    "r7": ("07 ...КОНЬ...", "ХОД... НЕ ВСЕ ДОМА..."),
    "r8": ("08", "ОН."),
    "r9": ("09 ...ПЕРЕПРЫГИВАТЬ...", "ДРУГИЕ ФИГУРЫ..."),
    "r10": ("10 ...БЕЛЫЙ КОРОЛЬ", "УМИРАЕТ...ЧЁРНЫЕ..."),
    "r11": ("11 ...ЧЁРНЫЙ КОРОЛЬ", "ПОГИБНЕТ...ЦИКЛ..."),
    "r12": ("12 ...КОРОЛЬ...", "ХОДИТ... ЛЕНИВ..."),
    "r13": ("13 ...СЛОН...", "ХОДИТ... %s..." % "{ARROWS}"),
    "r14": ("14 ...БАШНИ...", "НАУЧИЛИСЬ ХОДИТЬ..."),
    "r15": ("15 ...СЛОН РАБОТАЕТ", "ЗА ГОРОДОМ..."),
    "r16": ("16 ...ДВЕ ЛАДЬИ...", "ОБРАЗУЮТ... ЗАМОК..."),
    "r17": ("17 ...ЗАМКИ ~~СОЗ~~", "ОСКОЛКИ ВАЛОРИТА..."),
    "r18": ("18 ...ДАМА...ХОДИТ...", "ПОЛЗАМКА + СЛОН..."),
    "r19": ("19 ...МОРЩИНИСТЫХ...", "ТРОЛЛЕЙ..."),
    "r20": ("20 ...ЛЮБАЯ ПЕШКА...", "ПРЕДЕЛА... ВОЗНОСИТСЯ"),
    "r21": ("21 ...ФЕРЗЬ...", "МИР ВВЕРХ ДНОМ..."),
    "r22": ("22 ...СЛОНЫ...", "ДАР ЗНАНИЯ... КЛЕТКУ..."),
    "r23": ("23 ...ЛАДЬИ ЕДЯТ...", "СОЮЗНЫЕ... МОЩЬ..."),
    "r24": ("24 ...НЕ ХОДИТЕ", "...В ЧУЖИХ БОТИНКАХ..."),
    "r25": ("25 ...НИ ОДНА ФИГУРА...", "...ЗА ПРЕДЕЛЫ ДОСКИ"),
    "r26": ("26 ...НЕ ПЕРЕМЕЩАЙТЕ...", "...ДАРЫ..."),
    "r27": ("27 ...ЕСТЬ КЛЕТКИ...", "СКОЛЬЗКИЕ..."),
    "r28": ("28 ...ДВИГАТЬ ЗАМКИ", "ТРИ... ЛАДЬИ..."),
    "r29": ("29 ...КОРОЛЕВА РОМАН", "КОСНЁТСЯ... КОРОЛЯ..."),
    "t1": ("T1 ...ПОДОЗРЕВАЕТЕ...", "СЖУЛЬНИЧАЛ..."),
    "t2": ("T2 ...ФИГУРУ...", "...ЗАТЕМ СТРАНИЦУ..."),
}
# Stand-in character for a hand-drawn sign of crossed diagonal arrows (the bishop's "X").
ARROWS = "╳"
ARROWS_HEIGHT = 1.45
CAPTIONS["r13"] = (CAPTIONS["r13"][0], CAPTIONS["r13"][1].replace("{ARROWS}", ARROWS))
# Captions whose second line copies the wave of the first: the Russian lines are longer than the English ones,
# and the English second line alone would leave their ends hanging low.
LOWER_FOLLOWS_UPPER = {("t1", "l"), ("t1", "r"), ("r27", "l"), ("r27", "r"), ("t2", "l"), ("r6", "l"), ("r6", "r")}
# (caption, side) -> index of the line that keeps rising to its end instead of levelling out after the English text.
STEADY_LINES = {("r1", "l"): 0}
# Captions drawn letter for letter over the English letters instead of along a line ("HE." -> "ОН.").
LETTER_FOR_LETTER = {"r8"}


def bracket_mask(alpha):
    """Pixels of the two bracket strokes, together with any English letters that touch them."""
    keep = np.zeros(alpha.shape, dtype=bool)
    for c in components(alpha, threshold=0):
        if c["y1"] - c["y0"] >= 18:
            for p in c["pixels"]:
                keep[p] = True
    return keep


def clean_brackets(side):
    """Bracket strokes of the caption "...EPILOGUE...": every link of a side has its brackets at the same place,
    and nothing touches them in this one."""
    alpha = np.array(Image.open(os.path.join(SOURCE_DIR, "link_e1_%s.png" % side)).convert("RGBA"))[..., 3]
    return np.where(bracket_mask(alpha), alpha, 0)


def caption_runs(line):
    """Yields (char, struck) pairs; text between "~~" marks is struck through."""
    for i, part in enumerate(line.split("~~")):
        for ch in part:
            yield ch, i % 2 == 1


def paste_max(canvas, glyph, left, top):
    h, w = glyph.shape
    y0, x0 = max(0, top), max(0, left)
    y1, x1 = min(canvas.shape[0], top + h), min(canvas.shape[1], left + w)
    if y1 > y0 and x1 > x0:
        region = canvas[y0:y1, x0:x1]
        canvas[y0:y1, x0:x1] = np.maximum(region, glyph[y0 - top:y1 - top, x0 - left:x1 - left])


class Lettering:
    """BubbleSans at a given letter height, horizontal narrowing and gap between letters."""

    def __init__(self, cap, condense=1.0, gap=LETTER_GAPS[0]):
        probe = ImageFont.truetype(FONT, 200)
        box = probe.getbbox("Н", anchor="ls")
        self.size = cap / ((box[3] - box[1]) / 200.0)
        self.font = ImageFont.truetype(FONT, round(self.size * SCALE))
        self.cap = cap
        self.condense = condense
        self.gap = gap

    def ink_width(self, ch):
        if ch == ARROWS:
            return self.cap * 1.7 * self.condense
        left, _, right, _ = self.font.getbbox(ch, anchor="ls")
        return (right - left) / SCALE * self.condense

    def advance(self, ch, next_ch):
        if ch == " ":
            return WORD_GAP
        gap = DOT_GAP if ch == "." or next_ch == "." else self.gap
        return self.ink_width(ch) + (gap if next_ch not in (None, " ") else 0.0)

    def width(self, line):
        chars = [ch for ch, _ in caption_runs(line)]
        return sum(self.advance(ch, chars[i + 1] if i + 1 < len(chars) else None) for i, ch in enumerate(chars))

    def glyph(self, ch, height_scale=1.0):
        """Glyph alpha at SCALE and its pivot: the middle of the ink on the baseline."""
        pad = round(self.size * SCALE * height_scale)
        font = self.font if height_scale == 1.0 else ImageFont.truetype(FONT, round(self.size * SCALE * height_scale))
        left, _, right, _ = font.getbbox(ch, anchor="ls")
        ascent, descent = font.getmetrics()
        img = Image.new("L", (right + 2 * pad, ascent + descent + 2 * pad), 0)
        ImageDraw.Draw(img).text((pad, pad + ascent), ch, font=font, fill=255, anchor="ls",
                                 stroke_width=round(STROKE * SCALE), stroke_fill=255)
        img = img.resize((max(1, round(img.width * self.condense)), img.height), Image.LANCZOS)
        return img, ((pad + (left + right) / 2) * self.condense, pad + ascent)

    def arrows(self):
        """Two crossed diagonal arrows with heads on all four ends, drawn with the letters' stroke weight."""
        w, h = self.ink_width(ARROWS) * SCALE, self.cap * ARROWS_HEIGHT * SCALE
        pad = round(h)
        img = Image.new("L", (round(w) + 2 * pad, round(h) + 2 * pad), 0)
        draw = ImageDraw.Draw(img)
        stroke = round(0.95 * SCALE)
        head = h * 0.34
        ends = [((pad, pad + h), (pad + w, pad)), ((pad, pad), (pad + w, pad + h))]
        for a, b in ends:
            draw.line((a, b), fill=255, width=stroke)
            for (tx, ty), (fx, fy) in ((b, a), (a, b)):
                direction = math.atan2(ty - fy, tx - fx)
                for side in (-1, 1):
                    angle = direction + math.pi - side * math.radians(35)
                    draw.line(((tx, ty), (tx + head * math.cos(angle), ty + head * math.sin(angle))),
                              fill=255, width=stroke)
                r = stroke / 2
                draw.ellipse((tx - r, ty - r, tx + r, ty + r), fill=255)
        # Sits a little below the baseline, like the English "X", so it reads at the size of the letters.
        return img, (pad + w / 2, pad + h - 0.12 * h)

    def place(self, canvas, ch, cx, base_y, angle, height_scale=1.0):
        img, (px, py) = self.arrows() if ch == ARROWS else self.glyph(ch, height_scale)
        img = img.rotate(angle, resample=Image.BICUBIC, center=(px, py))
        paste_max(canvas, np.array(img), round(cx * SCALE - px), round(base_y * SCALE - py))

    def draw_line(self, canvas, line, baseline):
        chars = [(ch, strike) for ch, strike in caption_runs(line)]
        x = float(baseline.x0)
        struck = []
        for i, (ch, strike) in enumerate(chars):
            next_ch = chars[i + 1][0] if i + 1 < len(chars) else None
            ink = self.ink_width(ch) if ch != " " else 0.0
            cx = x + ink / 2
            if ch != " ":
                angle = -math.degrees(math.atan(baseline.slant(cx)))
                self.place(canvas, ch, cx, baseline.y(cx), max(-25.0, min(25.0, angle)))
            if strike:
                struck.append((x, x + ink))
            x += self.advance(ch, next_ch)
        if struck:
            x0, x1 = struck[0][0] - 1, struck[-1][1] + 1
            lift = self.cap * 0.45
            img = Image.fromarray(canvas)
            ImageDraw.Draw(img).line(
                (x0 * SCALE, (baseline.y(x0) - lift) * SCALE,
                 x1 * SCALE, (baseline.y(x1) - lift - 1) * SCALE),
                fill=255, width=round(1.4 * SCALE))
            canvas[...] = np.array(img)


def fit_lettering(lines, baselines, limits):
    """One letter height for the caption, the largest that fits; then each line gets the widest letters and gaps
    it has room for, so a short line is not squeezed because its neighbour is long."""
    def fits(lettering, line, baseline, limit):
        return baseline.x0 + lettering.width(line) <= limit

    def options(cap):
        return [Lettering(cap, condense, gap) for condense in CONDENSE_STEPS for gap in LETTER_GAPS]

    cap = min(MAX_CAP, float(np.median([b.cap for b in baselines])))
    while cap >= MIN_CAP:
        choice = []
        for line, baseline, limit in zip(lines, baselines, limits):
            choice.append(next((l for l in options(cap) if fits(l, line, baseline, limit)), None))
        if all(choice):
            return choice
        cap -= 0.25
    raise ValueError("caption does not fit: " + " / ".join(lines))


def right_limit(brackets, baseline):
    ys = [baseline.y(x) for x in range(int(baseline.x0), FREE_RIGHT + 1)]
    top, bottom = int(min(ys) - MAX_CAP - 1), int(max(ys) + 1)
    rows, cols = np.nonzero(brackets[max(0, top):bottom + 1, :])
    cols = cols[cols > brackets.shape[1] // 2]
    return min(FREE_RIGHT, cols.min() - BRACKET_CLEARANCE) if len(cols) else FREE_RIGHT


LINE_CLEARANCE = 2.0


def separate_lines(lines, baselines, letterings, height):
    """Moves lines apart where a longer Russian line would run into the line below it."""
    for i in range(len(lines) - 1):
        upper, lower = baselines[i], baselines[i + 1]
        x_end = min(upper.x0 + letterings[i].width(lines[i]), lower.x0 + letterings[i + 1].width(lines[i + 1]))
        xs = np.arange(max(upper.x0, lower.x0), x_end + 1, 1.0)
        if not len(xs):
            continue
        tallest = letterings[i + 1].cap * (ARROWS_HEIGHT if ARROWS in lines[i + 1] else 1.0)
        overlap = max(upper.y(x) + LINE_CLEARANCE - (lower.y(x) - tallest) for x in xs)
        if overlap > 0:
            room_below = height - 2 - max(lower.y(x) for x in xs)
            down = min(overlap, max(0.0, room_below))
            lower.offset += down
            upper.offset -= overlap - down


def english_letters(alpha, brackets):
    return [c for c in components(alpha) if c["y1"] - c["y0"] < 30 and not brackets[c["pixels"][0]]]


class FollowingBaseline:
    """Lower line that repeats the wave of the line above it, keeping its own start point."""

    def __init__(self, upper, lower):
        self.upper = upper
        self.x0, self.x1, self.cap = lower.x0, lower.x1, lower.cap
        self.distance = lower.y(lower.x0) - upper.y(lower.x0)
        self.offset = 0.0

    def y(self, x):
        return self.upper.y(x) + self.distance + self.offset

    def slant(self, x):
        return self.upper.slant(x)


class SteadyBaseline:
    """Gentle wave of the whole English line that keeps its slope past the last letter."""

    def __init__(self, base):
        self.base = base
        self.x0, self.x1, self.cap = base.x0, base.x1, base.cap
        self.offset = 0.0

    def y(self, x):
        lo, hi = self.base.xs.min(), self.base.xs.max()
        edge = min(max(x, lo), hi)
        y_edge, k = self.base._fit(edge, self.base.SLANT_SIGMA)
        return y_edge + k * (x - edge) + self.offset

    def slant(self, x):
        return self.base.slant(x)


def render_on_baselines(alpha, brackets, lines, follow_upper=False, steady=None):
    baselines = [Baseline(line) for line in split_lines(english_letters(alpha, brackets))]
    lines = [line for line in lines if line]
    if len(baselines) < len(lines):
        raise ValueError("%d lines of text but %d English lines" % (len(lines), len(baselines)))
    baselines = baselines[:len(lines)]
    # Leading dots are too small to join a line, so start every line at the caption's left margin at the latest.
    margin = min(b.x0 for b in baselines)
    for b in baselines:
        b.x0 = min(b.x0, margin + 1)
    if steady is not None:
        baselines[steady] = SteadyBaseline(baselines[steady])
    limits = [right_limit(brackets, b) for b in baselines]
    if follow_upper:
        baselines = [baselines[0]] + [FollowingBaseline(baselines[0], b) for b in baselines[1:]]
    letterings = fit_lettering(lines, baselines, limits)
    separate_lines(lines, baselines, letterings, alpha.shape[0])
    canvas = np.zeros((alpha.shape[0] * SCALE, alpha.shape[1] * SCALE), dtype=np.uint8)
    for line, baseline, lettering in zip(lines, baselines, letterings):
        lettering.draw_line(canvas, line, baseline)
    return canvas, letterings


def letter_tilt(component):
    """Tilt of a handwritten letter, from the line through the lowest pixel of each of its columns."""
    bottoms = {}
    for y, x in component["pixels"]:
        bottoms[x] = max(bottoms.get(x, y), y)
    xs = np.array(sorted(bottoms), dtype=float)
    if len(xs) < 3:
        return 0.0
    ys = np.array([bottoms[int(x)] for x in xs], dtype=float)
    return -math.degrees(math.atan(np.polyfit(xs, ys, 1)[0]))


def letter_groups(letters, max_gap=1):
    """Merges the strokes of one handwritten letter (an "H" is often two strokes) into a single component."""
    groups = []
    for c in sorted(letters, key=lambda c: c["x0"]):
        if groups and c["x0"] - groups[-1]["x1"] <= max_gap:
            g = groups[-1]
            g["pixels"] = g["pixels"] + c["pixels"]
            g["x1"] = max(g["x1"], c["x1"])
            g["y0"], g["y1"] = min(g["y0"], c["y0"]), max(g["y1"], c["y1"])
            g["cx"] = (g["x0"] + g["x1"]) / 2
        else:
            groups.append(dict(c, cx=(c["x0"] + c["x1"]) / 2))
    return groups


def render_letter_for_letter(alpha, brackets, lines):
    """Keeps the English number and puts each Russian letter where an English one was, at its height and tilt."""
    number, word = lines
    letters = letter_groups(english_letters(alpha, brackets))
    keep = letters[:len(number)]
    targets = letters[len(number):]
    chars = [ch for ch in word if ch != " "]
    if len(targets) != len(chars):
        raise ValueError("%d English letters for %d Russian ones" % (len(targets), len(chars)))
    canvas = np.zeros((alpha.shape[0] * SCALE, alpha.shape[1] * SCALE), dtype=np.uint8)
    for c in keep:
        for y, x in c["pixels"]:
            canvas[y * SCALE:(y + 1) * SCALE, x * SCALE:(x + 1) * SCALE] = alpha[y, x]
    # The English letters differ in height; the Russian ones all get the tallest so none reads as lowercase.
    tallest = max(t["y1"] - t["y0"] + 1 for t, ch in zip(targets, chars) if ch != ".")
    for ch, letter in zip(chars, targets):
        height = tallest
        if ch == ".":
            Lettering(8.0).place(canvas, ch, letter["cx"], letter["y1"] + 0.6, 0.0, height_scale=1.6)
        else:
            Lettering(height, condense=0.95).place(canvas, ch, letter["cx"], letter["y1"] + 0.5, letter_tilt(letter))
    return canvas, None


def build(name, side):
    src = Image.open(os.path.join(SOURCE_DIR, "link_%s_%s.png" % (name, side))).convert("RGBA")
    rgba = np.array(src)
    alpha = rgba[..., 3]
    brackets = bracket_mask(alpha)

    if name in LETTER_FOR_LETTER:
        canvas, lettering = render_letter_for_letter(alpha, brackets, CAPTIONS[name])
    else:
        canvas, letterings = render_on_baselines(alpha, brackets, CAPTIONS[name], (name, side) in LOWER_FOLLOWS_UPPER,
                                                    STEADY_LINES.get((name, side)))
        print("link_%s_%s: letter height %.2f, lines (width, gap): %s" % (
            name, side, letterings[0].cap, ", ".join("%.2f/%.2f" % (l.condense, l.gap) for l in letterings)))
    text = np.array(Image.fromarray(canvas).resize((alpha.shape[1], alpha.shape[0]), Image.LANCZOS))

    out = np.zeros_like(rgba)
    out[..., :3] = 255
    out[..., 3] = np.maximum(clean_brackets(side), text).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


TILE_SOURCE = os.path.join(REPO, "reference", "tiles_en", "tutorial5.png")
TILE_WORD_BOX = (19, 24, 45, 39)
TILE_SUPERSAMPLE = 8
TILE_SHIFT = 0.6
# Hand-drawn strokes of "ИЛИ" as (width, points) in tile pixels, spread over the free stone around the English
# word and slightly uneven like the brush strokes of the original "OR"; diagonals are thicker so they stay unbroken.
TILE_STROKES = [
    (2.8, [(16.3, 26.0), (16.0, 30.5), (16.2, 35.0)]),
    (2.8, [(21.6, 25.7), (21.8, 30.3), (21.4, 35.0)]),
    (3.1, [(16.4, 34.0), (19.0, 30.6), (21.4, 27.0)]),
    (2.8, [(29.0, 25.9), (31.3, 25.6), (33.4, 25.8)]),
    (2.8, [(29.0, 26.0), (28.6, 29.5), (27.6, 33.0), (26.2, 35.2)]),
    (2.8, [(33.4, 25.8), (33.7, 30.6), (33.3, 35.2)]),
    (2.8, [(38.4, 26.2), (38.2, 30.8), (38.5, 35.4)]),
    (2.8, [(43.6, 25.9), (43.4, 30.5), (43.8, 35.2)]),
    (3.1, [(38.6, 34.0), (41.1, 30.6), (43.4, 27.2)]),
]


def build_tile():
    src = np.array(Image.open(TILE_SOURCE).convert("RGBA"))
    stone = src[30, 18].copy()
    moss = src[17, 36].copy()
    x0, y0, x1, y1 = TILE_WORD_BOX
    out = src.copy()
    word = out[y0:y1, x0:x1]
    word[(word[..., 3] > 0)] = stone

    s = TILE_SUPERSAMPLE
    ink = Image.new("L", (64 * s, 64 * s), 0)
    draw = ImageDraw.Draw(ink)
    for width, stroke in TILE_STROKES:
        r = width * s / 2
        points = [((x + TILE_SHIFT) * s, y * s) for x, y in stroke]
        draw.line(points, fill=255, width=round(width * s))
        for px, py in points:
            draw.ellipse((px - r, py - r, px + r, py + r), fill=255)
    coverage = np.array(ink.resize((64, 64), Image.BOX)) / 255.0
    stone_pixels = np.all(out == stone, axis=-1)
    out[(coverage >= 0.5) & stone_pixels] = moss
    return Image.fromarray(out, "RGBA")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name in CAPTIONS:
        for side in ("l", "r"):
            build(name, side).save(os.path.join(OUT_DIR, "link_%s_%s.png" % (name, side)))
    build_tile().save(os.path.join(OUT_DIR, "tutorial5.png"))
    print("written", len(CAPTIONS) * 2 + 1, "sprites to", OUT_DIR)


if __name__ == "__main__":
    sys.exit(main())

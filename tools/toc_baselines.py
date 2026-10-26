"""Extracts the baseline curve of each handwritten line in the English table-of-contents sprites."""
import math
from collections import deque

import numpy as np


def components(alpha, threshold=40):
    h, w = alpha.shape
    mask = alpha > threshold
    seen = np.zeros_like(mask)
    result = []
    for y in range(h):
        for x in range(w):
            if not mask[y, x] or seen[y, x]:
                continue
            queue = deque([(y, x)])
            seen[y, x] = True
            pixels = []
            while queue:
                cy, cx = queue.popleft()
                pixels.append((cy, cx))
                for ny in range(cy - 1, cy + 2):
                    for nx in range(cx - 1, cx + 2):
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            queue.append((ny, nx))
            ys = np.array([p[0] for p in pixels])
            xs = np.array([p[1] for p in pixels])
            result.append({"x0": xs.min(), "x1": xs.max(), "y0": ys.min(), "y1": ys.max(),
                           "cx": xs.mean(), "cy": ys.mean(), "n": len(pixels), "pixels": pixels})
    return result


def split_lines(letters):
    """Chains letters left to right into lines; returns lists ordered top line first."""
    letters = sorted(letters, key=lambda c: c["cx"])
    lines = []
    for c in letters:
        best, best_d = None, None
        for line in lines:
            last = line[-1]
            if c["cx"] - last["cx"] > 30:
                continue
            d = abs(c["cy"] - last["cy"]) if c["n"] > 6 else abs(c["y1"] - last["y1"])
            if d <= 4.5 and (best_d is None or d < best_d):
                best, best_d = line, d
        if best is None:
            lines.append([c])
        else:
            best.append(c)
    lines = [l for l in lines if sum(c["n"] for c in l) > 15]
    lines.sort(key=lambda l: l[0]["cx"])
    merged = []
    for line in lines:
        # A wide gap between words breaks the chain; rejoin pieces that continue another line's height.
        for prev in merged:
            if line[0]["cx"] > prev[-1]["cx"] and abs(line[0]["y1"] - prev[-1]["y1"]) <= 7:
                prev.extend(line)
                break
        else:
            merged.append(line)
    merged.sort(key=lambda l: np.mean([c["cy"] for c in l]))
    return merged


class Baseline:
    """Smooth baseline through the letter bottoms (locally weighted linear fit).

    The smoothing keeps the word-scale waves of the handwriting but drops the letter-scale jitter. Letters tilt only
    with the overall run of the line (a much wider fit), so a wave moves them up and down without slanting them.
    """

    SIGMA = 14.0
    SLANT_SIGMA = 40.0

    def __init__(self, line):
        big = [c for c in line if c["n"] > 6] or line
        self.xs = np.array([c["cx"] for c in big], dtype=float)
        self.ys = np.array([c["y1"] + 0.5 for c in big], dtype=float)
        self.x0 = min(c["x0"] for c in line)
        self.x1 = max(c["x1"] for c in line)
        self.weights = np.ones_like(self.xs)
        if len(self.xs) >= 4:
            residual = np.abs(self.ys - np.array([self.y(x) for x in self.xs]))
            self.weights = np.where(residual > 1.6, 0.05, 1.0)
        self.cap = float(np.median([c["y1"] - c["y0"] + 1 for c in big]))

    def _fit(self, x, sigma=None):
        sigma = sigma or self.SIGMA
        w = self.weights * np.exp(-((self.xs - x) ** 2) / (2 * sigma ** 2)) + 1e-9
        if len(self.xs) == 1:
            return float(self.ys[0]), 0.0
        mx = np.sum(w * self.xs) / np.sum(w)
        my = np.sum(w * self.ys) / np.sum(w)
        var = np.sum(w * (self.xs - mx) ** 2)
        k = np.sum(w * (self.xs - mx) * (self.ys - my)) / var if var > 1e-6 else 0.0
        return float(my + k * (x - mx)), float(k)

    EASE = 8.0
    offset = 0.0

    def y(self, x):
        # Past the last letter the line keeps its slope for a few pixels and then levels out, so a longer Russian
        # line neither dives into the next line nor climbs out of the sprite.
        lo, hi = self.xs.min(), self.xs.max()
        edge = min(max(x, lo), hi)
        y_edge, k = self._fit(edge)
        d = x - edge
        eased = math.copysign(self.EASE * (1 - math.exp(-abs(d) / self.EASE)), d)
        return y_edge + k * eased + self.offset

    def slant(self, x):
        """Slope of the overall run of the line at x, used to tilt the letters."""
        edge = min(max(x, self.xs.min()), self.xs.max())
        return self._fit(edge, self.SLANT_SIGMA)[1]

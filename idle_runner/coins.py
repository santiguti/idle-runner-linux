"""Read the coin counter (top centre) right after an ascension. Not in the original.

The user's rule: start buying as soon as the counter reaches 6 coins (the sword's first level).
After an ascension it counts up from "0" in steps like 3, 7.5, 11.3 (measured 2026-10-22), so it is
read as a plain number; after an Ultra Ascension it climbs past 1,000 within seconds, with a thousands
comma. Anything else (a suffix like "Dd", a banner over it) reads as None.
"""
import numpy as np

from idle_runner.coin_glyphs import GLYPHS
from idle_runner.game import Game

TEMPLATES = [(label, np.array([[c == "#" for c in row] for row in rows]))
             for label, variants in GLYPHS.items() for rows in variants]
MIN_MATCH = 0.9  # share of equal pixels with the best template; measured matches score 1.0


def read_coins(game: Game) -> float | None:
    """The counter's value when it shows a plain number (digits and a decimal point), else None."""
    white = (game.grab(488, 69, 807, 97) == 255).all(axis=2)  # the digits' white fill
    columns = white.any(axis=0)
    text = ""
    x = 0
    while x < len(columns):
        if not columns[x]:
            x += 1
            continue
        start = x
        while x < len(columns) and columns[x]:
            x += 1
        glyph = white[:, start:x]
        rows = np.nonzero(glyph.any(axis=1))[0]
        glyph = glyph[rows.min():rows.max() + 1]
        if glyph.shape[0] <= 8 and glyph.shape[1] <= 8 and rows.min() >= 14:
            text += "."  # a small square on the baseline
            continue
        label = _classify(glyph)
        if label == ",":  # the thousands separator ("1,251", after the first Ultra Ascension)
            continue
        if label is None or not label.isdigit():
            return None
        text += label
    try:
        return float(text)
    except ValueError:  # empty, or several "dots" (e.g. bits of a banner)
        return None


def _classify(glyph: np.ndarray) -> str | None:
    best, best_score = None, 0.0
    for label, template in TEMPLATES:
        if template.shape[0] != glyph.shape[0] or abs(template.shape[1] - glyph.shape[1]) > 2:
            continue
        width = max(template.shape[1], glyph.shape[1])
        a = np.zeros((glyph.shape[0], width), dtype=bool)
        a[:, :glyph.shape[1]] = glyph
        b = np.zeros((glyph.shape[0], width), dtype=bool)
        b[:, :template.shape[1]] = template
        score = float((a == b).mean())
        if score > best_score:
            best, best_score = label, score
    return best if best_score >= MIN_MATCH else None

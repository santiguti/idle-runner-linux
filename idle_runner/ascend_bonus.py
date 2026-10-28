"""Read the Ascend button's "+X% CpS bonus." while the ascension panel is open. Not in the original.

The % is SP gained by ascending / SP earned so far, the wiki's measure of when to ascend. The button's lines are SP gained, then CpS bonus (then Souls bonus before the Ultra
Ascension), in pure white (the numbers gold once "Recommended"); the button's twinkling stars never are
(measured 2026-10-23). The game shrinks
the font to fit the button (14-16 px tall), so glyphs are compared scaled to one size.
"""
import re

import numpy as np

from idle_runner.bonus_glyphs import GLYPHS
from idle_runner.game import Game

H, W = 14, 10  # every glyph is compared at this size
# Leave-one-out on the 2026-10-23 samples (each shape read using only the others): the right character
# scored >= 0.70 and beat every other by >= 0.089.
MIN_SCORE = 0.6
MIN_MARGIN = 0.03


def _scaled(glyph: np.ndarray) -> np.ndarray:
    """Area-average onto an H x W grid, zero mean, unit length: a dot product is then a correlation."""
    big = np.kron(glyph.astype(float), np.ones((H, W)))
    v = big.reshape(H, glyph.shape[0], W, glyph.shape[1]).mean(axis=(1, 3))
    v -= v.mean()
    return v / (np.linalg.norm(v) or 1)


TEMPLATES = [(label, len(rows[0]) / len(rows), _scaled(np.array([[c == "#" for c in row] for row in rows])))
             for label, variants in GLYPHS.items() for rows in variants]


def read_ascend_bonus(game: Game) -> float | None:
    """The CpS bonus %; 0.0 when the button shows "+0" (nothing to claim); None if it can't be read."""
    pixels = game.grab(88, 471, 457, 630)  # client x 80-449, y 440-599
    # The numbers turn gold (FFC14D) while the game tags the button "Recommended" (2026-10-28, from
    # +53.9%); the stars never are (none in 61 samples and 27 black-box frames of the open panel).
    white = (pixels == 255).all(axis=2) | (pixels == (0xFF, 0xC1, 0x4D)).all(axis=2)
    # The title (client y 450-465) starts at x 158 with Ultra Ascend beside Ascend, at 278 without it;
    # Ascend's text is then within client x 92-330 or 200-440.
    left, right = (12, 250) if white[10:26, :170].any() else (120, 360)
    lines = _lines(white[30:, left:right])
    if len(lines) == 1 and re.match(r"\+0(?![\d.])", _text(lines[0])):
        return 0.0
    match = re.match(r"\+(\d+(?:\.\d)?)%", _text(lines[1])) if len(lines) >= 2 else None
    return float(match[1]) if match else None


def _lines(white: np.ndarray) -> list[np.ndarray]:
    rows = white.any(axis=1)
    lines, y = [], 0
    while y < len(rows):
        if rows[y]:
            start = y
            while y < len(rows) and rows[y]:
                y += 1
            lines.append(white[start:y])
        y += 1
    return lines


def _text(line: np.ndarray) -> str:
    """The line's characters up to the first one that isn't "+", a digit, "." or "%"."""
    columns = line.any(axis=0)
    text, x = "", 0
    while x < len(columns):
        if not columns[x]:
            x += 1
            continue
        start = x
        while x < len(columns) and columns[x]:
            x += 1
        glyph = line[:, start:x]
        rows = np.nonzero(glyph.any(axis=1))[0]
        glyph = glyph[rows.min():rows.max() + 1]
        if glyph.shape[0] <= 5 and glyph.shape[1] <= 5 and rows.min() >= len(line) // 2:
            text += "."  # a small square on the baseline
            continue
        label = _classify(glyph)
        if label is None:
            break
        text += label
    return text


def _classify(glyph: np.ndarray) -> str | None:
    aspect, v = glyph.shape[1] / glyph.shape[0], _scaled(glyph)
    best: dict[str, float] = {}
    for label, template_aspect, template in TEMPLATES:
        if 0.75 < aspect / template_aspect < 1.33:  # keeps "1" apart from the wide characters
            best[label] = max(best.get(label, -1.0), float((v * template).sum()))
    ranked = sorted(best.items(), key=lambda kv: -kv[1]) + [("", -1.0)] * 2
    (label, score), (_, second) = ranked[:2]
    return label if score >= MIN_SCORE and score - second >= MIN_MARGIN else None

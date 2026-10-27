"""Draw the window's pixel-art icon and logo into idle_runner/ui/assets/ (run once after changing them):

    .venv/bin/python packaging/make_icons.py

A downward sword, like the game's Slayer Points icon, on a plum tile in a copper frame; the logo adds
"Idle Runner" in a hand-made 5x7 pixel font, the way the original's labels were pixel images.
"""
from pathlib import Path

import numpy as np

from idle_runner.png import write_png
from idle_runner.ui.theme import PALETTE

ASSETS = Path(__file__).resolve().parents[1] / "idle_runner" / "ui" / "assets"
SWORD = [  # 16x16: B blade, E blade edge, G guard, H handle, P pommel, F frame
    "FFFFFFFFFFFFFFFF",
    "F..............F",
    "F......PP......F",
    "F......HH......F",
    "F......HH......F",
    "F...GGGGGGGG...F",
    "F...GGGGGGGG...F",
    "F......BE......F",
    "F......BE......F",
    "F......BE......F",
    "F......BE......F",
    "F......BE......F",
    "F......BE......F",
    "F.......E......F",
    "F..............F",
    "FFFFFFFFFFFFFFFF",
]
GLYPHS = {
    "I": ["###", ".#.", ".#.", ".#.", ".#.", ".#.", "###"],
    "d": ["....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"],
    "l": ["##.", ".#.", ".#.", ".#.", ".#.", ".#.", "###"],
    "e": [".....", ".....", ".###.", "#...#", "#####", "#....", ".####"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "u": [".....", ".....", "#...#", "#...#", "#...#", "#...#", ".####"],
    "n": [".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"],
    "r": [".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."],
    " ": ["..", "..", "..", "..", "..", "..", ".."],
}


def rgb(hex_colour: str) -> np.ndarray:
    return np.array([int(hex_colour[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.uint8)


def sword(scale: int, background: str) -> np.ndarray:
    colours = {".": PALETTE.raised, "F": PALETTE.frame, "B": "#E6E1EC", "E": "#9C93A8", "G": PALETTE.gold,
               "H": "#7A4A2E", "P": PALETTE.accent}
    tile = np.array([[rgb(colours[c]) for c in row] for row in SWORD])
    tile = tile.repeat(scale, axis=0).repeat(scale, axis=1)
    out = np.empty_like(tile)
    out[:] = rgb(background)
    out[:] = tile
    return out


def text(word: str, scale: int, background: str) -> np.ndarray:
    columns = []
    for char in word:
        glyph = GLYPHS[char]
        columns += [[row[x] for row in glyph] for x in range(len(glyph[0]))] + [["."] * 7]
    mask = np.array(columns).T == "#"
    height, width = mask.shape
    out = np.empty((height + 1, width + 1, 3), dtype=np.uint8)
    out[:] = rgb(background)
    out[1:, 1:][mask] = rgb("#000000")  # a hard shadow, like the game's outlined text
    out[:-1, :-1][mask] = rgb(PALETTE.text)
    return out.repeat(scale, axis=0).repeat(scale, axis=1)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    write_png(ASSETS / "icon.png", sword(16, PALETTE.bg))  # 256x256
    mark, label = sword(3, PALETTE.bg), text("Idle Runner", 3, PALETTE.bg)
    gap = np.empty((48, 12, 3), dtype=np.uint8)
    gap[:] = rgb(PALETTE.bg)
    padded = np.empty((48, label.shape[1], 3), dtype=np.uint8)
    padded[:] = rgb(PALETTE.bg)
    top = (48 - label.shape[0]) // 2
    padded[top:top + label.shape[0]] = label
    write_png(ASSETS / "logo.png", np.hstack([mark, gap, padded]))


if __name__ == "__main__":
    main()

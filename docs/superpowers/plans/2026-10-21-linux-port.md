# Idle Runner Linux Port — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port Devil4ngle's AutoIt "Idle Runner" (Idle Slayer bot) to Linux as a Python package that drives the native Linux build of the game through X11/XWayland, keeping every original feature and adding much richer logging so the weak parts (minigames) can be debugged and improved later.

**Architecture:** One X11 backend (python-xlib: window lookup, `XGetImage` capture, XTEST input) sits behind an AutoIt-compatible `Game` facade. `Game` accepts the original AutoIt coordinates verbatim and converts them with a measured window-frame offset. Feature modules are function-by-function ports of the AutoIt code on top of `Game`. A `Runner` reproduces the original `Main()` loop. Everything logs to a human log with millisecond timestamps and to `events.jsonl`, with PNG frame dumps on minigames, safety-net timeouts and crashes.

**Tech Stack:** Python ≥ 3.12 (machine: 3.14.8), python-xlib, numpy, stdlib (`tomllib`, `json`, `logging`, `zlib`, `threading`), pytest.

**Spec:** the "Design" section below (decisions taken with the user on 2026-10-21) plus the original AutoIt source at `/home/santi/Downloads/Idle_Slayer_Script` (read-only reference: `Idle Runner.au3`, `Libraries/*.au3`).

---

## Design

### Decisions (from the user)
- New standalone repo: `/home/santi/Downloads/idle-runner-linux`.
- Linux only, for now. Everything X11-specific lives in `idle_runner/x11.py`.
- Controlled from the terminal with a TOML config file; no GUI. Ctrl+C stops the bot.
- Full port of what the AutoIt project does. The user knows the original has bugs and that its minigames are unreliable, so **heavy logging is a first-class requirement**.

### Facts verified on this machine (2026-10-21)
- KDE Plasma 6.7 on Wayland. Idle Slayer is the **native Linux** Unity 6 build (`6000.3.14f1`) and selects `window backend: x11`, so its window is an XWayland window.
- Steam runs the game inside the "Steam Linux Runtime" container, where Firebase can't load `libsecret` and the game boots to a black screen. Workaround in use: Steam launch option `"/home/santi/.local/share/Steam/steamapps/common/Idle Slayer/Idle Slayer.x86_64" # %command%`.
- python-xlib can read XWayland windows: depth 24, 4 bytes per pixel, BGRX order. Minimized/unmapped windows raise `BadMatch`. `_NET_ACTIVE_WINDOW` stops pointing at X windows when a Wayland window has focus. XTEST is available.
- Not yet verified (this is Task 1's go/no-go): that the game window itself captures correctly, that XTEST input reaches the game, the exact frame offset, and colour fidelity.

### Coordinates
The AutoIt script uses `Opt("PixelCoordMode", 0)` and `Opt("MouseCoordMode", 0)`: every coordinate is relative to the game window **including the Windows title bar and borders**. Evidence: it checks `y = 752` inside a 720-px-tall client area. The port keeps every AutoIt number verbatim and subtracts a constant offset (`offset_x`, `offset_y`, expected ≈ (8, 31)). Task 1 measures the offset. This keeps every line traceable to the original.

### Deliberate deviations from the original
1. **No focus stealing.** Input is only sent while the game window is focused; otherwise `Game` raises `GameUnavailable` and the current routine aborts. Alt-tabbing away pauses the bot. This replaces the Home pause hotkey, `WinActivate`, `ControlFocus` and the 30-minute refocus.
2. **No global hotkeys** (Home, Shift+Esc, Ctrl+Shift+B). Wayland doesn't offer free global hotkeys. Ctrl+C in the terminal stops the bot.
3. **Read-only TOML config.** The one-shot crafts (Dimensional and Bidimensional staff) apply once per run instead of unticking a checkbox. The portal rotation starts from `circle_portals_count` on every run instead of being persisted.
4. **Safety nets.** Every loop that can spin forever in AutoIt gets a deadline (`STUCK_MS` = 60 s; 5 min for the chest-hunt end screen; 3 min for "do nothing" bonus stages). Hitting one logs a `stuck` event, saves a frame and moves on.
5. **The jumper pauses immediately.** The original second process noticed pauses up to 700 ms late, and kept jumping while menus opened.
6. **Obvious bugs fixed:**
   - Ascending Heights' right-edge clamp (`$iLeft = 900` should set `$iRight`).
   - Chest-hunt stats: they are now counted from events, so the "Chesthunt" vs "Chesthunt Started" mismatch is gone.
   - Clicks outside the window are refused and logged. In the original, a missing life saver clicked at (33, -23).
7. **Knight boss stays disabled.** The original returns right after logging, so its dead code is not ported.
8. **Extra logging:**
   - Every routine's start, end, duration and abort.
   - Purchase counts per buy pass.
   - Ascensions (never logged in the original).
   - Per-chest results.
   - Sync timeouts in bonus stages.
   - PNG frames at minigame start and end, timeouts and crashes.
   - Optional DEBUG trace of every pixel search.
9. **`find_until` sleeps 1 ms per poll.** AutoIt's version was a busy loop.
10. **`python -m idle_runner stats`** replaces the Log tab.

### Known issues ported as-is (to fix later, with log data)
- `CloseAll()` sleeps 2 s on every slow tick, blinding the fast checks.
- `AutoAscend()` checks the pixel at y = 480 but clicks y = 600.
- When the two timers coincide, auto-buy runs right before auto-ascend (a wasted buy).
- The buy-round counter (`$iAutoBuyLoopAmount`) isn't reset before the purchase that follows an ascension. Task 13 fixes this.

## Global Constraints
- Always use `./.venv/bin/python` / `./.venv/bin/pip`. Never the global interpreter. Dependencies are declared in `pyproject.toml` only.
- Runtime dependencies: `numpy`, `python-xlib`. Dev dependency: `pytest`. Nothing else.
- Strong type hints on every function in `idle_runner/`.
- pytest tests live in `tests/`, mirroring `idle_runner/` (e.g. `idle_runner/minigames/chest_hunt.py` → `tests/minigames/test_chest_hunt.py`).
- Code, comments, docstrings and event text are in English. Event names that exist in the original keep its exact text (e.g. `"Silver Box Collected"`, `"MegaHorde Rage"`).
- Coordinates, colours and sleeps are copied verbatim from the AutoIt source. AutoIt coordinates are passed to `Game` unchanged.
- No input may reach a window other than the game: `Game` refuses input while the game isn't focused and refuses clicks outside its client area.
- Commit messages end with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus
1. **The user alt-tabs in the middle of a routine.** No click or key may land on another window. The routine aborts, is logged, and the bot resumes when focus returns. → Task 7 `test_focus_loss_mid_routine_aborts_without_more_input`.
2. **The game window isn't 1280x720** (KDE scaling, maximized window). Every pixel check would fail silently; there must be a loud warning at start. → Task 7 `test_run_warns_on_wrong_window_size_and_releases_keys_on_ctrl_c`.
3. **Ctrl+C while a key or button is held** (bonus-stage holds, Ascending Heights' 15 s `d`). The key would stay stuck in X; everything must be released on exit. → Task 3 `test_release_all_releases_keys_and_button` + Task 7 run test.
4. **The jumper thread hits an unexpected error.** It would silently stop jumping; it must log the error and keep running. → Task 5 `test_repeater_logs_errors_and_keeps_running`.
5. **A typo or wrong type in `config.toml`.** It would silently fall back to a default; it must fail with an error naming the key. → Task 4 `test_unknown_key_is_an_error`, `test_wrong_type_is_an_error`.

## File Structure
```
idle-runner-linux/
  pyproject.toml           deps, pytest config
  README.md                setup, calibration, running, logs, differences
  LICENSE                  MIT (original copyright kept)
  config.example.toml      every setting with its default
  idle_runner/
    __init__.py
    __main__.py            CLI: probe | stats | run
    x11.py                 X11Backend + GameUnavailable (only X11 code)
    png.py                 stdlib PNG writer for frame dumps
    log.py                 setup_logging, event()
    stats.py               summarize events.jsonl
    game.py                Game facade: AutoIt coords, pixel_search, input, routine(), stuck()
    config.py              Settings + load_settings (TOML)
    repeater.py            Repeater thread (jumper, Victor's shooter)
    shop.py                AutoUpgrade/BuyUpgrade/BuyEquipment/ClaimQuests/AutoAscend
    actions.py             CloseAll, soul bonus, BuyTempItem, CollectMinion
    portals.py             CirclePortals
    runner.py              Main() loop
    minigames/
      __init__.py
      common.py            Slider, slide_until_gone
      chest_hunt.py
      bonus_stage.py
      boss.py              Victor (+ disabled Knight)
      ascending_heights.py
  tests/                   mirrors idle_runner/; fakes.py + conftest.py shared
  docs/superpowers/plans/2026-10-21-linux-port.md   (this file)
```

---

### Task 1: Scaffold, X11 backend and `probe` (live go/no-go)

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `LICENSE`, `README.md`, `idle_runner/__init__.py`, `idle_runner/png.py`, `idle_runner/x11.py`, `idle_runner/__main__.py`, `tests/__init__.py`, `tests/test_png.py`

**Interfaces:**
- Produces:
  - `idle_runner.x11.GameUnavailable(Exception)`
  - `X11Backend(window_name: str)` with:
    - `.window_id: int`
    - `size() -> tuple[int, int]`
    - `origin() -> tuple[int, int]`
    - `is_active() -> bool`
    - `grab(x, y, w, h) -> np.ndarray`, an `(h, w, 3)` uint8 RGB array in client coordinates
    - `move(x, y)`
    - `button(button: int, down: bool)`
    - `key(name: str, down: bool)`
    - `now_ms() -> float`
    - `sleep_ms(ms: float)`
  - `idle_runner.png.write_png(path: Path, rgb: np.ndarray) -> None`

- [ ] **Step 1: Create the repo and the venv**

```bash
cd /home/santi/Downloads/idle-runner-linux
git init
python3 -m venv .venv
mkdir -p idle_runner tests
```

- [ ] **Step 2: Write the project files**

`pyproject.toml`:
```toml
[project]
name = "idle-runner-linux"
version = "0.1.0"
description = "Linux port of Devil4ngle's Idle Runner, a pixel-based Idle Slayer bot"
requires-python = ">=3.12"
dependencies = [
    "numpy>=2.0",
    "python-xlib>=0.33",
]

[project.optional-dependencies]
dev = ["pytest>=8.3"]

[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["idle_runner*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

`.gitignore`:
```
.venv/
__pycache__/
*.egg-info/
.pytest_cache/
logs/
config.toml
probe.png
```

`LICENSE`:
```
MIT License

Copyright (c) 2023 Devil4ngle
Copyright (c) 2026 santiguti

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

`idle_runner/__init__.py`:
```python
"""Linux port of Devil4ngle's Idle Runner (AutoIt) for Idle Slayer."""
```

`tests/__init__.py`: empty file.

- [ ] **Step 3: Install**

Run: `.venv/bin/pip install -e '.[dev]'`
Expected: ends with `Successfully installed ... idle-runner-linux-0.1.0 ... numpy-... python-xlib-... pytest-...`

- [ ] **Step 4: Write the failing PNG test**

`tests/test_png.py`:
```python
import struct
import zlib

import numpy as np

from idle_runner.png import write_png


def test_write_png_roundtrip_from_a_reversed_view(tmp_path) -> None:
    bgr = np.array([[[0, 0, 255], [0, 255, 0], [255, 0, 0]],
                    [[3, 2, 1], [6, 5, 4], [9, 8, 7]]], dtype=np.uint8)
    rgb = bgr[:, :, ::-1]  # a non-contiguous view, like X11Backend.grab() returns
    path = tmp_path / "x.png"

    write_png(path, rgb)

    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">IIBB", data[16:26]) == (3, 2, 8, 2)  # width, height, bit depth, RGB
    idat_length = struct.unpack(">I", data[33:37])[0]
    raw = zlib.decompress(data[41:41 + idat_length])
    expected = np.ascontiguousarray(rgb)
    assert raw == b"\x00" + expected[0].tobytes() + b"\x00" + expected[1].tobytes()
```

- [ ] **Step 5: Run it to see it fail**

Run: `.venv/bin/python -m pytest tests/test_png.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'idle_runner.png'`

- [ ] **Step 6: Implement `png.py`**

`idle_runner/png.py`:
```python
"""Minimal PNG writer (stdlib only) for debug frame dumps."""
import struct
import zlib
from pathlib import Path

import numpy as np


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))


def write_png(path: Path, rgb: np.ndarray) -> None:
    """Write an (h, w, 3) uint8 RGB array as an 8-bit truecolor PNG."""
    height, width, _ = rgb.shape
    # Each scanline starts with filter type 0 (none).
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header) + _chunk(b"IDAT", zlib.compress(raw, 6)) + _chunk(b"IEND", b"")
    path.write_bytes(png)
```

- [ ] **Step 7: Run the test to see it pass**

Run: `.venv/bin/python -m pytest tests/test_png.py -v`
Expected: `1 passed`

- [ ] **Step 8: Write the X11 backend**

`idle_runner/x11.py`:
```python
"""X11 backend: finds the Idle Slayer window, captures its pixels and injects input via XTEST.

Coordinates here are client-area coordinates of the game window (0, 0 = top-left pixel of the
1280x720 game). The AutoIt window-frame offset is handled one level up, in game.py.
"""
import threading
import time

import numpy as np
from Xlib import X, XK, display, error
from Xlib.ext import xtest
from Xlib.xobject.drawable import Window


class GameUnavailable(Exception):
    """The game window can't be used right now (not focused, minimized or gone)."""


class X11Backend:
    def __init__(self, window_name: str) -> None:
        # python-xlib connections must not be used from two threads at once (the jumper
        # thread and the main loop both send input), so every request holds this lock.
        self._lock = threading.RLock()
        self._display = display.Display()
        if self._display.query_extension("XTEST") is None:
            raise RuntimeError("the X server has no XTEST extension; input injection is impossible")
        self._root = self._display.screen().root
        self._active_atom = self._display.intern_atom("_NET_ACTIVE_WINDOW")
        self._window = self._find_window(window_name)

    @property
    def window_id(self) -> int:
        return self._window.id

    def _find_window(self, name: str) -> Window:
        clients = self._root.get_full_property(self._display.intern_atom("_NET_CLIENT_LIST"), X.AnyPropertyType)
        for window_id in clients.value if clients else []:
            window = self._display.create_resource_object("window", window_id)
            if self._window_name(window) == name:
                return window
        raise GameUnavailable(f"no X11 window named {name!r}; is the game running?")

    def _window_name(self, window: Window) -> str:
        utf8_name = window.get_full_property(
            self._display.intern_atom("_NET_WM_NAME"), self._display.intern_atom("UTF8_STRING"))
        if utf8_name:
            return utf8_name.value.decode("utf-8", "replace")
        name = window.get_wm_name()
        return name.decode("latin-1") if isinstance(name, bytes) else (name or "")

    def size(self) -> tuple[int, int]:
        with self._lock:
            geometry = self._window.get_geometry()
            return geometry.width, geometry.height

    def origin(self) -> tuple[int, int]:
        """Top-left of the client area in root (screen) coordinates."""
        with self._lock:
            reply = self._root.translate_coords(self._window, 0, 0)
            return reply.x, reply.y

    def is_active(self) -> bool:
        with self._lock:
            prop = self._root.get_full_property(self._active_atom, X.AnyPropertyType)
            return bool(prop) and len(prop.value) > 0 and prop.value[0] == self._window.id

    def grab(self, x: int, y: int, w: int, h: int) -> np.ndarray:
        """RGB pixels (h, w, 3) of a client-area rectangle."""
        with self._lock:
            try:
                image = self._window.get_image(x, y, w, h, X.ZPixmap, 0xFFFFFFFF)
            except (error.BadMatch, error.BadWindow, error.BadDrawable) as exc:
                raise GameUnavailable(f"cannot capture the game window ({type(exc).__name__})") from exc
        bgrx = np.frombuffer(image.data, dtype=np.uint8).reshape(h, w, 4)
        return bgrx[:, :, 2::-1]

    def move(self, x: int, y: int) -> None:
        origin_x, origin_y = self.origin()
        with self._lock:
            xtest.fake_input(self._display, X.MotionNotify, x=origin_x + x, y=origin_y + y)
            self._display.sync()

    def button(self, button: int, down: bool) -> None:
        with self._lock:
            xtest.fake_input(self._display, X.ButtonPress if down else X.ButtonRelease, button)
            self._display.sync()

    def key(self, name: str, down: bool) -> None:
        with self._lock:
            keycode = self._display.keysym_to_keycode(XK.string_to_keysym(name))
            if not keycode:
                raise ValueError(f"unknown key {name!r}")
            xtest.fake_input(self._display, X.KeyPress if down else X.KeyRelease, keycode)
            self._display.sync()

    def now_ms(self) -> float:
        return time.monotonic() * 1000

    def sleep_ms(self, ms: float) -> None:
        if ms > 0:
            time.sleep(ms / 1000)
```

- [ ] **Step 9: Write the CLI with `probe`**

`idle_runner/__main__.py`:
```python
"""Command line entry point: python -m idle_runner <command>."""
import argparse
import sys
import time
from pathlib import Path

import numpy as np

from idle_runner.png import write_png
from idle_runner.x11 import GameUnavailable, X11Backend


def run_probe(args: argparse.Namespace) -> int:
    """Calibration/debugging: window info, colours, timings, a screenshot and manual input tests."""
    backend = X11Backend(args.name)
    if args.delay:
        print(f"waiting {args.delay:g} s: focus the game window now...")
        time.sleep(args.delay)
    width, height = backend.size()
    origin_x, origin_y = backend.origin()
    print(f"window 0x{backend.window_id:x}: client {width}x{height} at screen ({origin_x}, {origin_y}), "
          f"focused={backend.is_active()}")

    if (args.key or args.click) and not backend.is_active():
        print("error: refusing to send input while the game is not focused (use --delay)", file=sys.stderr)
        return 1
    if args.key:
        backend.key(args.key, True)
        time.sleep(0.05)
        backend.key(args.key, False)
        print(f"tapped {args.key}")
    if args.click:
        x, y = args.click
        backend.move(x, y)
        backend.button(1, True)
        time.sleep(0.05)
        backend.button(1, False)
        print(f"clicked client ({x}, {y})")
    if args.pixel:
        x, y = args.pixel
        r, g, b = (int(c) for c in backend.grab(x, y, 1, 1)[0, 0])
        print(f"pixel client ({x}, {y}) = 0x{r:02X}{g:02X}{b:02X}")

    start = time.perf_counter()
    for _ in range(100):
        backend.grab(width // 2, height // 2, 1, 1)
    one_pixel_ms = (time.perf_counter() - start) * 10
    start = time.perf_counter()
    for _ in range(10):
        frame = backend.grab(0, 0, width, height)
    full_frame_ms = (time.perf_counter() - start) * 100
    print(f"grab timings: 1 px {one_pixel_ms:.2f} ms, full frame {full_frame_ms:.1f} ms")

    if args.find is not None:
        target = np.array([(args.find >> 16) & 0xFF, (args.find >> 8) & 0xFF, args.find & 0xFF], dtype=np.uint8)
        ys, xs = np.nonzero((frame == target).all(axis=2))
        first = list(zip(xs[:20].tolist(), ys[:20].tolist()))
        print(f"0x{args.find:06X}: {len(xs)} client pixels, first: {first}")

    write_png(args.out, frame)
    print(f"saved {args.out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m idle_runner")
    sub = parser.add_subparsers(dest="command", required=True)

    probe = sub.add_parser("probe", help="inspect the game window (calibration and debugging)")
    probe.add_argument("--name", default="Idle Slayer", help="X11 window title")
    probe.add_argument("--delay", type=float, default=0, help="seconds to wait first (time to focus the game)")
    probe.add_argument("--out", type=Path, default=Path("probe.png"), help="where to save the screenshot")
    probe.add_argument("--pixel", type=int, nargs=2, metavar=("X", "Y"), help="print the colour at client X Y")
    probe.add_argument("--find", type=lambda s: int(s, 16), metavar="RRGGBB",
                       help="list client coordinates with exactly this colour")
    probe.add_argument("--key", help="tap this key (X keysym name, e.g. Up)")
    probe.add_argument("--click", type=int, nargs=2, metavar=("X", "Y"), help="left-click at client X Y")

    args = parser.parse_args(argv)
    try:
        if args.command == "probe":
            return run_probe(args)
    except GameUnavailable as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 10: Live check (needs the user)**

Ask the user to launch Idle Slayer (windowed 1280x720, English, on the normal running screen) and keep it visible. Then run each command and record the output.

a. Window and capture. Run `.venv/bin/python -m idle_runner probe`. Expected: `client 1280x720`, `focused=False` (the terminal has focus), `grab timings: ...`, `saved probe.png`. Open `probe.png` and confirm it shows the game, not a black image.

b. Frame offset and colour fidelity. Run `.venv/bin/python -m idle_runner probe --find 830399` and `.venv/bin/python -m idle_runner probe --find 290130`. These are the portal button colours the original checks at AutoIt (1180, 166); portals must be unlocked. A match at client (cx, cy) gives offset = (1180 − cx, 166 − cy); (8, 31) is expected. An exact match also proves colours are identical, so `color_tolerance` = 0.
   - Fallback if portals are locked: locate the centre of the shop button in `probe.png`. The original clicks it at AutoIt (1163, 655), so offset ≈ (1163 − cx, 655 − cy).
   - Then check the colour by hand with `probe --pixel CX CY` on any element whose AutoIt colour is known.

c. Focus detection. Run `.venv/bin/python -m idle_runner probe --delay 3` and click the game within 3 s. Expected: `focused=True`.

d. Keyboard. Run `.venv/bin/python -m idle_runner probe --delay 3 --key Up` and focus the game. Expected: the character jumps.

e. Mouse. Run `.venv/bin/python -m idle_runner probe --delay 3 --click <1163-ox> <655-oy>`. Expected: the shop opens. Then run `--click <1244-ox> <712-oy>`. Expected: it closes.
   - If KDE shows a "remote control / input" permission dialog, allow it and remember the choice.

**Go/no-go.** If the capture is black, the size isn't 1280x720, or keys or clicks have no effect: **stop and report to the user** with the exact output. Fallbacks to discuss are uinput (python-evdev) for input and gamescope for capture. Do not continue to Task 2.

- [ ] **Step 11: Write the README with the calibration results**

`README.md` (fill the bracketed values with what Step 10 measured):
````markdown
# Idle Runner (Linux)

Linux port of [Devil4ngle's Idle Runner](https://github.com/Devil4ngle/Idle_Slayer_Script), a pixel-based bot for the Steam game Idle Slayer. Like the AutoIt original, it only looks at the game window's pixels and sends keyboard/mouse input; it doesn't read or modify the game.

## Requirements
- The native Linux build of Idle Slayer on X11/XWayland. `~/.config/unity3d/Pablo Leban/Idle Slayer/Player.log` must say `Selected window backend: x11`. Don't launch it with `-force-wayland`.
- If the game boots to a black screen (Steam's runtime container lacks `libsecret`, so Firebase fails), set this Steam launch option:
  `"<steam library>/steamapps/common/Idle Slayer/Idle Slayer.x86_64" # %command%`
- In-game settings (same as the original):
  - Windowed 1280x720, English.
  - Jump = Up arrow, boost = Right arrow.
  - Custom cursor disabled.
  - Portal dialogue disabled.
  - Rounded bulk enabled.
  - Hide locked quest rewards enabled.
  - Don't buy the Vertical Magnet.
- Python ≥ 3.12.

## Setup
```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest
```

## Calibration and debugging: `probe`
```bash
.venv/bin/python -m idle_runner probe                     # window info, grab timings, probe.png
.venv/bin/python -m idle_runner probe --find 830399       # where is this exact colour?
.venv/bin/python -m idle_runner probe --pixel 640 360     # colour at a client pixel
.venv/bin/python -m idle_runner probe --delay 3 --key Up  # input test (focus the game within 3 s)
```

### Measured on the development machine (2026-10-21)
- Window: [1280x720], frame offset: [(8, 31)], colour tolerance needed: [0]
- Grab timings: 1 px [x.xx] ms, full frame [xx.x] ms
````

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "feat: scaffold, X11 backend and probe command" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Logging, events and `stats`

**Files:**
- Create: `idle_runner/log.py`, `idle_runner/stats.py`, `tests/conftest.py`, `tests/test_log.py`, `tests/test_stats.py`
- Modify: `idle_runner/__main__.py`

**Interfaces:**
- Produces:
  - `idle_runner.log.log`, the `logging.Logger` named `"idle_runner"`
  - `setup_logging(log_dir: Path, level: str = "INFO") -> None`
  - `event(name: str, **fields: object) -> None`
  - `idle_runner.stats.summarize(events_path: Path) -> list[str]`
  - Test fixtures: `logs` (autouse, returns the log `Path`), `events() -> list[dict]`, `event_names() -> list[str]`

- [ ] **Step 1: Write the shared fixtures**

`tests/conftest.py`:
```python
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from idle_runner.log import setup_logging


@pytest.fixture(autouse=True)
def logs(tmp_path: Path) -> Path:
    """Every test logs (at DEBUG) into its own temporary directory."""
    log_dir = tmp_path / "logs"
    setup_logging(log_dir, "DEBUG")
    return log_dir


@pytest.fixture
def events(logs: Path) -> Callable[[], list[dict]]:
    """Read back the events.jsonl records written so far."""
    def read() -> list[dict]:
        path = logs / "events.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return read


@pytest.fixture
def event_names(events: Callable[[], list[dict]]) -> Callable[[], list[str]]:
    return lambda: [record["event"] for record in events()]
```

- [ ] **Step 2: Write the failing tests**

`tests/test_log.py`:
```python
import json
import re

from idle_runner.log import event, log


def test_event_appends_a_json_line(logs) -> None:
    event("Silver Box Collected", x=644)

    record = json.loads((logs / "events.jsonl").read_text().splitlines()[-1])
    assert record["event"] == "Silver Box Collected"
    assert record["x"] == 644
    assert record["ts"] > 0


def test_human_log_has_millisecond_timestamps(logs) -> None:
    event("hello", a=1)
    for handler in log.handlers:
        handler.flush()

    text = (logs / "idle_runner.log").read_text()
    assert re.search(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3} INFO\s+\[MainThread\] hello a=1", text)
```

`tests/test_stats.py`:
```python
import json

from idle_runner.stats import summarize


def test_summarize_counts_events_and_routine_durations(tmp_path) -> None:
    records = [
        {"ts": 1, "event": "Silver Box Collected"},
        {"ts": 2, "event": "Silver Box Collected"},
        {"ts": 3, "event": "routine_end", "name": "auto_upgrade", "ms": 1000},
        {"ts": 4, "event": "routine_end", "name": "auto_upgrade", "ms": 3000},
    ]
    path = tmp_path / "events.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n{broken\n")

    out = summarize(path)

    assert "     2  Silver Box Collected" in out
    assert "auto_upgrade: n=2 avg=2000 ms max=3000 ms" in out
    assert "(1 unreadable lines skipped)" in out


def test_summarize_without_events_file(tmp_path) -> None:
    assert summarize(tmp_path / "missing.jsonl")[0].startswith("no events yet")
```

- [ ] **Step 3: Run them to see them fail**

Run: `.venv/bin/python -m pytest tests/test_log.py tests/test_stats.py -v`
Expected: ERROR / FAIL with `ModuleNotFoundError: No module named 'idle_runner.log'`

- [ ] **Step 4: Implement `log.py` and `stats.py`**

`idle_runner/log.py`:
```python
"""Logging: a human-readable log with millisecond timestamps plus machine-readable events.jsonl."""
import json
import logging
import logging.handlers
import threading
import time
from pathlib import Path

log = logging.getLogger("idle_runner")

_events_path: Path | None = None
_events_lock = threading.Lock()


def setup_logging(log_dir: Path, level: str = "INFO") -> None:
    """Log to the console (INFO) and to log_dir/idle_runner.log (at `level`); events to events.jsonl."""
    global _events_path
    log_dir.mkdir(parents=True, exist_ok=True)
    _events_path = log_dir / "events.jsonl"

    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)-7s [%(threadName)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "idle_runner.log", maxBytes=10_000_000, backupCount=5, encoding="utf-8")
    file_handler.setLevel(level)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)

    for handler in log.handlers[:]:
        log.removeHandler(handler)
        handler.close()
    for handler in (file_handler, console):
        handler.setFormatter(formatter)
        log.addHandler(handler)
    log.setLevel(logging.DEBUG)


def event(name: str, **fields: object) -> None:
    """Record a named event in the human log and as one JSON line in events.jsonl."""
    log.info("%s%s", name, "".join(f" {key}={value}" for key, value in fields.items()))
    if _events_path is None:
        return
    line = json.dumps({"ts": round(time.time(), 3), "event": name, **fields}, default=str)
    with _events_lock, _events_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
```

`idle_runner/stats.py`:
```python
"""`python -m idle_runner stats`: summarize events.jsonl (replaces the original Log tab)."""
import json
from collections import Counter, defaultdict
from pathlib import Path


def summarize(events_path: Path) -> list[str]:
    if not events_path.exists():
        return [f"no events yet ({events_path} not found)"]
    counts: Counter[str] = Counter()
    durations: defaultdict[str, list[int]] = defaultdict(list)
    unreadable = 0
    for line in events_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            unreadable += 1  # e.g. a line cut short by a crash
            continue
        counts[record["event"]] += 1
        if record["event"] == "routine_end":
            durations[record["name"]].append(record["ms"])

    lines = [f"{n:6d}  {name}" for name, n in counts.most_common()]
    if durations:
        lines += ["", "routine durations:"]
        for name, values in sorted(durations.items()):
            lines.append(f"{name}: n={len(values)} avg={sum(values) / len(values):.0f} ms max={max(values)} ms")
    if unreadable:
        lines.append(f"({unreadable} unreadable lines skipped)")
    return lines
```

- [ ] **Step 5: Add the `stats` command**

In `idle_runner/__main__.py`, add the import after the `png` import:
```python
from idle_runner.stats import summarize
```
Insert before the line `    args = parser.parse_args(argv)`:
```python
    stats = sub.add_parser("stats", help="summarize logs/events.jsonl")
    stats.add_argument("--log-dir", type=Path, default=Path("logs"))

```
Insert after the line `            return run_probe(args)`:
```python
        if args.command == "stats":
            print("\n".join(summarize(args.log_dir / "events.jsonl")))
            return 0
```

- [ ] **Step 6: Run the tests to see them pass**

Run: `.venv/bin/python -m pytest -v`
Expected: `5 passed`

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: ms-timestamped log, events.jsonl and stats command" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `Game`, the AutoIt-compatible facade

**Files:**
- Create: `idle_runner/game.py`, `tests/fakes.py`, `tests/test_game.py`
- Modify: `tests/conftest.py`

**Interfaces:**
- Consumes: `X11Backend` protocol shape and `GameUnavailable` (Task 1); `event`, `log` (Task 2); `write_png` (Task 1).
- Produces (all coordinates are AutoIt coordinates):
  - Module level: `Point = tuple[int, int]`, `STUCK_MS = 60_000`, `LEFT = 1`, `Backend` (Protocol).
  - `Game(backend, offset: Point = (8, 31), tolerance: int = 0, frames_dir: Path | None = None)`, with attribute `.size: tuple[int, int]` and these methods:

    | Method | Returns |
    |---|---|
    | `now()` | `float` |
    | `sleep(ms)` | |
    | `is_active()` | `bool` |
    | `pixel_search(left, top, right, bottom, color, variation=0)` | `Point \| None` |
    | `pixel_is(x, y, color)` | `bool` |
    | `find_until(left, top, right, bottom, color, timeout_ms=15_000)` | `Point \| None` |
    | `save_frame(label)` | `Path \| None` |
    | `stuck(where, **fields)` | |
    | `routine(name)` | context manager |
    | `move(x, y)` | |
    | `click(x, y, clicks=1)` | |
    | `mouse_down()` / `mouse_up()` | |
    | `wheel(up: bool, notches: int)` | |
    | `drag(x1, y1, x2, y2)` | |
    | `key_down(key)` / `key_up(key)` | |
    | `tap(key)` | |
    | `hold(press_ms, post_ms=0, key="Up")` | |
    | `release_all()` | |

  - Test fixtures: `fake` (a `FakeBackend`) and `game`. Shared test constant: `tests.fakes.OFFSET = (8, 31)`.

- [ ] **Step 1: Write the test double**

`tests/fakes.py`:
```python
"""Test doubles shared by the test suite."""
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import numpy as np

OFFSET = (8, 31)  # AutoIt window-frame offset used by every test


class FakeBackend:
    """In-memory stand-in for X11Backend.

    - `frame` is the client area; `paint()` takes AutoIt coordinates, like the code under test.
    - Virtual clock: `sleep_ms` advances `t`; every other backend call costs `cost_ms`.
    - `actions` logs input in client coordinates; `clicks()` / `taps()` summarize it.
    """

    def __init__(self, width: int = 1280, height: int = 720) -> None:
        self.frame = np.zeros((height, width, 3), dtype=np.uint8)
        self.t = 0.0
        self.cost_ms = 1.0
        self.active = True
        self.realtime = False  # also really sleep (for threaded tests)
        self.stop_at: float | None = None  # raise KeyboardInterrupt once t reaches this
        self.pointer = (0, 0)
        self.actions: list[tuple] = []
        self.on_action: Callable[[tuple], None] | None = None

    def paint(self, x: int, y: int, color: int, w: int = 1, h: int = 1) -> None:
        cx, cy = x - OFFSET[0], y - OFFSET[1]
        self.frame[cy:cy + h, cx:cx + w] = ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)

    def clicks(self) -> list[tuple[int, int]]:
        """Left-button presses, in AutoIt coordinates."""
        return [(a[1] + OFFSET[0], a[2] + OFFSET[1]) for a in self.actions if a[0] == "click"]

    def taps(self) -> list[str]:
        """Names of pressed keys, in order."""
        return [a[1] for a in self.actions if a[0] == "key" and a[2]]

    # --- Backend protocol ---
    def size(self) -> tuple[int, int]:
        return self.frame.shape[1], self.frame.shape[0]

    def is_active(self) -> bool:
        return self.active

    def grab(self, x: int, y: int, w: int, h: int) -> np.ndarray:
        self.t += self.cost_ms
        return self.frame[y:y + h, x:x + w]

    def move(self, x: int, y: int) -> None:
        self.pointer = (x, y)
        self._record(("move", x, y))

    def button(self, button: int, down: bool) -> None:
        if button == 1 and down:
            self._record(("click", *self.pointer))
        else:
            self._record(("button", button, down))

    def key(self, name: str, down: bool) -> None:
        self._record(("key", name, down))

    def now_ms(self) -> float:
        return self.t

    def sleep_ms(self, ms: float) -> None:
        if self.realtime:
            time.sleep(ms / 1000)
        self.t += ms
        if self.stop_at is not None and self.t >= self.stop_at:
            raise KeyboardInterrupt

    def _record(self, action: tuple) -> None:
        self.t += self.cost_ms
        self.actions.append(action)
        if self.on_action:
            self.on_action(action)


class FakeJumper:
    """Stand-in for the jump Repeater: records pauses instead of tapping keys."""

    def __init__(self) -> None:
        self.pauses = 0
        self.running = False
        self.stopped = False

    @contextmanager
    def paused(self) -> Iterator[None]:
        self.pauses += 1
        yield

    def resume(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.stopped = True
```

Append to `tests/conftest.py`:
```python
from idle_runner.game import Game
from tests.fakes import OFFSET, FakeBackend, FakeJumper  # OFFSET: tests use the same frame offset


@pytest.fixture
def fake() -> FakeBackend:
    return FakeBackend()


@pytest.fixture
def game(fake: FakeBackend, tmp_path: Path) -> Game:
    return Game(fake, offset=OFFSET, frames_dir=tmp_path / "frames")


@pytest.fixture
def jumper() -> FakeJumper:
    return FakeJumper()
```

- [ ] **Step 2: Write the failing tests**

`tests/test_game.py`:
```python
import pytest

from idle_runner.game import Game
from idle_runner.x11 import GameUnavailable
from tests.fakes import OFFSET


def test_pixel_search_uses_autoit_coordinates(game, fake) -> None:
    fake.paint(650, 36, 0xCA9700)

    assert game.pixel_search(640, 30, 660, 40, 0xCA9700) == (650, 36)
    assert game.pixel_is(650, 36, 0xCA9700)
    assert not game.pixel_is(651, 36, 0xCA9700)


def test_pixel_search_scan_order_follows_autoit(game, fake) -> None:
    for x, y in ((100, 100), (110, 100), (100, 110)):
        fake.paint(x, y, 0x123456)

    assert game.pixel_search(90, 90, 120, 120, 0x123456) == (100, 100)  # top row first, left to right
    assert game.pixel_search(120, 90, 90, 120, 0x123456) == (110, 100)  # left > right: right to left
    assert game.pixel_search(90, 120, 120, 90, 0x123456) == (100, 110)  # top > bottom: bottom to top


def test_variation_and_global_tolerance(fake) -> None:
    fake.paint(200, 200, 0x101010)

    assert Game(fake, offset=OFFSET).pixel_search(200, 200, 200, 200, 0x141414) is None
    assert Game(fake, offset=OFFSET).pixel_search(200, 200, 200, 200, 0x141414, variation=4) == (200, 200)
    assert Game(fake, offset=OFFSET, tolerance=4).pixel_is(200, 200, 0x141414)


def test_pixel_search_clips_to_the_client_area(game, fake) -> None:
    fake.paint(8, 31, 0xABCDEF)  # client pixel (0, 0)

    assert game.pixel_search(0, 0, 20, 40, 0xABCDEF) == (8, 31)
    assert game.pixel_search(2000, 2000, 2100, 2100, 0xABCDEF) is None


def test_find_until_times_out_on_the_clock(game, fake) -> None:
    assert game.find_until(10, 40, 10, 40, 0xFFFFFF, timeout_ms=100) is None
    assert fake.t >= 100


def test_click_requires_focus(game, fake) -> None:
    game.click(644, 49, clicks=2)
    assert fake.clicks() == [(644, 49), (644, 49)]

    fake.active = False
    with pytest.raises(GameUnavailable):
        game.click(644, 49)


def test_click_outside_the_window_is_refused_and_logged(game, fake, event_names) -> None:
    game.click(33, -23)

    assert fake.clicks() == []
    assert "click_outside_window" in event_names()


def test_hold_presses_the_key_for_the_whole_duration(game, fake) -> None:
    start = fake.t
    game.hold(300, 100, "Up")

    assert [a for a in fake.actions if a[0] == "key"] == [("key", "Up", True), ("key", "Up", False)]
    assert fake.t - start >= 400


def test_routine_logs_duration_and_saves_a_frame_on_crash(game, events) -> None:
    with game.routine("demo"):
        game.sleep(250)
    with pytest.raises(RuntimeError):
        with game.routine("boom"):
            raise RuntimeError("bug")

    records = events()
    end = next(r for r in records if r["event"] == "routine_end")
    assert end["name"] == "demo" and end["ms"] >= 250
    assert any(r["event"] == "frame" and r["label"] == "crash-boom" for r in records)


def test_stuck_logs_and_saves_a_frame(game, events, tmp_path) -> None:
    game.stuck("shop.scroll", y=170)

    records = events()
    assert any(r["event"] == "stuck" and r["where"] == "shop.scroll" and r["y"] == 170 for r in records)
    assert list((tmp_path / "frames").glob("*-stuck-shop.scroll.png"))


def test_release_all_releases_keys_and_button(game, fake) -> None:
    fake.active = False  # must work even when the game lost focus (e.g. on Ctrl+C)
    game.release_all()

    assert ("key", "Up", False) in fake.actions
    assert ("key", "d", False) in fake.actions
    assert ("button", 1, False) in fake.actions
```

- [ ] **Step 3: Run them to see them fail**

Run: `.venv/bin/python -m pytest tests/test_game.py -v`
Expected: ERROR with `ModuleNotFoundError: No module named 'idle_runner.game'`

- [ ] **Step 4: Implement `game.py`**

`idle_runner/game.py`:
```python
"""AutoIt-compatible facade over the X11 backend.

Every coordinate given to `Game` is an *AutoIt coordinate*, copied verbatim from the original
Idle Runner. It is relative to the game window's top-left corner *including* the Windows title
bar and borders (`Opt("PixelCoordMode", 0)` / `Opt("MouseCoordMode", 0)`). `offset` converts it
to client-area pixels, so each line of the port stays traceable to the AutoIt source.
"""
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Protocol

import numpy as np

from idle_runner.log import event, log
from idle_runner.png import write_png
from idle_runner.x11 import GameUnavailable

Point = tuple[int, int]

STUCK_MS = 60_000  # safety net for loops the AutoIt original would spin in forever
LEFT, WHEEL_UP, WHEEL_DOWN = 1, 4, 5
HELD_KEYS = ("Up", "Right", "a", "d", "r")  # every key the bot ever presses


class Backend(Protocol):
    """What Game needs from the outside world: X11Backend in production, FakeBackend in tests."""

    def size(self) -> tuple[int, int]: ...
    def is_active(self) -> bool: ...
    def grab(self, x: int, y: int, w: int, h: int) -> np.ndarray: ...
    def move(self, x: int, y: int) -> None: ...
    def button(self, button: int, down: bool) -> None: ...
    def key(self, name: str, down: bool) -> None: ...
    def now_ms(self) -> float: ...
    def sleep_ms(self, ms: float) -> None: ...


class Game:
    def __init__(self, backend: Backend, offset: Point = (8, 31), tolerance: int = 0,
                 frames_dir: Path | None = None) -> None:
        self.backend = backend
        self.ox, self.oy = offset
        self.tolerance = tolerance
        self.frames_dir = frames_dir
        self.size = backend.size()

    # --- time: AutoIt Sleep / TimerInit / TimerDiff ---
    def now(self) -> float:
        return self.backend.now_ms()

    def sleep(self, ms: float) -> None:
        self.backend.sleep_ms(ms)

    def is_active(self) -> bool:
        return self.backend.is_active()

    # --- screen ---
    def pixel_search(self, left: int, top: int, right: int, bottom: int, color: int,
                     variation: int = 0) -> Point | None:
        """AutoIt PixelSearch.

        Returns the first pixel whose RGB channels are each within `variation` of `color`.
        Rows are scanned top to bottom and columns left to right; `left > right` or `top > bottom`
        reverses that direction. Bounds are inclusive and clipped to the client area.
        """
        found = self._search(left, top, right, bottom, color, variation)
        log.debug("pixel_search (%d,%d,%d,%d) 0x%06X v%d -> %s", left, top, right, bottom, color, variation, found)
        return found

    def _search(self, left: int, top: int, right: int, bottom: int, color: int, variation: int) -> Point | None:
        width, height = self.size
        x0, x1 = sorted((left - self.ox, right - self.ox))
        y0, y1 = sorted((top - self.oy, bottom - self.oy))
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, width - 1), min(y1, height - 1)
        if x0 > x1 or y0 > y1:
            return None
        region = self.backend.grab(x0, y0, x1 - x0 + 1, y1 - y0 + 1)
        target = np.array([(color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF], dtype=np.uint8)
        tolerance = variation + self.tolerance
        if tolerance == 0:
            mask = (region == target).all(axis=2)
        else:
            mask = (np.abs(region.astype(np.int16) - target.astype(np.int16)) <= tolerance).all(axis=2)
        if top > bottom:
            mask = mask[::-1]
        if left > right:
            mask = mask[:, ::-1]
        if not mask.any():
            return None
        row, col = divmod(int(mask.argmax()), mask.shape[1])
        y = y1 - row if top > bottom else y0 + row
        x = x1 - col if left > right else x0 + col
        return x + self.ox, y + self.oy

    def pixel_is(self, x: int, y: int, color: int) -> bool:
        return self.pixel_search(x, y, x, y, color) is not None

    def find_until(self, left: int, top: int, right: int, bottom: int, color: int,
                   timeout_ms: float = 15_000) -> Point | None:
        """FindPixelUntilFound from Common.au3: poll until the colour shows up or time runs out."""
        start = self.now()
        while self.now() - start <= timeout_ms:
            found = self._search(left, top, right, bottom, color, 0)
            if found:
                log.debug("find_until 0x%06X found at %s after %.0f ms", color, found, self.now() - start)
                return found
            self.sleep(1)
        log.debug("find_until 0x%06X in (%d,%d,%d,%d) timed out after %.0f ms",
                  color, left, top, right, bottom, timeout_ms)
        return None

    # --- debugging aids ---
    def save_frame(self, label: str) -> Path | None:
        """Save the whole client area as PNG under frames_dir (no-op when frames are disabled)."""
        if self.frames_dir is None:
            return None
        try:
            rgb = self.backend.grab(0, 0, *self.size)
        except GameUnavailable:
            return None
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        path = self.frames_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')[:-3]}-{label}.png"
        write_png(path, rgb)
        event("frame", label=label, path=str(path))
        return path

    def stuck(self, where: str, **fields: object) -> None:
        """Report a safety-net timeout (a loop the AutoIt original would spin in forever)."""
        event("stuck", where=where, **fields)
        self.save_frame(f"stuck-{where}")

    @contextmanager
    def routine(self, name: str) -> Iterator[None]:
        """Log start, end and duration of a routine; save a frame if it crashes."""
        start = self.now()
        event("routine_start", name=name)
        try:
            yield
        except GameUnavailable:
            event("routine_abort", name=name, ms=round(self.now() - start))
            raise
        except Exception:
            log.exception("routine %s crashed", name)
            self.save_frame(f"crash-{name}")
            raise
        event("routine_end", name=name, ms=round(self.now() - start))

    # --- input (refused while the game isn't focused) ---
    def _require_focus(self) -> None:
        if not self.backend.is_active():
            raise GameUnavailable("the game window is not focused")

    def _client(self, x: int, y: int) -> Point | None:
        cx, cy = x - self.ox, y - self.oy
        if 0 <= cx < self.size[0] and 0 <= cy < self.size[1]:
            return cx, cy
        event("click_outside_window", x=x, y=y)
        return None

    def move(self, x: int, y: int) -> None:
        """MouseMove(x, y, 0)."""
        self._require_focus()
        point = self._client(x, y)
        if point:
            self.backend.move(*point)

    def click(self, x: int, y: int, clicks: int = 1) -> None:
        """MouseClick("left", x, y, clicks, 0): instant move, 10 ms down/up delays (AutoIt defaults)."""
        self._require_focus()
        point = self._client(x, y)
        if point is None:
            return
        self.backend.move(*point)
        for _ in range(clicks):
            self.backend.button(LEFT, True)
            self.sleep(10)
            self.backend.button(LEFT, False)
            self.sleep(10)

    def mouse_down(self) -> None:
        self._require_focus()
        self.backend.button(LEFT, True)

    def mouse_up(self) -> None:
        self.backend.button(LEFT, False)  # never refused: a stuck button is worse than a stray release

    def wheel(self, up: bool, notches: int) -> None:
        """MouseWheel($MOUSE_WHEEL_UP/DOWN, notches) at the current pointer position."""
        self._require_focus()
        button = WHEEL_UP if up else WHEEL_DOWN
        for _ in range(notches):
            self.backend.button(button, True)
            self.backend.button(button, False)

    def drag(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """MouseClickDrag("left", ...) at AutoIt's default speed: press, wait, glide, wait, release."""
        self._require_focus()
        start, end = self._client(x1, y1), self._client(x2, y2)
        if start is None or end is None:
            return
        self.backend.move(*start)
        self.backend.button(LEFT, True)
        self.sleep(250)
        steps = 20
        for i in range(1, steps + 1):
            self.backend.move(start[0] + (end[0] - start[0]) * i // steps,
                              start[1] + (end[1] - start[1]) * i // steps)
            self.sleep(10)
        self.sleep(250)
        self.backend.button(LEFT, False)

    def key_down(self, key: str) -> None:
        self._require_focus()
        self.backend.key(key, True)

    def key_up(self, key: str) -> None:
        self.backend.key(key, False)  # never refused, like mouse_up

    def tap(self, key: str) -> None:
        """Send("{key}") / ControlSend with AutoIt's default 5 ms key delays."""
        self.key_down(key)
        self.sleep(5)
        self.key_up(key)
        self.sleep(5)

    def hold(self, press_ms: float, post_ms: float = 0, key: str = "Up") -> None:
        """cSend() from Common.au3: hold `key` for press_ms, release, then wait post_ms."""
        self.key_down(key)
        self.sleep(press_ms)
        self.key_up(key)
        self.sleep(post_ms)

    def release_all(self) -> None:
        """Release every key and the mouse button (on exit, so nothing stays stuck in X)."""
        for key in HELD_KEYS:
            self.backend.key(key, False)
        self.backend.button(LEFT, False)
```

- [ ] **Step 5: Run the tests to see them pass**

Run: `.venv/bin/python -m pytest -v`
Expected: `16 passed`

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: AutoIt-compatible Game facade with focus guard and debug aids" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Settings (TOML)

**Files:**
- Create: `idle_runner/config.py`, `config.example.toml`, `tests/test_config.py`

**Interfaces:**
- Produces: `idle_runner.config.Settings` (frozen dataclass, fields below), `load_settings(path: Path) -> Settings` (raises `ValueError` naming the file and key).

- [ ] **Step 1: Write the failing tests**

`tests/test_config.py`:
```python
from pathlib import Path

import pytest

from idle_runner.config import Settings, load_settings

EXAMPLE = Path(__file__).resolve().parents[1] / "config.example.toml"


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(text)
    return path


def test_defaults_match_the_original(tmp_path) -> None:
    s = load_settings(write(tmp_path, ""))
    assert s.jump_interval_ms == 150
    assert s.auto_buy_minutes == 10 and s.auto_ascend_minutes == 10
    assert s.no_lockpicking is True
    assert s.circle_portals_count == 7


def test_sections_are_flattened(tmp_path) -> None:
    s = load_settings(write(tmp_path, "[general]\nauto_buy_upgrades = true\nauto_buy_minutes = 2.5\n"))
    assert s.auto_buy_upgrades is True
    assert s.auto_buy_minutes == 2.5


def test_unknown_key_is_an_error(tmp_path) -> None:
    with pytest.raises(ValueError, match="unknown setting 'auto_bu_upgrades'"):
        load_settings(write(tmp_path, "[general]\nauto_bu_upgrades = true\n"))


def test_wrong_type_is_an_error(tmp_path) -> None:
    with pytest.raises(ValueError, match="'jump_interval_ms' must be int"):
        load_settings(write(tmp_path, '[general]\njump_interval_ms = "fast"\n'))
    with pytest.raises(ValueError, match="'jump_interval_ms' must be int"):
        load_settings(write(tmp_path, "[general]\njump_interval_ms = true\n"))


def test_out_of_range_is_an_error(tmp_path) -> None:
    with pytest.raises(ValueError, match="jump_interval_ms must be 0-300"):
        load_settings(write(tmp_path, "[general]\njump_interval_ms = 301\n"))


def test_example_config_documents_the_defaults() -> None:
    assert load_settings(EXAMPLE) == Settings()
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest tests/test_config.py -v`
Expected: ERROR with `ModuleNotFoundError: No module named 'idle_runner.config'`

- [ ] **Step 3: Implement `config.py` and the example**

`idle_runner/config.py` (use the offset measured in Task 1 if it wasn't (8, 31)):
```python
"""Settings, read from a TOML file (see config.example.toml)."""
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    # [game]
    window_name: str = "Idle Slayer"
    offset_x: int = 8
    offset_y: int = 31
    color_tolerance: int = 0
    # [general]
    jump_interval_ms: int = 150
    circle_portals: bool = False
    circle_portals_count: int = 7
    disable_rage_without_soul_bonus: bool = False
    auto_buy_upgrades: bool = False
    auto_buy_minutes: float = 10
    auto_ascend: bool = False
    auto_ascend_minutes: float = 10
    # [minigames]
    skip_bonus_stage: bool = False
    no_lockpicking: bool = True
    no_reinforced_crystal_saver: bool = False
    perfect_chest_hunt: bool = False
    # [crafting]
    craft_soul_bonus: bool = False
    craft_rage_pill: bool = False
    craft_dimensional_staff: bool = False
    craft_bidimensional_staff: bool = False
    # [debug]
    log_dir: str = "logs"
    log_level: str = "INFO"
    save_frames: bool = True


def load_settings(path: Path) -> Settings:
    """Read a TOML config. Every key is optional; unknown keys, wrong types and bad ranges are errors."""
    with path.open("rb") as f:
        data = tomllib.load(f)
    values: dict[str, object] = {}
    for section, entries in data.items():
        if not isinstance(entries, dict):
            raise ValueError(f"{path}: '{section}' must be a [section] table")
        values.update(entries)

    types = {field.name: field.type for field in fields(Settings)}
    for key, value in values.items():
        if key not in types:
            raise ValueError(f"{path}: unknown setting '{key}'")
        expected = types[key]
        accepted = (int, float) if expected is float else (expected,)
        # bool is a subclass of int in Python, so check it explicitly both ways.
        if isinstance(value, bool) is not (expected is bool) or not isinstance(value, accepted):
            raise ValueError(f"{path}: '{key}' must be {expected.__name__}, got {value!r}")

    settings = Settings(**values)
    _check_ranges(path, settings)
    return settings


def _check_ranges(path: Path, s: Settings) -> None:
    problems = []
    if not 0 <= s.jump_interval_ms <= 300:
        problems.append("jump_interval_ms must be 0-300")
    if not 1 <= s.circle_portals_count <= 9:
        problems.append("circle_portals_count must be 1-9")
    if s.auto_buy_minutes <= 0 or s.auto_ascend_minutes <= 0:
        problems.append("auto_buy_minutes and auto_ascend_minutes must be > 0")
    if not 0 <= s.color_tolerance <= 255:
        problems.append("color_tolerance must be 0-255")
    if s.log_level not in ("DEBUG", "INFO", "WARNING"):
        problems.append("log_level must be DEBUG, INFO or WARNING")
    if problems:
        raise ValueError(f"{path}: " + "; ".join(problems))
```

`config.example.toml`:
```toml
# Idle Runner (Linux) settings. Copy to config.toml and edit.
# Every key is optional: a missing key uses the default shown here.

[game]
window_name = "Idle Slayer"
# Offset between the original AutoIt coordinates (window including the Windows title bar
# and borders) and the game's client area. Measured with `python -m idle_runner probe`.
offset_x = 8
offset_y = 31
# Extra per-channel tolerance added to every colour comparison (0 = exact, like AutoIt).
color_tolerance = 0

[general]
jump_interval_ms = 150                   # 0-300: "Jump Rate" of the original GUI
circle_portals = false
circle_portals_count = 7                 # first destination: 1 hills, 2 hot desert, 3 jungle, 4 frozen fields,
                                         # 5 funky, 6 modern city, 7 factory, 8 valley, 9 castle
disable_rage_without_soul_bonus = false  # don't rage at Megahordes unless Soul Bonus is active
auto_buy_upgrades = false
auto_buy_minutes = 10
auto_ascend = false
auto_ascend_minutes = 10

[minigames]
skip_bonus_stage = false
no_lockpicking = true                    # true if you DON'T have the Divinity Lockpicking 100
no_reinforced_crystal_saver = false      # true if you DON'T have the Reinforced Crystal Saver
perfect_chest_hunt = false               # riskier strategy that goes for Perfect Chest Hunts

[crafting]
craft_soul_bonus = false                 # Souls Compass at Megahorde + Soul Bonus
craft_rage_pill = false                  # Rage Pill at Megahorde + Soul Bonus
craft_dimensional_staff = false          # once per run, at the first Megahorde
craft_bidimensional_staff = false        # once per run, at the first Megahorde

[debug]
log_dir = "logs"
log_level = "INFO"                       # DEBUG also traces every pixel search in the log file
save_frames = true                       # PNG screenshots at minigames, timeouts and crashes
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `.venv/bin/python -m pytest -v`
Expected: `22 passed`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: TOML settings with strict validation" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: `Repeater` (jumper thread)

**Files:**
- Create: `idle_runner/repeater.py`, `tests/test_repeater.py`

**Interfaces:**
- Consumes: `Game.tap`, `Game.sleep` (Task 3); `GameUnavailable`; `event`, `log`.
- Produces: `Repeater(game: Game, keys: tuple[str, ...], interval_ms: float, name: str)` with `resume()`, `pause()` (synchronous), `stop()`, `paused()` context manager. It starts paused.

- [ ] **Step 1: Write the failing tests**

`tests/test_repeater.py`:
```python
import time

from idle_runner.repeater import Repeater


def test_taps_keys_until_paused_and_pause_is_immediate(fake, game) -> None:
    fake.realtime = True
    repeater = Repeater(game, ("Up", "Right"), interval_ms=10, name="jumper")
    repeater.resume()
    time.sleep(0.2)
    repeater.pause()
    count = len(fake.taps())
    time.sleep(0.1)
    repeater.stop()

    assert count >= 4
    assert fake.taps()[:2] == ["Up", "Right"]
    assert len(fake.taps()) == count  # nothing after pause() returned


def test_paused_context_restores_the_previous_state(fake, game) -> None:
    fake.realtime = True
    repeater = Repeater(game, ("Up",), interval_ms=10, name="jumper")
    repeater.resume()
    with repeater.paused():
        count = len(fake.taps())
        time.sleep(0.05)
        assert len(fake.taps()) == count
    time.sleep(0.05)
    repeater.stop()

    assert len(fake.taps()) > count


def test_does_not_tap_while_the_game_is_unfocused(fake, game) -> None:
    fake.realtime = True
    fake.active = False
    repeater = Repeater(game, ("Up",), interval_ms=10, name="jumper")
    repeater.resume()
    time.sleep(0.1)
    repeater.stop()

    assert fake.taps() == []


def test_repeater_logs_errors_and_keeps_running(fake, game, event_names) -> None:
    fake.realtime = True
    real_key = fake.key
    failures = [RuntimeError("X connection hiccup")]

    def flaky_key(name: str, down: bool) -> None:
        if failures:
            raise failures.pop()
        real_key(name, down)

    fake.key = flaky_key
    repeater = Repeater(game, ("Up",), interval_ms=10, name="jumper")
    repeater.resume()
    time.sleep(1.3)  # the error, a 1 s back-off, then more taps
    repeater.stop()

    assert "repeater_error" in event_names()
    assert "Up" in fake.taps()
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest tests/test_repeater.py -v`
Expected: ERROR with `ModuleNotFoundError: No module named 'idle_runner.repeater'`

- [ ] **Step 3: Implement `repeater.py`**

`idle_runner/repeater.py`:
```python
"""Background key repeater.

Used for the jump/boost loop and for Victor's `AdlibRegister("Shoot", 50)`. In the original,
`ShootAndBoost` ran as a second process that noticed pauses up to 700 ms late.
"""
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from idle_runner.game import Game
from idle_runner.log import event, log
from idle_runner.x11 import GameUnavailable


class Repeater:
    """Taps `keys` every `interval_ms` on a daemon thread. Starts paused: call resume()."""

    def __init__(self, game: Game, keys: tuple[str, ...], interval_ms: float, name: str) -> None:
        self.game = game
        self.keys = keys
        self.interval_ms = interval_ms
        self.name = name
        self._running = threading.Event()
        self._stop = threading.Event()
        self._tap_lock = threading.Lock()
        self._thread = threading.Thread(target=self._loop, name=name, daemon=True)
        self._thread.start()

    def resume(self) -> None:
        self._running.set()

    def pause(self) -> None:
        """Stop tapping. Returns only once an in-flight tap has finished (SyncProcess(False))."""
        self._running.clear()
        with self._tap_lock:
            pass

    def stop(self) -> None:
        self._stop.set()
        self._running.set()  # wake the thread so it can exit
        self._thread.join(timeout=2)

    @contextmanager
    def paused(self) -> Iterator[None]:
        """Pause for the duration of a routine, then restore the previous state."""
        was_running = self._running.is_set()
        self.pause()
        try:
            yield
        finally:
            if was_running:
                self.resume()

    def _loop(self) -> None:
        while True:
            self._running.wait()
            if self._stop.is_set():
                return
            self.game.sleep(self.interval_ms)
            try:
                with self._tap_lock:
                    if self._stop.is_set() or not self._running.is_set():
                        continue
                    for key in self.keys:
                        self.game.tap(key)
            except GameUnavailable:
                self.game.sleep(500)  # the game isn't focused: stay quiet
            except Exception:
                log.exception("repeater %s failed; retrying in 1 s", self.name)
                event("repeater_error", name=self.name)
                self.game.sleep(1000)
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `.venv/bin/python -m pytest -v`
Expected: `26 passed`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: Repeater thread with synchronous pause" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Shop (auto upgrade, quests, auto ascend)

**Files:**
- Create: `idle_runner/shop.py`, `tests/test_shop.py`

**Interfaces:**
- Consumes: `Game`, `STUCK_MS` (Task 3); `event`.
- Produces:
  - `scroll_to_top(game: Game, x: int, y: int, where: str, pause_ms: float = 0) -> None`
  - `Shop(game: Game)` with:
    - attributes `loop_amount: int`, `upgrades_bought: int`, `equipment_buys: int`
    - methods `auto_upgrade() -> None`, `buy_upgrade() -> None`, `buy_equipment() -> None`, `claim_quests() -> None`
    - `auto_ascend() -> bool` (True when it ascended)

- [ ] **Step 1: Write the failing tests**

`tests/test_shop.py`:
```python
from idle_runner.shop import Shop
from tests.fakes import OFFSET


def client_click(x: int, y: int) -> tuple:
    """The FakeBackend action recorded for a click at AutoIt (x, y)."""
    return ("click", x - OFFSET[0], y - OFFSET[1])


def test_buy_upgrade_clicks_green_rows_until_none_is_left(game, fake) -> None:
    fake.paint(1180, 180, 0x11A622)  # first row's green buy button (checked at y + 10)

    def sold_out_after_three(action: tuple) -> None:
        if action == client_click(1180, 170) and fake.clicks().count((1180, 170)) == 3:
            fake.paint(1180, 180, 0x000000)

    fake.on_action = sold_out_after_three
    shop = Shop(game)
    shop.loop_amount = 6  # no equipment round: the shop closes right away
    shop.buy_upgrade()

    assert fake.clicks().count((1180, 170)) == 3
    assert fake.clicks()[-1] == (1222, 677)
    assert shop.upgrades_bought == 3


def test_buy_upgrade_skips_the_excluded_upgrades(game, fake) -> None:
    fake.paint(890, 200, 0xF4B41B)   # excluded upgrade icon in the first row
    fake.paint(1180, 276, 0x0C7418)  # the second row (y = 266) is buyable
    fake.on_action = lambda a: fake.paint(1180, 276, 0) if a == client_click(1180, 266) else None
    shop = Shop(game)
    shop.loop_amount = 6
    shop.buy_upgrade()

    assert (1180, 266) in fake.clicks()
    assert (1180, 170) not in fake.clicks()


def test_auto_upgrade_logs_when_the_shop_does_not_open(game, fake, event_names) -> None:
    Shop(game).auto_upgrade()

    assert fake.clicks() == [(1244, 712), (1163, 655)]
    assert "AutoUpgrade shop not open" in event_names()
    assert "AutoUpgrade Done" in event_names()


def test_stuck_scrollbar_is_reported_instead_of_looping_forever(game, fake, events) -> None:
    fake.paint(1254, 167, 0xD6D6D6)  # the scrollbar top never changes
    shop = Shop(game)
    shop.loop_amount = 6
    shop.buy_upgrade()

    assert any(r["event"] == "stuck" and r["where"] == "buy_upgrade.scroll_top" for r in events())


def test_claim_quests_clicks_green_claim_buttons(game, fake, event_names) -> None:
    fake.paint(1160, 300, 0x11A622)
    fake.on_action = lambda a: fake.paint(1160, 300, 0) if a == client_click(1160, 300) else None
    Shop(game).claim_quests()

    assert (1160, 300) in fake.clicks()
    assert event_names().count("Quest Claimed") == 1
    assert fake.clicks()[-1] == (1244, 712)


def test_auto_ascend_when_the_panel_is_already_open(game, fake, event_names) -> None:
    fake.paint(260, 600, 0x58188D)

    assert Shop(game).auto_ascend() is True
    assert fake.clicks()[:4] == [(260, 600), (550, 580), (1244, 712), (1163, 655)]
    assert "Ascended" in event_names()


def test_auto_ascend_logs_and_saves_a_frame_when_the_button_is_missing(game, fake, event_names) -> None:
    assert Shop(game).auto_ascend() is False
    assert fake.clicks() == [(95, 90), (93, 680)]
    assert "Ascend skipped" in event_names()
    assert "frame" in event_names()
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest tests/test_shop.py -v`
Expected: ERROR with `ModuleNotFoundError: No module named 'idle_runner.shop'`

- [ ] **Step 3: Implement `shop.py`**

`idle_runner/shop.py`:
```python
"""Shop routines ported from Idle Runner.au3: AutoUpgrade, BuyUpgrade, BuyEquipment, ClaimQuests, AutoAscend."""
from idle_runner.game import STUCK_MS, Game
from idle_runner.log import event

SCROLLBAR_GRAY = 0xD6D6D6


def scroll_to_top(game: Game, x: int, y: int, where: str, pause_ms: float = 0) -> None:
    """Wheel up until the scrollbar's top pixel at (x, y) is no longer gray."""
    deadline = game.now() + STUCK_MS
    while True:
        game.wheel(up=True, notches=20)
        game.sleep(pause_ms)
        if not game.pixel_is(x, y, SCROLLBAR_GRAY):
            return
        if game.now() > deadline:
            game.stuck(f"{where}.scroll_top")
            return


class Shop:
    def __init__(self, game: Game) -> None:
        self.game = game
        # $iAutoBuyLoopAmount: caps the BuyUpgrade <-> BuyEquipment rounds at 6. The main loop
        # resets it before each timed buy; nothing else does (known issue, see Task 13).
        self.loop_amount = 0
        self.upgrades_bought = 0
        self.equipment_buys = 0

    def auto_upgrade(self) -> None:
        g = self.game
        event("AutoUpgrade Active")
        self.upgrades_bought = 0
        self.equipment_buys = 0
        g.click(1244, 712)  # close the shop window if it's open
        g.sleep(150)
        g.click(1163, 655)  # open the shop window
        g.sleep(150)
        if g.pixel_search(807, 140, 807, 155, 0xFFFFFF):  # the shop's corner is visible
            self.buy_upgrade()
        else:
            event("AutoUpgrade shop not open")
            g.save_frame("shop-not-open")
        event("AutoUpgrade Done", upgrades=self.upgrades_bought, equipment=self.equipment_buys,
              rounds=self.loop_amount)

    def buy_upgrade(self) -> None:
        g = self.game
        g.click(927, 683)  # upgrades tab
        g.sleep(150)
        g.move(1254, 172)  # over the scrollbar
        scroll_to_top(g, 1254, 167, "buy_upgrade")
        g.sleep(400)
        bought = False
        y = 170
        deadline = g.now() + STUCK_MS
        while True:
            # Rows the original never buys (its tooltip: Vertical Magnet and Electric Worms).
            if g.pixel_search(882, y, 909, y + 72, 0xF4B41B):
                y += 96
            if g.pixel_search(882, y, 909, y + 72, 0xE478FF):
                y += 96
            if not (g.pixel_is(1180, y + 10, 0x11A622) or g.pixel_is(1180, y + 10, 0x0C7418)):
                break
            if g.now() > deadline:
                g.stuck("buy_upgrade", y=y)
                break
            bought = True
            self.upgrades_bought += 1
            g.click(1180, y)  # green buy button
            g.sleep(50)
        if bought and self.loop_amount < 6:
            self.loop_amount += 1
            self.buy_equipment()
        else:
            g.click(1222, 677)  # close the shop

    def buy_equipment(self) -> None:
        g = self.game
        g.click(850, 690)  # armor tab
        g.sleep(50)
        g.click(1180, 636, clicks=4)  # "max" buy amount
        if g.pixel_is(1257, 340, 0x11AA23):  # no scrollbar: buy the first item (sword)
            g.click(1200, 200, clicks=5)
            self.equipment_buys += 1
        else:
            g.click(1253, 592, clicks=5)  # bottom of the scrollbar
            g.sleep(200)
        deadline = g.now() + STUCK_MS
        while True:
            found = g.pixel_search(1160, 590, 1160, 170, 0x11AA23, variation=10)  # bottom to top
            if found is None:
                g.move(1260, 170)
                g.wheel(up=True, notches=1)
                if not g.pixel_is(1260, 168, SCROLLBAR_GRAY):
                    break
                g.sleep(10)
            else:
                g.click(850, 690)  # armor tab (as in the original)
                g.click(*found, clicks=5)
                self.equipment_buys += 1
            if g.now() > deadline:
                g.stuck("buy_equipment")
                break
        self.buy_upgrade()

    def claim_quests(self) -> None:
        g = self.game
        event("Claiming quest")
        g.click(1244, 712)  # close the shop window if it's open
        g.sleep(150)
        g.click(1163, 655)  # open the shop window
        g.sleep(150)
        g.click(850, 690)  # armor tab
        g.click(927, 683)  # upgrades tab
        g.sleep(150)
        g.click(1000, 690)  # quests tab
        g.sleep(50)
        g.move(1254, 272)
        scroll_to_top(g, 1254, 267, "claim_quests", pause_ms=20)
        g.sleep(600)
        deadline = g.now() + STUCK_MS
        while True:
            found = g.pixel_search(1160, 270, 1160, 590, 0x11A622, variation=10)
            if found is None:
                g.move(1267, 270)
                g.wheel(up=False, notches=1)
                if not g.pixel_is(1267, 658, 0xA0A0A0):  # no gray scrollbar
                    break
                if g.pixel_is(1267, 655, 0xFFFFFF):  # reached the bottom
                    break
                g.sleep(100)
            else:
                event("Quest Claimed")
                g.click(*found)
            if g.now() > deadline:
                g.stuck("claim_quests")
                break
        g.click(1244, 712)  # close the shop

    def auto_ascend(self) -> bool:
        """Ascend and run one AutoUpgrade. Returns False when the ascend button wasn't found."""
        g = self.game
        if g.pixel_is(260, 600, 0x58188D):  # the ascension panel is already open
            self._ascend("panel_open")
            return True
        g.click(95, 90)  # ascension button
        g.sleep(400)
        g.click(93, 680)  # ascension tab
        g.sleep(400)
        # Known issue kept from the original: it checks y = 480 but clicks y = 600.
        if g.pixel_is(260, 480, 0x58188D):
            self._ascend("opened_panel")
            return True
        event("Ascend skipped", reason="ascend button not found")
        g.save_frame("ascend-not-found")
        return False

    def _ascend(self, path: str) -> None:
        g = self.game
        g.click(260, 600)  # ascend
        g.sleep(300)
        g.click(550, 580)  # confirm
        g.sleep(300)
        event("Ascended", path=path)
        self.auto_upgrade()
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `.venv/bin/python -m pytest -v`
Expected: `33 passed`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: port shop, quests and auto ascend" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Actions, `Runner` and the `run` command (first live run)

**Files:**
- Create: `idle_runner/actions.py`, `idle_runner/runner.py`, `tests/test_runner.py`
- Modify: `idle_runner/__main__.py`, `README.md`

**Interfaces:**
- Consumes: `Game`, `Shop`, `Repeater`, `Settings`, `event`, `GameUnavailable`.
- Produces:
  - Module `idle_runner.actions`:
    - Constants `SOUL_BONUS`, `RAGE_PILL`, `SOUL_COMPASS`, `DIMENSIONAL_STAFF`, `BIDIMENSIONAL_STAFF`.
    - `close_all(game)`, `soul_bonus_active(game) -> bool`, `buy_temp_item(game, color: int)`, `collect_minions(game)`.
  - `idle_runner.runner.Runner(game, settings, jumper)` with:
    - Methods `tick()`, `run()`, `rage_when_horde()`, `rage()`.
    - `_routine(name, fn) -> T`, which pauses the jumper, wraps `game.routine`, and returns `fn()`.
    - Attributes `last_slow`, `timer_buy`, `timer_ascend`, `buy_minutes`, `shop`, `focused`.
  - Later tasks insert their checks into `Runner.tick` at the anchors named in those tasks.

- [ ] **Step 1: Write the failing tests**

`tests/test_runner.py`:
```python
from dataclasses import replace

import pytest

from idle_runner.config import Settings
from idle_runner.game import Game
from idle_runner.runner import Runner
from idle_runner.x11 import GameUnavailable
from tests.fakes import OFFSET, FakeBackend


def test_silver_box_is_collected(game, fake, jumper, event_names) -> None:
    fake.paint(650, 36, 0xCA9700)
    Runner(game, Settings(), jumper).tick()

    assert (644, 49) in fake.clicks()
    assert "Silver Box Collected" in event_names()


def test_unfocused_game_gets_no_input_and_pause_is_logged_once(game, fake, jumper, event_names) -> None:
    fake.paint(650, 36, 0xCA9700)
    fake.active = False
    runner = Runner(game, Settings(), jumper)
    runner.tick()
    runner.tick()

    assert fake.clicks() == []
    assert event_names().count("Paused: game not focused") == 1


def test_megahorde_with_soul_bonus_crafts_and_rages(game, fake, jumper, event_names) -> None:
    fake.paint(385, 280, 0x140C1C)  # megahorde
    fake.paint(627, 150, 0xA86D0A)  # soul bonus
    Runner(game, replace(Settings(), craft_rage_pill=True), jumper).tick()

    assert (160, 100) in fake.clicks()  # crafting menu opened
    assert "r" in fake.taps()
    assert jumper.pauses >= 1
    names = event_names()
    assert "MegaHorde Rage with SoulBonus" in names and "MegaHorde Rage" in names


def test_no_rage_without_soul_bonus_when_disabled(game, fake, jumper) -> None:
    fake.paint(385, 280, 0x140C1C)
    Runner(game, replace(Settings(), disable_rage_without_soul_bonus=True), jumper).tick()

    assert "r" not in fake.taps()


def test_dimensional_staff_is_crafted_once_per_run(game, fake, jumper, event_names) -> None:
    fake.paint(385, 280, 0x140C1C)
    runner = Runner(game, replace(Settings(), craft_dimensional_staff=True), jumper)
    runner.tick()
    runner.tick()

    assert event_names().count("Trying to CraftingTemp Item") == 1


def test_auto_buy_runs_on_the_slow_tick_after_its_interval(game, fake, jumper, event_names) -> None:
    runner = Runner(game, replace(Settings(), auto_buy_upgrades=True, auto_buy_minutes=0.1), jumper)
    fake.t += 7_000
    runner.tick()

    assert "AutoUpgrade Active" in event_names()


def test_auto_ascend_runs_on_the_slow_tick_after_its_interval(game, fake, jumper, event_names) -> None:
    runner = Runner(game, replace(Settings(), auto_ascend=True, auto_ascend_minutes=0.1), jumper)
    fake.t += 7_000
    runner.tick()

    assert "Ascend skipped" in event_names()  # the fake screen has no ascend button


def test_focus_loss_mid_routine_aborts_without_more_input(game, fake, jumper, event_names) -> None:
    fake.paint(99, 113, 0xFFFF7A)  # minions are back

    def lose_focus(action: tuple) -> None:
        if action[0] == "click":
            fake.active = False

    fake.on_action = lose_focus
    with pytest.raises(GameUnavailable):
        Runner(game, Settings(), jumper).tick()

    assert fake.clicks() == [(95, 90)]
    assert "routine_abort" in event_names()


def test_run_warns_on_wrong_window_size_and_releases_keys_on_ctrl_c(jumper, event_names) -> None:
    fake = FakeBackend(width=1600, height=900)
    fake.stop_at = 1_000  # Ctrl+C after one virtual second
    Runner(Game(fake, offset=OFFSET), Settings(), jumper).run()

    names = event_names()
    assert "Window size mismatch" in names and "Bot stopped" in names
    assert ("key", "Up", False) in fake.actions and ("button", 1, False) in fake.actions
    assert jumper.running and jumper.stopped
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest tests/test_runner.py -v`
Expected: ERROR with `ModuleNotFoundError: No module named 'idle_runner.runner'`

- [ ] **Step 3: Implement `actions.py`**

`idle_runner/actions.py`:
```python
"""Small UI routines from Idle Runner.au3: CloseAll, CheckForSoulBonus, BuyTempItem, CollectMinion."""
from idle_runner.game import Game
from idle_runner.log import event

SOUL_BONUS = 0xA86D0A
RAGE_PILL = 0x871646
SOUL_COMPASS = 0x7D55D8
DIMENSIONAL_STAFF = 0xF37C55
BIDIMENSIONAL_STAFF = 0x526629


def close_all(game: Game) -> None:
    """Close a popup (red X button) if one is showing."""
    game.sleep(2000)  # known issue kept from the original: blinds the fast checks for 2 s
    if game.pixel_is(680, 593, 0xAF0000):
        game.click(780, 600)


def soul_bonus_active(game: Game) -> bool:
    return game.pixel_search(625, 143, 629, 214, SOUL_BONUS) is not None


def buy_temp_item(game: Game, color: int) -> None:
    """Craft the temporary item whose icon has `color`."""
    item = f"0x{color:06X}"
    event("Trying to CraftingTemp Item", item=item)
    game.click(160, 100)  # open the menu
    game.sleep(150)
    game.click(260, 690)  # temporary items tab
    game.sleep(150)
    found = game.pixel_search(43, 330, 625, 630, color)
    if found:
        game.click(*found)
        game.sleep(200)
        game.click(420, 156)  # craft
        event("CraftingTemp Item Active", item=item)
    else:
        event("CraftingTemp Item Failed, not enough materials", item=item)
    game.click(440, 690)  # close
    game.sleep(100)


def collect_minions(game: Game) -> None:
    game.click(95, 90)  # ascension button
    game.sleep(400)
    game.click(93, 680)  # ascension tab
    game.sleep(200)
    game.click(193, 680)  # ascension tree tab
    game.sleep(200)
    game.click(691, 680)  # unlabelled in the original
    game.sleep(200)
    game.click(332, 680)  # minions tab
    game.sleep(200)
    if game.pixel_search(370, 410, 910, 470, 0x11AA23, variation=9):  # daily bonus available
        game.click(320, 280, clicks=5)  # claim all
        game.sleep(200)
        game.click(320, 280, clicks=5)  # send all
        game.sleep(200)
        game.click(320, 180, clicks=5)  # claim the daily bonus
        game.sleep(200)
        event("Minions Collect with Daily Bonus")
    else:
        game.click(318, 182, clicks=5)  # claim all
        game.sleep(200)
        game.click(318, 182, clicks=5)  # send all
        game.sleep(200)
        event("Minions Collect")
    game.click(570, 694)  # exit
```

- [ ] **Step 4: Implement `runner.py`**

`idle_runner/runner.py`:
```python
"""The main loop, ported from Main() in Idle Runner.au3: fast checks every ~40 ms, slow checks every 5 s."""
from collections.abc import Callable

from idle_runner.actions import (BIDIMENSIONAL_STAFF, DIMENSIONAL_STAFF, RAGE_PILL, SOUL_COMPASS,
                                 buy_temp_item, close_all, collect_minions, soul_bonus_active)
from idle_runner.config import Settings
from idle_runner.game import Game
from idle_runner.log import event
from idle_runner.repeater import Repeater
from idle_runner.shop import Shop
from idle_runner.x11 import GameUnavailable


class Runner:
    def __init__(self, game: Game, settings: Settings, jumper: Repeater) -> None:
        self.game = game
        self.s = settings
        self.jumper = jumper
        self.shop = Shop(game)
        now = game.now()
        self.last_slow = now
        self.timer_buy = now
        self.timer_ascend = now
        self.buy_minutes: float = settings.auto_buy_minutes  # $iAutoBuyTempTimer
        # The original unticks these after one use; with a read-only config they apply once per run.
        self.dimensional_pending = settings.craft_dimensional_staff
        self.bidimensional_pending = settings.craft_bidimensional_staff
        self.focused = True

    def run(self) -> None:
        g = self.game
        event("Bot started", window=f"{g.size[0]}x{g.size[1]}")
        if g.size != (1280, 720):
            event("Window size mismatch", expected="1280x720", actual=f"{g.size[0]}x{g.size[1]}")
        self.jumper.resume()
        try:
            while True:
                try:
                    self.tick()
                except GameUnavailable as exc:
                    event("Game unavailable", reason=str(exc))
                    g.sleep(500)
        except KeyboardInterrupt:
            event("Bot stopped")
        finally:
            self.jumper.stop()
            g.release_all()

    def tick(self) -> None:
        """One iteration of the original Main() loop."""
        g, s = self.game, self.s
        g.sleep(40)
        if not g.is_active():
            if self.focused:
                event("Paused: game not focused")
                self.focused = False
            g.sleep(500)
            return
        if not self.focused:
            event("Resumed: game focused")
            self.focused = True

        # --- fast checks ---
        if g.pixel_is(650, 36, 0xCA9700):  # silver box
            event("Silver Box Collected")
            g.click(644, 49)
        if g.pixel_is(385, 280, 0x140C1C):  # megahorde
            self._routine("rage_when_horde", self.rage_when_horde)
        if g.pixel_is(1130, 610, 0xCBCB4C):  # a quest can be claimed
            self._routine("claim_quests", self.shop.claim_quests)
        if soul_bonus_active(g):  # rage during soul bonus
            g.tap("r")
        if g.pixel_is(99, 113, 0xFFFF7A):  # minions are back
            self._routine("collect_minions", lambda: collect_minions(g))

        # --- slow checks, every 5 s ---
        if g.now() - self.last_slow >= 5000:
            self.last_slow = g.now()
            close_all(g)
            if s.auto_buy_upgrades and g.now() - self.timer_buy > self.buy_minutes * 60_000:
                self.timer_buy = g.now()
                self.buy_minutes = s.auto_buy_minutes
                self.shop.loop_amount = 0
                self._routine("auto_upgrade", self.shop.auto_upgrade)
            if s.auto_ascend and g.now() - self.timer_ascend > s.auto_ascend_minutes * 60_000:
                self.timer_ascend = g.now()
                self._routine("auto_ascend", self.shop.auto_ascend)

    def rage_when_horde(self) -> None:
        g, s = self.game, self.s
        soul_bonus = soul_bonus_active(g)
        if soul_bonus:
            event("MegaHorde Rage with SoulBonus")
            if s.craft_rage_pill:
                buy_temp_item(g, RAGE_PILL)
            if s.craft_soul_bonus:
                buy_temp_item(g, SOUL_COMPASS)
        if soul_bonus or not s.disable_rage_without_soul_bonus:
            self.rage()

    def rage(self) -> None:
        g = self.game
        event("MegaHorde Rage")
        if self.dimensional_pending:
            buy_temp_item(g, DIMENSIONAL_STAFF)
            self.dimensional_pending = False
        if self.bidimensional_pending:
            buy_temp_item(g, BIDIMENSIONAL_STAFF)
            self.bidimensional_pending = False
        g.tap("r")

    def _routine[T](self, name: str, fn: Callable[[], T]) -> T:
        """SyncProcess(False) ... SyncProcess(True) around `fn`, with timing logs."""
        with self.jumper.paused(), self.game.routine(name):
            return fn()
```

- [ ] **Step 5: Add the `run` command**

In `idle_runner/__main__.py`, add the imports after `from idle_runner.png import write_png`:
```python
from idle_runner.config import load_settings
from idle_runner.game import Game
from idle_runner.log import setup_logging
from idle_runner.repeater import Repeater
from idle_runner.runner import Runner
```
Add this function before `def main(`:
```python
def run_bot(config_path: Path) -> int:
    if not config_path.exists():
        print(f"error: {config_path} not found; copy config.example.toml to {config_path} and edit it",
              file=sys.stderr)
        return 1
    settings = load_settings(config_path)
    log_dir = Path(settings.log_dir)
    setup_logging(log_dir, settings.log_level)
    backend = X11Backend(settings.window_name)
    game = Game(backend, (settings.offset_x, settings.offset_y), settings.color_tolerance,
                log_dir / "frames" if settings.save_frames else None)
    jumper = Repeater(game, ("Up", "Right"), settings.jump_interval_ms, "jumper")
    Runner(game, settings, jumper).run()
    return 0

```
Insert before the line `    args = parser.parse_args(argv)`:
```python
    run = sub.add_parser("run", help="run the bot (Ctrl+C to stop)")
    run.add_argument("--config", type=Path, default=Path("config.toml"))

```
Insert after the `stats` branch (after its `return 0`):
```python
        if args.command == "run":
            return run_bot(args.config)
```
Replace:
```python
    except GameUnavailable as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
```
with:
```python
    except (GameUnavailable, ValueError) as exc:  # ValueError: invalid config.toml
        print(f"error: {exc}", file=sys.stderr)
        return 1
```

- [ ] **Step 6: Run the tests to see them pass**

Run: `.venv/bin/python -m pytest -v`
Expected: `42 passed`

- [ ] **Step 7: Document running, logs and differences**

Append to `README.md`:
````markdown
## Running
```bash
cp config.example.toml config.toml   # then edit it
.venv/bin/python -m idle_runner run
```
The bot only sends input while the Idle Slayer window is focused. Alt-tab away to pause it and focus the game again to resume. Stop it with Ctrl+C in the terminal.

## Logs
- `logs/idle_runner.log`: human-readable, millisecond timestamps. With `log_level = "DEBUG"` it also traces every pixel search.
- `logs/events.jsonl`: one JSON object per event (`ts`, `event`, extra fields), for analysis.
- `logs/frames/`: PNG screenshots at minigame start/end, safety-net timeouts (`stuck-*`) and crashes (`crash-*`).
- `.venv/bin/python -m idle_runner stats`: event counts and routine durations.

## Differences from the AutoIt original
- No focus stealing and no global hotkeys: focus = run, alt-tab = pause, Ctrl+C = stop.
- One-shot crafts (Dimensional/Bidimensional staff) apply once per run. The portal rotation restarts from `circle_portals_count`.
- Loops that could hang forever give up after a timeout and log a `stuck` event with a screenshot.
- The jumper pauses immediately when a menu routine starts.
- Fixed:
  - the Ascending Heights right-edge clamp;
  - chest-hunt stats;
  - clicks outside the window (now refused).
- The Knight boss stays disabled, as in the original.
````

- [ ] **Step 8: Live run (needs the user)**

1. Copy the config and enable the core features: `cp config.example.toml config.toml`, then set `auto_buy_upgrades = true` and `auto_buy_minutes = 1` in `config.toml`.
2. Ask the user to focus the game, then run `.venv/bin/python -m idle_runner run`.
3. Check, with the user watching:
   - The character jumps and boosts continuously.
   - Within about 1 minute a buy pass runs: the shop opens, upgrades and equipment are bought, and the shop closes. `logs/events.jsonl` shows `AutoUpgrade Done` with non-zero counts.
   - Alt-tabbing to the terminal logs `Paused: game not focused` and stops all input. Refocusing logs `Resumed`.
   - Ctrl+C logs `Bot stopped` and no key stays pressed.
4. Run `.venv/bin/python -m idle_runner stats` and confirm the counts and `auto_upgrade` durations print.

If buying misbehaves, keep the frames and the log lines and fix the coordinates or offset before continuing. Every fix must cite the AutoIt line it corresponds to.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: main loop, actions and run command" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Circle portals

**Files:**
- Create: `idle_runner/portals.py`, `tests/test_portals.py`
- Modify: `idle_runner/runner.py`, `tests/test_runner.py`

**Interfaces:**
- Consumes: `Game`, `STUCK_MS`, `scroll_to_top` (Task 6), `event`.
- Produces: `PORTAL_COLORS: dict[int, int]`, `portal_ready(game) -> bool`, `take_portal(game, count: int) -> None`; `Runner.portal_count: int`.

- [ ] **Step 1: Write the failing tests**

`tests/test_portals.py`:
```python
from idle_runner.portals import portal_ready, take_portal


def test_not_ready_when_the_portal_button_is_hidden(game) -> None:
    assert not portal_ready(game)


def test_not_ready_while_the_countdown_shows(game, fake) -> None:
    fake.paint(1180, 166, 0x830399)
    fake.paint(1160, 150, 0xFFFFFF)  # countdown text
    assert not portal_ready(game)


def test_ready_when_the_button_shows_without_countdown(game, fake) -> None:
    fake.paint(1180, 166, 0x290130)
    assert portal_ready(game)


def test_take_portal_clicks_the_destination(game, fake, event_names) -> None:
    fake.paint(470, 300, 0x00F8B5)  # factory = destination 7
    take_portal(game, 7)

    assert (770, 300) in fake.clicks()
    assert "CirclePortals" in event_names()


def test_take_portal_gives_up_when_the_destination_is_missing(game, fake, event_names) -> None:
    take_portal(game, 1)

    assert (600, 600) in fake.clicks()
    assert "Portal destination not found" in event_names()
```

Add `import idle_runner.runner as runner_module` to the imports at the top of `tests/test_runner.py` (later tasks reuse it), then append:
```python
def test_circle_portals_rotate_destinations(game, fake, jumper, monkeypatch) -> None:
    taken = []
    monkeypatch.setattr(runner_module, "portal_ready", lambda g: True)
    monkeypatch.setattr(runner_module, "take_portal", lambda g, count: taken.append(count))
    runner = Runner(game, replace(Settings(), circle_portals=True, circle_portals_count=9), jumper)
    fake.t += 6_000
    runner.tick()
    fake.t += 6_000
    runner.tick()

    assert taken == [9, 1]
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest tests/test_portals.py tests/test_runner.py -v`
Expected: ERROR with `ModuleNotFoundError: No module named 'idle_runner.portals'`

- [ ] **Step 3: Implement `portals.py`**

`idle_runner/portals.py`:
```python
"""CirclePortals from Idle Runner.au3: take the next portal destination whenever the portal is ready."""
from idle_runner.game import STUCK_MS, Game
from idle_runner.log import event
from idle_runner.shop import SCROLLBAR_GRAY, scroll_to_top

PORTAL_COLORS = {
    1: 0x00CBF8,  # hills
    2: 0xBD4348,  # hot desert
    3: 0x009D93,  # jungle
    4: 0x6FF5F8,  # frozen fields
    5: 0xB362C7,  # funky
    6: 0x000173,  # modern city
    7: 0x00F8B5,  # factory
    8: 0xE198BF,  # valley
    9: 0x4F0085,  # castle
}


def portal_ready(game: Game) -> bool:
    """The portal button is visible and shows no countdown."""
    visible = game.pixel_is(1180, 166, 0x830399) or game.pixel_is(1180, 166, 0x290130)
    return visible and game.pixel_search(1154, 144, 1210, 155, 0xFFFFFF, variation=9) is None


def take_portal(game: Game, count: int) -> None:
    color = PORTAL_COLORS[count]
    game.click(1180, 150)  # portal button
    game.sleep(300)
    game.move(867, 300)  # over the destination list's scrollbar
    game.sleep(200)
    scroll_to_top(game, 875, 250, "portals")
    game.sleep(400)
    deadline = game.now() + STUCK_MS
    while True:
        found = game.pixel_search(470, 230, 470, 540, color, variation=10)
        if found is None:
            if not game.pixel_is(875, 536, SCROLLBAR_GRAY):  # bottom of the list: give up
                event("Portal destination not found", count=count)
                game.save_frame("portal-not-found")
                game.click(600, 600)
                break
            game.sleep(100)
            game.move(867, 300)
            game.wheel(up=False, notches=1)
        else:
            game.sleep(300)
            game.wheel(up=False, notches=1)
            game.wheel(up=False, notches=1)
            game.click(found[0] + 300, found[1])  # the destination's travel button
            break
        if game.now() > deadline:
            game.stuck("portals", count=count)
            break
    event("CirclePortals", count=count)
    game.sleep(10_000)
```

- [ ] **Step 4: Wire it into the runner**

In `idle_runner/runner.py`, add the import after the `idle_runner.log` import:
```python
from idle_runner.portals import portal_ready, take_portal
```
In `Runner.__init__`, insert after the `self.buy_minutes` line:
```python
        self.portal_count = settings.circle_portals_count
```
In `Runner.tick`, insert before the line `            if s.auto_buy_upgrades and g.now() - self.timer_buy > self.buy_minutes * 60_000:`:
```python
            if s.circle_portals and portal_ready(g):
                self._routine("circle_portals", lambda: take_portal(g, self.portal_count))
                self.portal_count = self.portal_count % 9 + 1
```

- [ ] **Step 5: Run the tests to see them pass**

Run: `.venv/bin/python -m pytest -v`
Expected: `48 passed`

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: port circle portals" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Chest hunt

**Files:**
- Create: `idle_runner/minigames/__init__.py`, `idle_runner/minigames/chest_hunt.py`, `tests/minigames/__init__.py`, `tests/minigames/test_chest_hunt.py`
- Modify: `idle_runner/runner.py`, `tests/test_runner.py`

**Interfaces:**
- Consumes: `Game`, `Point`, `STUCK_MS`, `event`.
- Produces:
  - Enums `Chest` and `State`.
  - `updated_state(count, state, chest, perfect, no_reinforced) -> State`
  - `perfect_state(chest, state, count) -> State | None`
  - `find_saver(game) -> Point | None`
  - `process_grid(game, saver, no_lockpicking, perfect, no_reinforced) -> None`
  - `open_chest(game, x, y, no_lockpicking) -> Chest`
  - `open_life_saver(game, saver, no_lockpicking) -> None`
  - `chest_hunt(game, no_lockpicking: bool, perfect: bool, no_reinforced: bool) -> None`

- [ ] **Step 1: Write the failing tests**

`idle_runner/minigames/__init__.py`:
```python
"""Minigames ported from Libraries/*.au3."""
```
`tests/minigames/__init__.py`: empty file.

`tests/minigames/test_chest_hunt.py`:
```python
from idle_runner.minigames.chest_hunt import Chest, State, chest_hunt, find_saver, process_grid, updated_state


def test_normal_strategy_opens_the_life_saver_after_the_second_chest() -> None:
    assert updated_state(0, State.NO_MIMIC, Chest.REWARD, False, False) == State.NO_MIMIC
    assert updated_state(0, State.NO_MIMIC, Chest.MIMIC, False, False) == State.ONE_MIMIC
    assert updated_state(1, State.ONE_MIMIC, Chest.REWARD, False, False) == State.OPEN_LIFE_SAVER


def test_2x_chest_always_opens_the_life_saver() -> None:
    assert updated_state(5, State.NO_MIMIC, Chest.X2, True, False) == State.OPEN_LIFE_SAVER


def test_normal_state_is_final() -> None:
    assert updated_state(3, State.NORMAL, Chest.X2, False, False) == State.NORMAL


def test_without_reinforced_crystal_saver_the_life_saver_opens_first() -> None:
    assert updated_state(0, State.NO_MIMIC, Chest.REWARD, False, True) == State.OPEN_LIFE_SAVER


def test_perfect_strategy_thresholds() -> None:
    assert updated_state(1, State.NO_MIMIC, Chest.MIMIC, True, False) == State.ONE_MIMIC
    assert updated_state(1, State.ONE_MIMIC, Chest.MIMIC, True, False) == State.TWO_MIMICS
    assert updated_state(12, State.NO_MIMIC, Chest.REWARD, True, False) == State.NO_MIMIC
    assert updated_state(13, State.NO_MIMIC, Chest.REWARD, True, False) == State.OPEN_LIFE_SAVER
    assert updated_state(15, State.ONE_MIMIC, Chest.REWARD, True, False) == State.OPEN_LIFE_SAVER
    assert updated_state(21, State.TWO_MIMICS, Chest.REWARD, True, False) == State.OPEN_LIFE_SAVER


def test_find_saver(game, fake) -> None:
    fake.paint(377, 325, 0xFFEB04)  # row 0, column 2 (x = 185 + 2 * 95)
    assert find_saver(game) == (375, 325)


def test_process_grid_skips_the_saver_and_stops_at_the_end_screen(game, fake) -> None:
    def end_after_two_clicks(action: tuple) -> None:
        if action[0] == "click" and len(fake.clicks()) == 2:
            fake.paint(550, 694, 0xAF0000)  # close button = chest hunt over

    fake.on_action = end_after_two_clicks
    process_grid(game, (280, 325), no_lockpicking=False, perfect=False, no_reinforced=False)

    assert fake.clicks() == [(218, 302), (408, 302)]  # column 1 (the saver) was skipped


def test_chest_hunt_without_saver_still_finishes(game, fake, event_names) -> None:
    fake.paint(550, 694, 0xAF0000)
    chest_hunt(game, no_lockpicking=True, perfect=False, no_reinforced=False)

    assert fake.clicks()[-1] == (643, 693)
    assert "Chesthunt saver not found" in event_names()
```

Append to `tests/test_runner.py`:
```python
def test_chest_hunt_is_dispatched(game, fake, jumper, monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(runner_module, "chest_hunt", lambda g, *flags: calls.append(flags))
    fake.paint(187, 296, 0xFFBB31)
    fake.paint(187, 303, 0xF68F37)
    Runner(game, Settings(), jumper).tick()

    assert calls == [(True, False, False)]
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest tests/minigames/test_chest_hunt.py -v`
Expected: ERROR with `ModuleNotFoundError: No module named 'idle_runner.minigames.chest_hunt'`

- [ ] **Step 3: Implement `chest_hunt.py`**

`idle_runner/minigames/chest_hunt.py`:
```python
"""Chest hunt, ported from Libraries/ChestHunt.au3."""
from enum import IntEnum

from idle_runner.game import STUCK_MS, Game, Point
from idle_runner.log import event

GRID_X, GRID_Y, STEP = 185, 325, 95  # chest grid: 3 rows x 10 columns


class Chest(IntEnum):
    REWARD = 0
    MIMIC = 1
    X2 = 2
    END = 3
    LIFE_SAVER = 4


class State(IntEnum):
    NO_MIMIC = 0
    ONE_MIMIC = 1
    TWO_MIMICS = 2
    OPEN_LIFE_SAVER = 3
    NORMAL = 4


def updated_state(count: int, state: State, chest: Chest, perfect: bool, no_reinforced: bool) -> State:
    """GetUpdatedState: what to do after opening chest number `count` (0-based)."""
    if state == State.NORMAL or chest == Chest.LIFE_SAVER:  # after the life saver: just open chests
        return State.NORMAL
    if chest == Chest.X2:  # always open the life saver after a 2x chest
        return State.OPEN_LIFE_SAVER
    if perfect:
        perfect_next = perfect_state(chest, state, count)
        if perfect_next is not None:
            return perfect_next
    if count == 0:
        if no_reinforced:
            return State.OPEN_LIFE_SAVER
        if chest == Chest.REWARD:
            return State.NO_MIMIC
        if chest == Chest.MIMIC:
            return State.ONE_MIMIC
    elif count == 1:
        if not perfect:  # normal strategy: open the life saver after the 2nd chest
            return State.OPEN_LIFE_SAVER
        if state == State.NO_MIMIC:
            if chest == Chest.REWARD:
                return State.NO_MIMIC
            if chest == Chest.MIMIC:
                return State.ONE_MIMIC
        elif state == State.ONE_MIMIC:
            if chest == Chest.REWARD:
                return State.ONE_MIMIC
            if chest == Chest.MIMIC:
                return State.TWO_MIMICS
    return state


def perfect_state(chest: Chest, state: State, count: int) -> State | None:
    """PerfectChestHuntState: ignore the life saver until a 2x is found or enough chests are open."""
    if chest == Chest.REWARD and (state, count) in (
            (State.NO_MIMIC, 13), (State.ONE_MIMIC, 15), (State.TWO_MIMICS, 21)):
        return State.OPEN_LIFE_SAVER
    return None


def find_saver(game: Game) -> Point | None:
    for row in range(3):
        for col in range(10):
            x, y = GRID_X + col * STEP, GRID_Y + row * STEP
            if game.pixel_search(x, y - 1, x + 5, y, 0xFFEB04):
                return x, y
    return None


def open_chest(game: Game, x: int, y: int, no_lockpicking: bool) -> Chest:
    game.click(x + 33, y - 23)
    game.sleep(1500 if no_lockpicking else 550)
    if game.pixel_is(550, 694, 0xAF0000):  # close button: the hunt is over
        return Chest.END
    if game.pixel_is(500, 210, 0x00FF00):  # 2x
        game.sleep(1000)
        return Chest.X2
    if game.pixel_is(434, 211, 0xFF0000):  # mimic
        game.sleep(2500 if no_lockpicking else 1500)
        return Chest.MIMIC
    return Chest.REWARD


def open_life_saver(game: Game, saver: Point | None, no_lockpicking: bool) -> None:
    if saver is None:  # the original clicked at (33, -23) here
        event("Life saver skipped: saver not found")
        return
    game.click(saver[0] + 33, saver[1] - 23)
    game.sleep(1500 if no_lockpicking else 550)
    event("Life saver opened")


def process_grid(game: Game, saver: Point | None, no_lockpicking: bool, perfect: bool,
                 no_reinforced: bool) -> None:
    count = 0
    state = State.NO_MIMIC
    for row in range(3):
        for col in range(10):
            x, y = GRID_X + col * STEP, GRID_Y + row * STEP
            if (x, y) == saver:
                continue
            chest = open_chest(game, x, y, no_lockpicking)
            if chest == Chest.END:
                return
            state = updated_state(count, state, chest, perfect, no_reinforced)
            event("Chest opened", index=count, row=row, col=col, result=chest.name, state=state.name)
            if state == State.OPEN_LIFE_SAVER:
                open_life_saver(game, saver, no_lockpicking)
                state = State.NORMAL
            count += 1


def chest_hunt(game: Game, no_lockpicking: bool, perfect: bool, no_reinforced: bool) -> None:
    event("Chesthunt Started", perfect_strategy=perfect)
    game.sleep(4000 if no_lockpicking else 2000)
    saver = find_saver(game)
    if saver is None:
        event("Chesthunt saver not found")
        game.save_frame("chesthunt-no-saver")
    process_grid(game, saver, no_lockpicking, perfect, no_reinforced)

    perfect_found = False
    attempts = 0
    deadline = game.now() + 5 * STUCK_MS
    while True:  # wait for the close button, clicking the perfect-chest reward if it shows
        game.sleep(50)
        attempts += 1
        if game.pixel_is(550, 694, 0xAF0000):
            break
        if game.pixel_is(457, 439, 0xF68F37):
            perfect_found = True
            game.click(457, 439)
        if attempts > 200:
            event("Chesthunt blocked, opening the grid again")
            game.save_frame("chesthunt-blocked")
            process_grid(game, saver, no_lockpicking, perfect, no_reinforced)
            attempts = 0
        if game.now() > deadline:
            game.stuck("chest_hunt.end_screen")
            break
    if perfect_found:
        event("Perfect ChestHunt Completed")
    game.click(643, 693)
```

- [ ] **Step 4: Wire it into the runner**

In `idle_runner/runner.py`, add the import after the `idle_runner.log` import:
```python
from idle_runner.minigames.chest_hunt import chest_hunt
```
In `Runner.tick`, insert before the line `        # --- slow checks, every 5 s ---`:
```python
        if g.pixel_is(187, 296, 0xFFBB31) and g.pixel_is(187, 303, 0xF68F37):  # chest hunt
            self._routine("chest_hunt", lambda: chest_hunt(
                g, s.no_lockpicking, s.perfect_chest_hunt, s.no_reinforced_crystal_saver))

```

- [ ] **Step 5: Run the tests to see them pass**

Run: `.venv/bin/python -m pytest -v`
Expected: `57 passed`

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: port chest hunt with per-chest logging" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Bonus stages (and the shared slider)

**Files:**
- Create: `idle_runner/minigames/common.py`, `idle_runner/minigames/bonus_stage.py`, `tests/minigames/test_common.py`, `tests/minigames/test_bonus_stage.py`
- Modify: `idle_runner/runner.py`, `tests/test_runner.py`

**Interfaces:**
- Consumes: `Game`, `STUCK_MS`, `event`.
- Produces:
  - In `common`: `slider(game) -> None` and `slide_until_gone(game, where: str, left, top, right, bottom, color) -> None`.
  - In `bonus_stage`, the public API:
    - `bonus_stage(game, skip: bool) -> None`
    - `run_bs2(game, sb: bool) -> None`
    - `run_bs3(game, sb: bool, sections=BS3_SECTIONS) -> None`
  - In `bonus_stage`, the helpers:
    - `stage_fail(game, n: int) -> bool`
    - `bs3_fail(game, sb: bool) -> bool`
    - `collect_loot_bs3(game, sb, count=25, stop_early=True) -> bool`
  - In `bonus_stage`, the tables: `Bs2Section` and the tuples `BS2_SECTIONS`, `BS2_SB_SECTIONS`, `BS3_SECTIONS`.

- [ ] **Step 1: Write the failing tests**

`tests/minigames/test_common.py`:
```python
from idle_runner.minigames.common import slider
from tests.fakes import OFFSET


def test_slider_drags_the_handle_across(game, fake) -> None:
    fake.paint(442, 560, 0x007E00)  # handle found by the "top left" search
    slider(game)

    assert fake.clicks() == [(840, 560)]                       # pressed at the drag start
    assert fake.pointer == (450 - OFFSET[0], 560 - OFFSET[1])  # released at the drag end
```

`tests/minigames/test_bonus_stage.py`:
```python
from idle_runner.minigames.bonus_stage import bonus_stage, run_bs2, run_bs3


def test_bs2_stops_and_logs_when_the_stage_fails(game, fake, event_names) -> None:
    fake.paint(716, 600, 0xAF0000)  # the fail screen's close button
    run_bs2(game, sb=False)

    names = event_names()
    assert "BonusStage2" in names and "BonusStage2 Failed" in names
    assert "BonusStage2 Section 1 Complete" not in names
    assert (716, 600) in fake.clicks()


def test_bs3_retries_one_failed_section_once(game) -> None:
    calls = []
    pending_failures = {1: 1}  # section index 1 fails once

    def make(index: int):
        def section(g, sb: bool) -> bool:
            calls.append(index)
            if pending_failures.get(index):
                pending_failures[index] -= 1
                return False
            return True
        return section

    run_bs3(game, False, sections=tuple(make(i) for i in range(4)))

    assert calls == [0, 1, 1, 2, 3]


def test_bs3_gives_up_after_the_second_failure(game) -> None:
    calls = []

    def ok(g, sb: bool) -> bool:
        calls.append("ok")
        return True

    def bad(g, sb: bool) -> bool:
        calls.append("bad")
        return False

    run_bs3(game, False, sections=(ok, bad, ok, ok))

    assert calls == ["ok", "bad", "bad"]


def test_skip_bonus_stage_waits_for_the_fail_screen(game, fake, event_names) -> None:
    fake.paint(716, 600, 0xAF0000)
    bonus_stage(game, skip=True)

    names = event_names()
    assert "Do nothing BonusStage Active" in names and "BonusStage2 Failed" in names
```

Append to `tests/test_runner.py`:
```python
def test_bonus_stage_is_dispatched_on_the_slow_tick(game, fake, jumper, monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(runner_module, "bonus_stage", lambda g, skip: calls.append(skip))
    fake.paint(660, 254, 0xFFE737)
    fake.paint(638, 236, 0xFFBB31)
    runner = Runner(game, replace(Settings(), skip_bonus_stage=True), jumper)
    fake.t += 6_000
    runner.tick()

    assert calls == [True]
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest tests/minigames -v`
Expected: ERROR with `ModuleNotFoundError: No module named 'idle_runner.minigames.common'`

- [ ] **Step 3: Implement `common.py`**

`idle_runner/minigames/common.py`:
```python
"""Shared minigame helpers from Libraries/Common.au3."""
from idle_runner.game import STUCK_MS, Game

# Where the green slider handle can be: (search left, search right, y, drag from x, drag to x).
SLIDER_POSITIONS = (
    (441, 443, 560, 840, 450),  # top left
    (441, 443, 620, 840, 450),  # bottom left
    (847, 850, 560, 450, 840),  # top right
    (847, 850, 620, 450, 840),  # bottom right
)


def slider(game: Game) -> None:
    """Slider(): drag the green handle to start a minigame."""
    for left, right, y, x_from, x_to in SLIDER_POSITIONS:
        if game.pixel_search(left, y, right, y, 0x007E00):
            game.move(x_from, y)
            game.drag(x_from, y, x_to, y)
            return


def slide_until_gone(game: Game, where: str, left: int, top: int, right: int, bottom: int, color: int) -> None:
    """`Do Slider() / Sleep(500) / Until PixelSearch(...) fails`, with a safety net."""
    deadline = game.now() + STUCK_MS
    while True:
        slider(game)
        game.sleep(500)
        if game.pixel_search(left, top, right, bottom, color) is None:
            return
        if game.now() > deadline:
            game.stuck(f"{where}.slider")
            return
```

- [ ] **Step 4: Implement `bonus_stage.py`**

`idle_runner/minigames/bonus_stage.py`:
```python
"""Bonus stages 2 and 3, ported from Libraries/BonusStage.au3.

The jump sequences are `cSend(press_ms, post_ms)` pairs copied verbatim. BS2 is table-driven
(its four sections share one shape); BS3 interleaves waits for on-screen markers, so it stays
function-per-section like the original.
"""
from collections.abc import Callable
from dataclasses import dataclass

from idle_runner.game import STUCK_MS, Game
from idle_runner.log import event
from idle_runner.minigames.common import slide_until_gone

Moves = tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class Bs2Section:
    sync: tuple[int, int, int, int, int]  # find_until(left, top, right, bottom, color) before starting
    sync_sleep: int                       # extra wait after the sync marker shows up
    moves: Moves                          # the jump sequence
    fail_check_before_collect: bool
    collect_hold: tuple[int, int] | None  # cSend() before the collection taps
    collect_taps: int                     # Send("{Up}") + Sleep(500), repeated


S1_SYNC = (220, 465, 220, 465, 0xCFBCB8)
S2_SYNC = (780, 513, 780, 513, 0xBB26DF)
S3_SYNC = (151, 465, 220, 465, 0xCFBCB8)
S4_SYNC = (250, 472, 100, 250, 0x0D2030)

S2_MOVES: Moves = (
    (156, 719), (47, 687), (360, 1390), (485, 344), (406, 749), (78, 600), (94, 900), (109, 954),
    (31, 672), (515, 1344), (484, 297), (406, 749), (78, 600), (94, 900), (109, 954), (31, 672),
    (515, 1344), (469, 219), (297, 750), (156, 500), (110, 3000), (360, 2984), (531, 2313),
)

BS2_SECTIONS = (
    Bs2Section(S1_SYNC, 200, (
        (94, 1640), (32, 1218), (94, 600), (109, 1828), (63, 640), (47, 688), (78, 1906),
        (141, 1625), (47, 3187), (47, 734), (47, 750), (78, 1203), (110, 5000),
    ), True, (40, 5000), 17),
    Bs2Section(S2_SYNC, 0, S2_MOVES, True, (350, 1000), 20),
    Bs2Section(S3_SYNC, 0,
               ((109, 1203), (31, 641), (47, 1578), (47, 2437)) * 3 + ((109, 1203), (31, 641), (47, 5125)),
               True, (900, 200), 20),
    Bs2Section(S4_SYNC, 200, (
        (32, 1375), (641, 690), (41, 1375), (41, 1374), (641, 690), (41, 1373), (41, 2500), (31, 809),
        (41, 1375), (41, 1374), (641, 690), (41, 1373), (41, 1372), (641, 690), (41, 1371),
        (41, 0),  # "extra jump just in case"
    ), False, None, 23),
)

BS2_SB_SECTIONS = (
    Bs2Section(S1_SYNC, 200,
               ((94, 1640), (47, 2072), (187, 688), (31, 672), (31, 1700)) * 2 + ((94, 5000),),
               True, (40, 2500), 19),
    Bs2Section(S2_SYNC, 0, S2_MOVES, True, (350, 1000), 20),
    Bs2Section(S3_SYNC, 0,
               ((109, 1203), (31, 641), (47, 1200), (1, 3100)) * 3 + ((109, 1203), (31, 641), (47, 5125)),
               True, (900, 200), 20),
    Bs2Section(S4_SYNC, 200, (
        (32, 2800), (31, 809), (41, 1200), (100, 900), (641, 500),
        (31, 850), (41, 770), (641, 400),
        (31, 850), (41, 870), (641, 300),
        (31, 850), (41, 790), (641, 400),
        (31, 850), (41, 840), (641, 300),
        (31, 850), (41, 840), (641, 300),
    ), False, None, 23),
)


def holds(game: Game, moves: Moves) -> None:
    for press_ms, post_ms in moves:
        game.hold(press_ms, post_ms)


def stage_fail(game: Game, n: int) -> bool:
    """BonusStageFail: the fail screen is up; close it."""
    if game.pixel_is(716, 600, 0xAF0000):
        game.click(716, 600)
        event(f"BonusStage{n} Failed")
        return True
    return False


def bonus_stage(game: Game, skip: bool) -> None:
    event("Start of BonusStage")
    game.sleep(200)
    is_bs3 = game.pixel_search(160, 498, 200, 498, 0x16171F) is not None
    game.save_frame("bonus-stage-start")
    slide_until_gone(game, "bonus_stage", 775, 448, 775, 448, 0xFFFFFF)
    if skip:
        do_nothing(game, 3 if is_bs3 else 2)
        return
    game.sleep(3900)
    spirit_boost = game.pixel_is(454, 91, 0xE1E0E2)
    event("BonusStage detected", stage=3 if is_bs3 else 2, spirit_boost=spirit_boost)
    if is_bs3:
        run_bs3(game, spirit_boost)
    else:
        run_bs2(game, spirit_boost)
    game.save_frame("bonus-stage-end")


def do_nothing(game: Game, n: int) -> None:
    """BonusStageDoNothing: let the timer run out, then close the fail screen."""
    event("Do nothing BonusStage Active")
    deadline = game.now() + 3 * STUCK_MS
    while True:
        game.sleep(200)
        if stage_fail(game, n):
            return
        if game.now() > deadline:
            game.stuck("bonus_stage.do_nothing")
            return


# --- Bonus stage 2 ---

def run_bs2(game: Game, sb: bool) -> None:
    tag = "BonusStage2SB" if sb else "BonusStage2"
    event(tag)
    for number, section in enumerate(BS2_SB_SECTIONS if sb else BS2_SECTIONS, start=1):
        if game.find_until(*section.sync) is None:  # the original carries on regardless
            event("BonusStage sync timeout", stage=tag, section=number)
            game.save_frame(f"{tag}-sync-{number}")
        game.sleep(section.sync_sleep)
        holds(game, section.moves)
        if section.fail_check_before_collect and stage_fail(game, 2):
            return
        if section.collect_hold:
            game.hold(*section.collect_hold)
        for _ in range(section.collect_taps):
            game.tap("Up")
            game.sleep(500)
        if stage_fail(game, 2):
            return
        event(f"{tag} Section {number} Complete")


# --- Bonus stage 3 ---

def bs3_tag(sb: bool) -> str:
    return "BonusStage3SB" if sb else "BonusStage3"


def bs3_fail(game: Game, sb: bool) -> bool:
    """BonusStage3Fail: retry if offered, otherwise detect that the stage is over."""
    tag = bs3_tag(sb)
    if game.pixel_is(615, 590, 0x00A400):  # retry button
        game.click(560, 600)
        event(f"{tag} Retry")
        game.sleep(1000)
        return True
    if (game.pixel_is(1130, 604, 0x989898)                             # items icon
            or game.pixel_search(115, 570, 125, 590, 0x09439B)          # boost icon
            or game.pixel_search(115, 570, 125, 590, 0x099B66)):        # wind rush icon
        event(f"{tag} Failed")
        return True
    return False


def wall_jump(game: Game, count: int = 5, sleep_ms: int = 50) -> None:
    for _ in range(count):
        game.hold(30, sleep_ms)


def collect_loot_bs3(game: Game, sb: bool, count: int = 25, stop_early: bool = True) -> bool:
    if bs3_fail(game, sb):
        return False
    for i in range(1, count + 1):
        if stop_early and i > 8:
            if game.find_until(1100, 240, 1100, 440, 0x8D87A2, 480):  # the next section already started
                break
        else:
            game.sleep(500)
        game.hold(0, 0)
    return not bs3_fail(game, sb)


def bs3_section1(game: Game, sb: bool) -> bool:
    game.find_until(520, 200, 580, 250, 0xFFFFFF)
    game.sleep(360)
    holds(game, ((140, 530), (70, 640), (80, 740), (150, 765), (65, 625), (65, 500)))
    game.find_until(540, 335, 555, 360, 0xFFFFFF, 700)
    holds(game, ((150, 750), (200, 200)))
    game.find_until(390, 230, 410, 250, 0xFFFFFF, 3500)
    holds(game, ((130, 545), (70, 620), (80, 400)))
    game.find_until(500, 200, 515, 250, 0xFFFFFF, 1500)
    holds(game, ((150, 755), (65, 625), (65, 500)))
    game.find_until(540, 335, 555, 360, 0xFFFFFF, 700)
    holds(game, ((150, 740), (200, 1490), (110, 580), (65, 640), (80, 740), (150, 765), (130, 560), (70, 650)))
    game.sleep(800)
    if not collect_loot_bs3(game, sb, 21):
        return False
    event(f"{bs3_tag(sb)} Section 1 Complete")
    return True


def bs3_section2(game: Game, sb: bool) -> bool:
    game.find_until(306, 200, 309, 275, 0xFFFFFF)
    for _ in range(2):
        holds(game, ((80, 440), (95, 660), (105, 500)))
        game.find_until(475, 445, 482, 475, 0xFFFFFF, 1000)
        holds(game, ((79, 601), (63, 980), (82, 440), (95, 660), (48, 750)))
        game.find_until(515, 265, 522, 285, 0xFFFFFF, 1200)
        game.hold(63, 500)
        wall_jump(game, 1)
        game.sleep(80)
        wall_jump(game, 1)
        game.sleep(300)
        wall_jump(game, 4)
        game.find_until(306, 200, 309, 275, 0xFFFFFF, 1000)
    holds(game, ((80, 440), (95, 660)))
    if not collect_loot_bs3(game, sb):
        return False
    event(f"{bs3_tag(sb)} Section 2 Complete")
    return True


def bs3_section3(game: Game, sb: bool) -> bool:
    upper_way = False
    game.find_until(280, 385, 330, 435, 0xFFFFFF)
    game.sleep(600)
    for _ in range(2):
        if upper_way:
            wall_jump(game)
            upper_way = False
        else:
            game.hold(120, 100)
            game.find_until(205, 395, 215, 410, 0xFFFFFF, 780)
            game.hold(95, 225)
            wall_jump(game)
        game.sleep(2000)
        game.hold(300, 500)
        wall_jump(game)
        game.find_until(205, 395, 215, 410, 0xFFFFFF, 900)
        # The original wraps the rest in `If $iX < 3`, which is always true for its 2 iterations.
        game.hold(95, 250)
        wall_jump(game, 1, 715)
        wall_jump(game, 6)
        if game.find_until(300, 415, 330, 435, 0xFFFFFF, 1000 if sb else 2500) is None:
            upper_way = True
        else:
            game.sleep(2500)
        game.sleep(150)
    if not collect_loot_bs3(game, sb):
        return False
    event(f"{bs3_tag(sb)} Section 3 Complete")
    return True


def bs3_section4(game: Game, sb: bool) -> bool:
    game.find_until(330, 170, 380, 195, 0xFFFFFF)
    if not sb:
        for _ in range(5):
            holds(game, ((300, 600), (300, 420), (35, 748), (35, 540), (35, 1160)))
    else:
        for _ in range(14):
            game.hold(110, 1180)
        game.hold(300, 300)
    if not collect_loot_bs3(game, sb, 25, stop_early=False):
        return False
    event(f"{bs3_tag(sb)} Section 4 Complete")
    return True


BS3_SECTIONS: tuple[Callable[[Game, bool], bool], ...] = (bs3_section1, bs3_section2, bs3_section3, bs3_section4)


def run_bs3(game: Game, sb: bool, sections: tuple[Callable[[Game, bool], bool], ...] = BS3_SECTIONS) -> None:
    """BonusStage3 / BonusStage3SB.

    The original recurses with `$iCurrentSection + 4` when a section fails, which allows one
    retry per stage (it rerun the failed section) and stops at the second failure.
    """
    event(bs3_tag(sb))
    retried = False
    index = 0
    while index < len(sections):
        if sections[index](game, sb):
            index += 1
        elif not retried:
            retried = True
            event("BonusStage3 section rerun", stage=bs3_tag(sb), section=index + 1)
        else:
            return
```

- [ ] **Step 5: Verify the BS2 tables against the AutoIt source (one-off check, not committed)**

Run:
```bash
.venv/bin/python - <<'EOF'
import re
from pathlib import Path
from idle_runner.minigames.bonus_stage import BS2_SECTIONS, BS2_SB_SECTIONS

src = Path("/home/santi/Downloads/Idle_Slayer_Script/Libraries/BonusStage.au3").read_text()

def autoit_holds(func: str) -> list[tuple[int, int]]:
    body = src.split(f"Func {func}()")[1].split("EndFunc")[0]
    return [(int(a), int(b or 0)) for a, b in re.findall(r"cSend\((\d+)(?:,\s*(\d+))?\)", body)]

def python_holds(sections) -> list[tuple[int, int]]:
    out = []
    for s in sections:
        out += list(s.moves)
        if s.collect_hold:
            out.append(s.collect_hold)
    return out

assert python_holds(BS2_SB_SECTIONS) == autoit_holds("BonusStage2SB")
assert python_holds(BS2_SECTIONS) == autoit_holds("BonusStage2")
print("BS2 tables match the AutoIt source")
EOF
```
Expected: `BS2 tables match the AutoIt source`. Then compare each `bs3_section*` function side by side with `BonusStage3Section1..4` in `BonusStage.au3`: same waits, same `cSend` pairs, same order.

- [ ] **Step 6: Wire it into the runner**

In `idle_runner/runner.py`, add the import after the chest hunt import:
```python
from idle_runner.minigames.bonus_stage import bonus_stage
```
In `Runner.tick`, insert before the line `            if s.circle_portals and portal_ready(g):`:
```python
            if g.pixel_is(660, 254, 0xFFE737) and g.pixel_is(638, 236, 0xFFBB31):  # bonus stage
                self._routine("bonus_stage", lambda: bonus_stage(g, s.skip_bonus_stage))
```

- [ ] **Step 7: Run the tests to see them pass**

Run: `.venv/bin/python -m pytest -v`
Expected: `63 passed`

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: port bonus stages 2 and 3" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Boss fights

**Files:**
- Create: `idle_runner/minigames/boss.py`, `tests/minigames/test_boss.py`
- Modify: `idle_runner/runner.py`, `tests/test_runner.py`

**Interfaces:**
- Consumes: `Game`, `STUCK_MS`, `Repeater` (Task 5), `slide_until_gone` (Task 10), `event`.
- Produces: `boss_fight_victor(game) -> None`, `victor_battle(game, shooter) -> None` (shooter: anything with `resume()`/`pause()`), `boss_fight_knight(game) -> None`.

- [ ] **Step 1: Write the failing tests**

`tests/minigames/test_boss.py`:
```python
from idle_runner.minigames.boss import boss_fight_knight, victor_battle


class FakeShooter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def resume(self) -> None:
        self.calls.append("resume")

    def pause(self) -> None:
        self.calls.append("pause")


def test_victor_battle_ends_when_won(game, fake, event_names) -> None:
    fake.paint(835, 477, 0xFD3169)  # the victory screen
    shooter = FakeShooter()
    victor_battle(game, shooter)

    assert "Victor Won" in event_names()
    assert (615, 563) in fake.clicks()
    assert shooter.calls[0] == "resume" and shooter.calls[-1] == "pause"


def test_victor_battle_gives_up_after_200_seconds(game, fake, event_names) -> None:
    fake.cost_ms = 50
    victor_battle(game, FakeShooter())

    assert "Victor Lost" in event_names()


def test_knight_is_logged_but_not_fought(game, fake, event_names) -> None:
    boss_fight_knight(game)

    assert event_names() == ["Start of BossFight Knight"]
    assert fake.actions == []
```

Append to `tests/test_runner.py`:
```python
def test_boss_fight_picks_knight_or_victor(game, fake, jumper, monkeypatch) -> None:
    fought = []
    monkeypatch.setattr(runner_module, "boss_fight_victor", lambda g: fought.append("victor"))
    monkeypatch.setattr(runner_module, "boss_fight_knight", lambda g: fought.append("knight"))
    for x, color in ((639, 0xFF878A), (634, 0xF263BD), (644, 0xFFF38F)):
        fake.paint(x, 224, color)
    runner = Runner(game, Settings(), jumper)
    fake.t += 6_000
    runner.tick()
    fake.paint(30, 690, 0x0B0303)  # Knight's arena
    fake.t += 6_000
    runner.tick()

    assert fought == ["victor", "knight"]
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest tests/minigames/test_boss.py -v`
Expected: ERROR with `ModuleNotFoundError: No module named 'idle_runner.minigames.boss'`

- [ ] **Step 3: Implement `boss.py`**

`idle_runner/minigames/boss.py`:
```python
"""Boss fights, ported from Libraries/BossFightVictor.au3 and BossFightKnight.au3."""
from typing import Protocol

from idle_runner.game import STUCK_MS, Game
from idle_runner.log import event
from idle_runner.minigames.common import slide_until_gone
from idle_runner.repeater import Repeater


class Shooter(Protocol):
    """AdlibRegister("Shoot", 50) / AdlibUnRegister("Shoot")."""

    def resume(self) -> None: ...
    def pause(self) -> None: ...


def boss_fight_knight(game: Game) -> None:
    # The original returns right after this log line: its Knight logic is disabled, so it isn't ported.
    event("Start of BossFight Knight")


def boss_fight_victor(game: Game) -> None:
    event("Start of BossFight Victor")
    slide_until_gone(game, "victor", 653, 222, 653, 222, 0xFFF38F)
    game.save_frame("victor-start")
    shooter = Repeater(game, ("Up",), 50, "victor-shoot")
    try:
        victor_battle(game, shooter)
    finally:
        shooter.stop()
        game.save_frame("victor-end")


def victor_battle(game: Game, shooter: Shooter) -> None:
    shooter.resume()
    game.sleep(5000)
    first_stage = True
    interval = 2000
    last_check = start = game.now()
    while True:
        if not first_stage and game.pixel_search(1072, 150, 1072, 488, 0xFFFFFF):
            flame_attack(game)
        attack = game.pixel_search(919, 292, 919, 452, 0xFFFFFF)
        if attack:
            shooter.pause()
            if attack[1] > 370:
                down_attack(game, shooter, first_stage)
            else:
                upper_attack(game, shooter, first_stage)

        if game.now() - last_check > interval:
            if game.pixel_is(835, 477, 0xFD3169):  # victory screen
                shooter.pause()
                game.sleep(500)
                game.click(615, 563)
                event("Victor Won")
                return
            if first_stage and game.pixel_is(272, 130, 0xAE6C37):  # stage 2 dialog
                first_stage = False
                interval = 10_000
                event("Victor Stage 2")
                shooter.resume()
                deadline = game.now() + STUCK_MS
                while True:
                    game.sleep(50)
                    if not game.pixel_is(272, 130, 0xAE6C37):
                        break
                    if game.now() > deadline:
                        game.stuck("victor.dialog")
                        break
                game.sleep(4000)
                shooter.pause()
            if game.now() - start > 200_000:
                shooter.pause()
                event("Victor Lost")
                return
            last_check = game.now()


def flame_attack(game: Game) -> None:
    game.sleep(350)
    game.key_down("Up")
    game.sleep(100)
    game.key_up("Up")
    for _ in range(18):
        game.sleep(10)
        game.tap("Up")


def down_attack(game: Game, shooter: Shooter, first_stage: bool) -> None:
    game.sleep(200)
    if first_stage:
        shooter.resume()
        return
    game.key_down("Up")
    game.sleep(100)
    game.key_up("Up")
    for _ in range(18):
        game.sleep(10)
        game.tap("Up")


def upper_attack(game: Game, shooter: Shooter, first_stage: bool) -> None:
    game.sleep(730)
    if first_stage:
        shooter.resume()
        return
    for _ in range(15):
        game.sleep(10)
        game.tap("Up")
```

- [ ] **Step 4: Wire it into the runner**

In `idle_runner/runner.py`, add the import after the bonus stage import:
```python
from idle_runner.minigames.boss import boss_fight_knight, boss_fight_victor
```
In `Runner.tick`, insert before the line `            if s.circle_portals and portal_ready(g):`:
```python
            if (g.pixel_is(639, 224, 0xFF878A) and g.pixel_is(634, 224, 0xF263BD)
                    and g.pixel_is(644, 224, 0xFFF38F)):  # boss fight
                if g.pixel_is(30, 690, 0x0B0303):
                    self._routine("boss_knight", lambda: boss_fight_knight(g))
                else:
                    self._routine("boss_victor", lambda: boss_fight_victor(g))
```

- [ ] **Step 5: Run the tests to see them pass**

Run: `.venv/bin/python -m pytest -v`
Expected: `67 passed`

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: port Victor boss fight (Knight stays disabled)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Ascending Heights

**Files:**
- Create: `idle_runner/minigames/ascending_heights.py`, `tests/minigames/test_ascending_heights.py`
- Modify: `idle_runner/runner.py`, `tests/test_runner.py`

**Interfaces:**
- Consumes: `Game`, `Point`, `slide_until_gone`, `event`.
- Produces: `ascending_heights(game) -> None`, `play(game) -> None`, `platform_below(game, px: int, py: int, same: bool) -> Point | None`.

- [ ] **Step 1: Write the failing tests**

`tests/minigames/test_ascending_heights.py`:
```python
from idle_runner.minigames.ascending_heights import platform_below, play


def test_platform_below_prefers_the_platform_near_the_player(game, fake) -> None:
    # Near the right edge the original clamped `left` instead of `right` and lost nearby platforms.
    fake.paint(400, 450, 0xC0CBDC)  # far platform, higher on screen
    fake.paint(880, 500, 0xC0CBDC)  # platform right below the player

    assert platform_below(game, 850, 300, same=False) == (880, 500)


def test_play_stops_on_the_failure_screen(game, fake, event_names) -> None:
    fake.paint(190, 125, 0xFFAF36)
    fake.cost_ms = 50
    play(game)

    assert event_names()[-1] == "Ascending Height Failed"


def test_play_times_out_after_4_minutes(game, fake, event_names) -> None:
    fake.cost_ms = 200
    play(game)

    assert "Ascending Heights timed out after 4 minutes" in event_names()
    assert ("key", "a", True) in fake.actions and ("key", "d", True) in fake.actions
```

Append to `tests/test_runner.py`:
```python
def test_ascending_heights_is_dispatched(game, fake, jumper, monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(runner_module, "ascending_heights", lambda g: calls.append(True))
    fake.paint(671, 213, 0xC2F4F9)
    fake.paint(637, 300, 0xFFCC66)
    runner = Runner(game, Settings(), jumper)
    fake.t += 6_000
    runner.tick()

    assert calls == [True]
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest tests/minigames/test_ascending_heights.py -v`
Expected: ERROR with `ModuleNotFoundError: No module named 'idle_runner.minigames.ascending_heights'`

- [ ] **Step 3: Implement `ascending_heights.py`**

`idle_runner/minigames/ascending_heights.py`:
```python
"""Ascending Heights, ported from Libraries/AscendingHeights.au3."""
from idle_runner.game import Game, Point
from idle_runner.log import event
from idle_runner.minigames.common import slide_until_gone

PLATFORM = 0xC0CBDC
PLATFORM_EDGE = 0x8B9BB4
PLAYER = 0x633E75


def ascending_heights(game: Game) -> None:
    event("Start of Ascending Heights")
    slide_until_gone(game, "ascending_heights", 640, 240, 634, 640, 0xFFCC66)
    game.sleep(3900)
    game.save_frame("ascending-heights-start")
    play(game)
    game.save_frame("ascending-heights-end")


def play(game: Game) -> None:
    last_platform: Point = (0, 0)
    same_count = 0
    same = False
    last_check = start = game.now()
    while True:
        if game.now() - start >= 240_000:
            event("Ascending Heights timed out after 4 minutes")
            game.hold(3000, 0, "a")
            game.sleep(100)
            game.hold(3000, 0, "d")
            return
        if game.now() - last_check >= 5000:
            last_check = game.now()
            if game.pixel_is(190, 125, 0xFFAF36):
                event("Ascending Height Failed")
                return
            if game.pixel_is(540, 560, 0x00A400):  # "second wind": continue
                game.sleep(2000)
                game.click(560, 570)
            if game.pixel_search(700, 385, 730, 385, 0x7A444A):
                game.hold(15_000, 0, "d")
                event("Ascending Height Won")
                return

        player = game.pixel_search(375, 260, 900, 730, PLAYER)
        if player is None:
            continue
        platform = platform_below(game, player[0], player[1], same)
        if platform is None:
            continue
        if platform == last_platform:
            same_count += 1
            if same_count == 5:  # stuck aiming at the same platform: widen the search
                same = True
        else:
            same_count = 0
            same = False
        last_platform = platform

        if platform[0] + 35 > player[0] + 35:
            steer(game, 1100)  # hold on the right half of the screen
        elif platform[0] + 35 < player[0] - 35:
            steer(game, 100)  # hold on the left half


def steer(game: Game, x: int) -> None:
    game.move(x, 600)
    game.mouse_down()
    game.sleep(100)
    game.mouse_up()


def platform_below(game: Game, px: int, py: int, same: bool) -> Point | None:
    """searchAllPlatformBellowPlayer: the highest platform under the player whose edge pixel isn't dark."""
    if not same:
        # Fixed: the original set `$iLeft = 900` when the right bound overflowed.
        left, right = max(px - 130, 375), min(px + 130, 900)
        platform = (game.pixel_search(left, py + 50, right, 752, PLATFORM)
                    or game.pixel_search(375, py + 50, 900, 752, PLATFORM))
    else:
        platform = game.pixel_search(375, py + 50, 900, 752, PLATFORM)
    for _ in range(1000):  # the original's safety counter
        if platform is None:
            return None
        if not game.pixel_is(platform[0] + 6, platform[1], PLATFORM_EDGE):
            return platform
        if platform[1] + 2 > 752:
            return None
        platform = game.pixel_search(375, platform[1] + 1, 900, 752, PLATFORM)
    return None
```

- [ ] **Step 4: Wire it into the runner**

In `idle_runner/runner.py`, add the import after the boss import:
```python
from idle_runner.minigames.ascending_heights import ascending_heights
```
In `Runner.tick`, insert before the line `            if s.circle_portals and portal_ready(g):`:
```python
            if g.pixel_is(671, 213, 0xC2F4F9) and g.pixel_search(640, 240, 634, 640, 0xFFCC66):  # ascending heights
                self._routine("ascending_heights", lambda: ascending_heights(g))
```

- [ ] **Step 5: Run the tests to see them pass**

Run: `.venv/bin/python -m pytest -v`
Expected: `71 passed`

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: port Ascending Heights (fix right-edge clamp)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: Fast buying after ascension (first improvement over the original)

This is the user's first requested improvement and the first deliberate behaviour change. Right after ascending, coins grow fast but the original waits a full `auto_buy_minutes` before buying again, and it doesn't reset the buy-round counter. The new behaviour: buy `post_ascend_first_buy_seconds` after ascending, then double the wait each time up to `auto_buy_minutes` (15 s → 30 s → 1 m → 2 m → 4 m → 8 m → 10 m). Set it to 0 for the original behaviour.

**Files:**
- Modify: `idle_runner/config.py`, `config.example.toml`, `idle_runner/runner.py`, `tests/test_runner.py`, `README.md`

**Interfaces:**
- Consumes: `Shop.auto_ascend() -> bool` (Task 6), `Runner._routine` returns `fn()`'s result (Task 7).
- Produces: `Settings.post_ascend_first_buy_seconds: int = 15`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_runner.py`:
```python
def test_post_ascend_ramp_buys_soon_then_backs_off(game, fake, jumper, monkeypatch) -> None:
    settings = replace(Settings(), auto_buy_upgrades=True, auto_buy_minutes=10,
                       auto_ascend=True, auto_ascend_minutes=1, post_ascend_first_buy_seconds=15)
    runner = Runner(game, settings, jumper)
    buys = []
    monkeypatch.setattr(runner.shop, "auto_ascend", lambda: True)
    monkeypatch.setattr(runner.shop, "auto_upgrade", lambda: buys.append(fake.t))

    fake.t += 61_000
    runner.tick()  # ascends; the 10-minute buy timer isn't due
    assert buys == [] and runner.buy_minutes == 0.25

    fake.t += 16_000
    runner.tick()  # 15 s after ascending: first fast buy
    assert len(buys) == 1 and runner.buy_minutes == 0.5


def test_post_ascend_ramp_can_be_disabled(game, fake, jumper, monkeypatch) -> None:
    settings = replace(Settings(), auto_buy_upgrades=True, auto_ascend=True, auto_ascend_minutes=1,
                       post_ascend_first_buy_seconds=0)
    runner = Runner(game, settings, jumper)
    monkeypatch.setattr(runner.shop, "auto_ascend", lambda: True)
    fake.t += 61_000
    runner.tick()

    assert runner.buy_minutes == 10
```

- [ ] **Step 2: Run it to see it fail**

Run: `.venv/bin/python -m pytest tests/test_runner.py -k post_ascend -v`
Expected: FAIL with `TypeError: ... unexpected keyword argument 'post_ascend_first_buy_seconds'`

- [ ] **Step 3: Add the setting**

In `idle_runner/config.py`, insert after `auto_ascend_minutes: float = 10`:
```python
    post_ascend_first_buy_seconds: int = 15
```
In `_check_ranges`, insert before `    if not 0 <= s.color_tolerance <= 255:`:
```python
    if s.post_ascend_first_buy_seconds < 0:
        problems.append("post_ascend_first_buy_seconds must be >= 0")
```
In `config.example.toml`, insert after `auto_ascend_minutes = 10`:
```toml
post_ascend_first_buy_seconds = 15       # after ascending, buy this soon, then double the wait up to
                                         # auto_buy_minutes (0 = original behaviour)
```

- [ ] **Step 4: Change the runner**

In `idle_runner/runner.py` `Runner.tick`, replace:
```python
                self.buy_minutes = s.auto_buy_minutes
```
with:
```python
                self.buy_minutes = min(self.buy_minutes * 2, s.auto_buy_minutes)
```
and replace:
```python
                self.timer_ascend = g.now()
                self._routine("auto_ascend", self.shop.auto_ascend)
```
with:
```python
                self.timer_ascend = g.now()
                self.shop.loop_amount = 0  # the original left this at its last value
                ascended = self._routine("auto_ascend", self.shop.auto_ascend)
                if ascended and s.post_ascend_first_buy_seconds:
                    self.timer_buy = g.now()
                    self.buy_minutes = s.post_ascend_first_buy_seconds / 60
                    event("Post-ascend buy ramp", first_buy_seconds=s.post_ascend_first_buy_seconds)
```

- [ ] **Step 5: Run the tests to see them pass**

Run: `.venv/bin/python -m pytest -v`
Expected: `73 passed` (`test_example_config_documents_the_defaults` still passes because the example has the new key with its default)

- [ ] **Step 6: Document it**

In `README.md`, under "Differences from the AutoIt original", add:
```markdown
- After an ascension, buying restarts quickly (`post_ascend_first_buy_seconds`, default 15 s) and the wait doubles up to `auto_buy_minutes`. Set it to 0 for the original behaviour.
```

- [ ] **Step 7: Live check (needs the user)**

Set `auto_buy_upgrades = true`, `auto_ascend = true` and `auto_ascend_minutes = 2` in `config.toml`, then run the bot with the game focused. After the ascension, `logs/events.jsonl` must show `Ascended`, then `Post-ascend buy ramp`, then `AutoUpgrade Done` at about +15 s, +45 s and +105 s, with growing `upgrades` counts. Then run `.venv/bin/python -m idle_runner stats`.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: fast buying right after ascension" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

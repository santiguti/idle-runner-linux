# Idle Runner (Linux)

Linux port of [Devil4ngle's Idle Runner](https://github.com/Devil4ngle/Idle_Slayer_Script), a pixel-based bot for the Steam game Idle Slayer. Like the AutoIt original, it only looks at the game window's pixels and sends keyboard/mouse input; it doesn't read or modify the game.

## Requirements
- The native Linux build of Idle Slayer on X11/XWayland (`~/.config/unity3d/Pablo Leban/Idle Slayer/Player.log` says `Selected window backend: x11`; don't launch it with `-force-wayland`).
- If the game boots to a black screen (Steam's runtime container lacks `libsecret`, so Firebase fails), set the Steam launch option:
  `"<steam library>/steamapps/common/Idle Slayer/Idle Slayer.x86_64" # %command%`
- In-game settings, as in the original: windowed 1280x720, English, jump = Up arrow, boost = Right arrow, custom cursor disabled, portal dialogue disabled, rounded bulk enabled, hide locked quest rewards enabled, don't buy the Vertical Magnet.
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
- Window: 1280x720 client area, frame offset (8, 31), colour tolerance needed: 0. Verified with the portal button pixel (AutoIt (1180, 166) is exactly `0x830399`) and the chest-hunt grid (the saver bracket sits exactly on the AutoIt cell coordinates).
- Grab timings: 1 px 0.23 ms, full frame 5.1 ms.

## Running
From the KDE menu: **Idle Runner** (or `.venv/bin/python -m idle_runner gui`). The window starts and stops the bot, edits `config.toml` (saving rewrites it without comments; `config.example.toml` keeps them), shows the log and has a **Mark problem** box.

From a terminal:
```bash
cp config.example.toml config.toml   # then edit it
.venv/bin/python -m idle_runner run
```
The bot only sends input while the Idle Slayer window is focused. Alt-tab away to pause it and focus the game again to resume. Stop it with Ctrl+C in the terminal (or Stop in the window).

## Logs
- `logs/idle_runner.log`: human-readable, millisecond timestamps. With `log_level = "DEBUG"` it also traces every pixel search.
- `logs/events.jsonl`: one JSON object per event (`ts`, `event`, extra fields), for analysis.
- `logs/frames/`: PNG screenshots at minigame start/end, safety-net timeouts (`stuck-*`) and crashes (`crash-*`).
- `.venv/bin/python -m idle_runner stats`: event counts and routine durations.
- `logs/blackbox/`: the black box. While the bot runs, a separate process saves the game window `blackbox_fps` times a second (default 4, about 100 KB a frame) and keeps the last `blackbox_minutes` (default 60, about 1.4 GB).
- `logs/marks/<time>-<why>/`: frames kept for good, with a `note.txt`:
  - by the black box itself around every anomaly the bot logs (a minute before to 30 s after; see `ANOMALIES` in `idle_runner/blackbox.py`);
  - by **Mark problem** in the window, or `.venv/bin/python -m idle_runner mark "what you saw"`: the last 5 minutes. Mark as soon as you notice something.

  The frames are hard links, so a mark costs no extra space until the black box prunes its copy. Delete old marks by hand.
- `.venv/bin/python -m idle_runner blackbox`: only the black box, e.g. while you play by hand.
- Every click, wheel notch and key hold the bot sends is in `idle_runner.log` (not on the console). The jumper's taps are only there at `log_level = "DEBUG"`.

## Differences from the AutoIt original
- The original slept 2 s every 5 s before closing popups, which blinded the fast checks (megahordes, chest hunts, quests, silver boxes) 40% of the time. That sleep is gone.
- No focus stealing and no global hotkeys: focus = run, alt-tab = pause, Ctrl+C = stop. Closing the terminal or `kill` also stops it cleanly, and held keys are released (a long key hold ends as soon as the game loses focus).
- The bot pauses, with a warning, while the game window isn't exactly 1280x720 (checked continuously, e.g. if the window gets maximized).
- An unexpected error is logged with its traceback and the bot keeps going; it stops after 5 errors in a row.
- Bonus-stage sync markers that never show up are logged as `Sync timeout` events with a screenshot.
- One-shot crafts (Dimensional/Bidimensional staff) apply once per run. The portal rotation restarts from `circle_portals_count`.
- Loops that could hang forever give up after a timeout and log a `stuck` event with a screenshot.
- The jumper pauses immediately when a menu routine starts.
- Fixed: the Ascending Heights right-edge clamp, chest-hunt stats, and clicks outside the window (refused).
- Auto-ascend confirms at (598, 581) instead of (550, 580), and only once the "Are you sure?" dialog shows. Since the Ultra Ascension node is bought, (550, 580) is on the Ultra Ascend button whenever the dialog is late.
- Upgrades: blue event-quest rows are skipped only while their button is the grey "Quest Reward"; once claimed they get a buy button and are bought.
- The Knight boss stays disabled, as in the original.
- After an ascension, buying restarts quickly (`post_ascend_first_buy_seconds`, default 15 s) and the wait doubles up to `auto_buy_minutes`. Set it to 0 for the original behaviour.

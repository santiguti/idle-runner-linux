# Idle Runner (Linux)

Python port of Devil4ngle's AutoIt bot for the Steam game Idle Slayer. It reads the game window's pixels and sends keyboard/mouse input; it never reads or modifies game memory, files or network.

- Original AutoIt source (read-only reference): `/home/santi/Downloads/Idle_Slayer_Script` (`Idle Runner.au3`, `Libraries/*.au3`)
- Implementation plan + design decisions: `docs/superpowers/plans/2026-10-21-linux-port.md`
- Execution ledger (every ruling, live-test result and review finding): `.superpowers/sdd/2026-10-21-linux-port/progress.md` (git-ignored)
- Pending work, already triaged: `docs/next-steps.md` — read it before starting anything. Its section 3 lists the UI colours and timings measured on 2026-10-22 (the game changed since the original: scrollbar, tabs, Buy all bar, event quests).
- Recordings and measuring scripts of 2026-10-22: `logs/recordings/2026-10-22/` (git-ignored).

## Rules
- **Never `git commit`**: Santi commits himself (a hook blocks it). Leave changes uncommitted.
- Always use `./.venv/bin/python` / `./.venv/bin/pip`; dependencies only in `pyproject.toml` (runtime: numpy, python-xlib; dev: pytest).
- TDD: write the test, watch it fail, then implement. Tests live in `tests/`, mirroring `idle_runner/`. Run `.venv/bin/python -m pytest -q`.
- Strong type hints; code, comments and event text in English. Event names that exist in the original keep its exact text.
- Coordinates, colours and sleeps are copied verbatim from the AutoIt source as **AutoIt coordinates** (window incl. Windows title bar); `Game` subtracts the offset (8, 31). Every port line must stay traceable to an AutoIt line.
- Never send input to the user's desktop without asking: live tests (`python -m idle_runner run`, `probe --key/--click`) need the user's go-ahead and the game focused. Ascending is irreversible in the game: on 2026-10-21 the user allowed ascensions during live tests; confirm again in a new session.

## Verified environment (2026-10-21)
- Fedora 44, KDE Plasma 6.7 on Wayland. Idle Slayer is the native Linux build (Unity 6000.3.14f1), X11 backend via XWayland. Window title `Idle Slayer`, client 1280x720.
- Steam's runtime container lacks `libsecret`, so Firebase fails and the game boots black. Workaround in use (Steam launch option): `"/home/santi/.local/share/Steam/steamapps/common/Idle Slayer/Idle Slayer.x86_64" # %command%`
- Offset (8, 31) verified exactly (AutoIt portal pixel (1180,166) = 0x830399; chest-hunt grid). Colours identical to Windows (tolerance 0). Capture: 1 px 0.23 ms, full frame 5.1 ms. XTEST clicks and keys reach the game.
- In-game keybinds: jump = Up, boost = Right (set by the user).
- KDE asks for permission (a "remote control" dialog) the first time XTEST input is sent after XWayland starts; the dialog takes focus, so the bot pauses until the user accepts and refocuses the game (seen 2026-10-22).
- Shop lists (measured 2026-10-22 with XTEST): one wheel notch = 50 px, usually drawn within 30 ms; the game sometimes stops drawing for over 1 s and then catches up. Fully covered windows aren't redrawn.
- Game log: `~/.config/unity3d/Pablo Leban/Idle Slayer/Player.log`; saves next to it (`savedata.sav`, cloud-synced via Firebase). Backup of 2026-10-21: `~/Documents/idle-slayer-save-backup-20261021`.

## Layout
- `blackbox.py` — the black box (own process, `logs/blackbox/`, keeps frames around anomalies and user marks in `logs/marks/`). `gui.py` — tkinter window that runs `run` as a child process (KDE menu entry: `~/.local/share/applications/idle-runner.desktop`).
- `idle_runner/x11.py` — only X11 code (window lookup, XGetImage, XTEST). `game.py` — AutoIt-compatible facade (`pixel_search` is column-major like AutoIt, focus guard, `routine()`, `stuck()`, frames), `GameUnavailable` / `WindowGone`, and `open_backend()` (picks X11 or, later, Win32; python-xlib is Linux-only). `process.py` — `self_command()` to start the bot/black box as children (also from a frozen exe). `ui/updates.py` — GitHub release check. CI: `.github/workflows/ci.yml`. Plan for Windows + new window: `docs/superpowers/plans/2026-10-26-v2.md` (ledger `.superpowers/sdd/2026-10-26-v2/progress.md`). `runner.py` — the AutoIt `Main()` loop. `shop.py`, `actions.py`, `portals.py`, `minigames/*` — ports of the AutoIt functions. `repeater.py` — jump/boost thread.
- Logs: `logs/idle_runner.log` (ms timestamps, plus every click/wheel/hold), `logs/events.jsonl`, `logs/frames/*.png`, `logs/blackbox/` (last hour at 4 fps), `logs/marks/` (kept frames + note); `python -m idle_runner stats`. To debug a user's unattended run, start from `logs/marks/` and the events around each mark's time.
- Tests use `tests/fakes.py` (`FakeBackend` with a virtual clock; `paint()` takes AutoIt coordinates).

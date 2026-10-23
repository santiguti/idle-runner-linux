"""Command line entry point: python -m idle_runner <command>."""
import argparse
import sys
import time
from pathlib import Path

import numpy as np

from idle_runner.png import write_png
from idle_runner.config import load_settings
from idle_runner.game import Game
from idle_runner.log import setup_logging
from idle_runner.repeater import Repeater
from idle_runner.runner import Runner, install_stop_signals
from idle_runner.stats import summarize
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


def run_bot(config_path: Path) -> int:
    if not config_path.exists():
        print(f"error: {config_path} not found; copy config.example.toml to {config_path} and edit it",
              file=sys.stderr)
        return 1
    try:
        settings = load_settings(config_path)
    except ValueError as exc:  # also covers tomllib.TOMLDecodeError
        print(f"error: {exc}", file=sys.stderr)
        return 1
    log_dir = Path(settings.log_dir)
    setup_logging(log_dir, settings.log_level)
    backend = X11Backend(settings.window_name)
    game = Game(backend, (settings.offset_x, settings.offset_y), settings.color_tolerance,
                log_dir / "frames" if settings.save_frames else None)
    jumper = Repeater(game, ("Up", "Right"), settings.jump_interval_ms, "jumper")
    install_stop_signals()
    Runner(game, settings, jumper).run()
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

    stats = sub.add_parser("stats", help="summarize logs/events.jsonl")
    stats.add_argument("--log-dir", type=Path, default=Path("logs"))

    run = sub.add_parser("run", help="run the bot (Ctrl+C to stop)")
    run.add_argument("--config", type=Path, default=Path("config.toml"))

    args = parser.parse_args(argv)
    try:
        if args.command == "probe":
            return run_probe(args)
        if args.command == "stats":
            print("\n".join(summarize(args.log_dir / "events.jsonl")))
            return 0
        if args.command == "run":
            return run_bot(args.config)
    except GameUnavailable as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

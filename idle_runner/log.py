"""Logging: a human-readable log with millisecond timestamps plus machine-readable events.jsonl."""
import json
import logging
import logging.handlers
import threading
import time
from pathlib import Path

log = logging.getLogger("idle_runner")
# Clicks, wheel notches, key holds: in the log file (to replay what the bot did), not on the console.
inputs = logging.getLogger("idle_runner.input")

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
    console.addFilter(lambda record: record.name != inputs.name)

    for handler in log.handlers[:]:
        log.removeHandler(handler)
        handler.close()
    for handler in (file_handler, console):
        handler.setFormatter(formatter)
        log.addHandler(handler)
    log.setLevel(logging.DEBUG)


def event(name: str, /, **fields: object) -> None:
    """Record a named event in the human log and as one JSON line in events.jsonl.

    `name` is positional-only so events can carry a `name=` field (e.g. routine names).
    """
    log.info("%s%s", name, "".join(f" {key}={value}" for key, value in fields.items()))
    if _events_path is None:
        return
    line = json.dumps({"ts": round(time.time(), 3), "event": name, **fields}, default=str)
    with _events_lock, _events_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

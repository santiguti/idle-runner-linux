import os
import time
from pathlib import Path

from idle_runner.blackbox import ANOMALIES, BlackBox, mark
from idle_runner.log import event
from tests.fakes import read_png


def test_capture_saves_the_whole_window(fake, tmp_path) -> None:
    fake.paint(100, 100, 0x123456)
    box = BlackBox(fake, tmp_path, minutes=60)

    path = box.capture()

    assert path is not None and path.parent == tmp_path / "blackbox"
    assert (read_png(path) == fake.frame).all()


def test_capture_skips_while_the_game_is_not_focused(fake, tmp_path) -> None:
    fake.active = False  # the bot is paused: nothing to record

    assert BlackBox(fake, tmp_path, minutes=60).capture() is None


def test_prune_keeps_only_the_last_minutes(fake, tmp_path) -> None:
    box = BlackBox(fake, tmp_path, minutes=60)
    old, recent = box.capture(), box.capture()
    an_hour_ago = time.time() - 3601
    os.utime(old, (an_hour_ago, an_hour_ago))

    box.prune()

    assert not old.exists() and recent.exists()


def test_mark_keeps_the_last_minutes_and_logs_the_note(fake, logs, events) -> None:
    box = BlackBox(fake, logs, minutes=60)
    old, recent = box.capture(), box.capture()
    ten_minutes_ago = time.time() - 600
    os.utime(old, (ten_minutes_ago, ten_minutes_ago))

    folder = mark(logs, "magnet bought", minutes=5)
    os.utime(recent, (0, 0))
    box.prune()  # the black box moves on; the marked copy stays

    assert [p.name for p in folder.glob("*.png")] == [recent.name]
    assert (folder / "note.txt").read_text(encoding="utf-8") == "magnet bought\n"
    assert events()[-1] == {"ts": events()[-1]["ts"], "event": "User note", "text": "magnet bought",
                            "frames": 1, "folder": str(folder)}


def test_anomalies_keep_the_minute_before_and_30_s_after(fake, logs) -> None:
    event("Bot started")
    box = BlackBox(fake, logs, minutes=60)
    box.watch_events(now=time.time())  # starts at the end of events.jsonl
    too_old, before = box.capture(), box.capture()
    two_minutes_ago = time.time() - 120
    os.utime(too_old, (two_minutes_ago, two_minutes_ago))
    event("Quest Claimed")  # not an anomaly
    event("stuck", where="buy_upgrade")
    after = box.capture()

    box.watch_events(now=time.time())
    assert not (logs / "marks").exists()  # waits for what happens next
    box.watch_events(now=time.time() + 31)

    [folder] = (logs / "marks").iterdir()
    assert folder.name.endswith("-stuck")
    assert sorted(p.name for p in folder.glob("*.png")) == sorted([before.name, after.name])
    assert '"where": "buy_upgrade"' in (folder / "note.txt").read_text(encoding="utf-8")


def test_every_anomaly_is_an_event_the_bot_logs() -> None:
    package = Path(__file__).resolve().parents[1] / "idle_runner"
    source = "".join(p.read_text(encoding="utf-8") for p in package.rglob("*.py") if p.name != "blackbox.py")

    assert [name for name in ANOMALIES if f'"{name}"' not in source] == []

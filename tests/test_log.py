import json
import re

from idle_runner.log import event, log


def test_event_appends_a_json_line(logs) -> None:
    event("Silver Box Collected", x=644)

    record = json.loads((logs / "events.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert record["event"] == "Silver Box Collected"
    assert record["x"] == 644
    assert record["ts"] > 0


def test_human_log_has_millisecond_timestamps(logs) -> None:
    event("hello", a=1)
    for handler in log.handlers:
        handler.flush()

    text = (logs / "idle_runner.log").read_text(encoding="utf-8")
    assert re.search(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3} INFO\s+\[MainThread\] hello a=1", text)

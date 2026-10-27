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
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n{broken\n", encoding="utf-8")

    out = summarize(path)

    assert "     2  Silver Box Collected" in out
    assert "auto_upgrade: n=2 avg=2000 ms max=3000 ms" in out
    assert "(1 unreadable lines skipped)" in out


def test_summarize_without_events_file(tmp_path) -> None:
    assert summarize(tmp_path / "missing.jsonl")[0].startswith("no events yet")

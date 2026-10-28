import json
from pathlib import Path

import pytest

from idle_runner.ui.activity import EventTail, Session, apply, describe

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "events" / "2026-10-26.jsonl"
# Three real runs of the bot on 2026-10-26: lines 0-11 (02:03, one ascension, stopped), 12-23 (02:10, tree
# buys, stopped) and 24-42 (18:44, an ascension with a jewel offer, a bonus stage, still running).
RECORDS = [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines()]


def replay(records: list[dict]) -> Session:
    session = Session()
    for record in records:
        apply(session, record)
    return session


def counters(s: Session) -> tuple:
    return (s.upgrades, s.equipment, s.ascensions, s.last_bonus, s.tree_nodes, s.minigames, s.boxes, s.quests,
            s.problems)


def test_first_run_of_the_fixture() -> None:
    s = replay(RECORDS[:12])
    # problems: "AutoUpgrade shop not open"
    assert counters(s) == (1, 5, 1, 10.2, 0, 0, 0, 0, 1)
    assert s.state == "stopped" and s.started_ts == RECORDS[0]["ts"]


def test_second_run_buys_tree_nodes() -> None:
    s = replay(RECORDS[12:24])
    # problems: "Tree node not bought"
    assert counters(s) == (7, 22, 0, 1.9, 4, 0, 0, 0, 1)
    assert s.nodes_bought == {"Idle Earrings I", "Idle Earrings II", "Blessing of Cronus", "Portals"}


def test_whole_fixture_is_the_last_run_because_bot_started_resets() -> None:
    s = replay(RECORDS)
    # problems: "Shop tab not shown", two "Sync timeout" and the jewel offer (an anomaly since B2)
    assert counters(s) == (0, 6, 1, 21.5, 0, 1, 1, 1, 4)
    assert (s.state, s.detail, s.nodes_bought) == ("running", "", set())


def test_state_changes() -> None:
    s = Session()
    for record, state, detail in [
        ({"event": "Bot started", "ts": 5.0}, "running", ""),
        ({"event": "Paused: game not focused"}, "paused", "game not focused"),
        ({"event": "Resumed"}, "running", ""),
        ({"event": "Game unavailable", "reason": "the game window is not focused"}, "paused",
         "the game window is not focused"),
        ({"event": "Resumed"}, "running", ""),
        ({"event": "Game window lost"}, "game lost", ""),
        ({"event": "Game window found"}, "running", ""),
        ({"event": "Bot stopped after repeated errors"}, "stopped", ""),
    ]:
        apply(s, record)
        assert (s.state, s.detail) == (state, detail), record
    assert s.problems == 2  # "Game window lost" and "Bot stopped after repeated errors"


def test_every_minigame_start_counts() -> None:
    s = Session()
    for name in ["Start of BonusStage", "Chesthunt Started", "Start of BossFight Victor",
                 "Start of Ascending Heights", "Start of BossFight Knight"]:
        apply(s, {"event": name})
    assert s.minigames == 5


def test_texts() -> None:
    session = Session(last_bonus=10.1)
    for record, expected in [
        ({"event": "AutoUpgrade Done", "upgrades": 12, "equipment": 4}, ("buy", "Bought 12 upgrades and 4 equipment")),
        ({"event": "AutoUpgrade Done", "upgrades": 1, "equipment": 0}, ("buy", "Bought 1 upgrade")),
        ({"event": "AutoUpgrade Done", "upgrades": 0, "equipment": 9}, ("buy", "Bought 9 equipment")),
        ({"event": "Ascended"}, ("ascend", "Ascended (+10.1% bonus)")),
        ({"event": "Tree node bought", "node": "Legendary Belt"}, ("tree", "Tree: bought Legendary Belt")),
        ({"event": "Ascend bonus", "percent": 4.2}, ("ascend", "Bonus: +4.2%")),
        ({"event": "Paused: game not focused"}, ("state", "Paused: game not focused")),
        ({"event": "Resumed"}, ("state", "Resumed")),
        ({"event": "Bot started"}, ("state", "Bot started")),
        ({"event": "Bot stopped"}, ("state", "Bot stopped")),
        ({"event": "Start of BonusStage"}, ("minigame", "Bonus Stage started")),
        ({"event": "Chesthunt Started"}, ("minigame", "Chest Hunt started")),
        ({"event": "Silver Box Collected"}, ("box", "Silver Box collected")),
        ({"event": "Quest Claimed"}, ("quest", "Quest claimed")),
        ({"event": "Extra daily quests taken"}, ("quest", "Took 2 extra daily quests")),
        ({"event": "Sync timeout", "where": "BonusStage2-s1", "timeout_ms": 15000},
         ("problem", "Sync timeout: BonusStage2-s1")),
        ({"event": "Tree node not bought", "node": "Village Key"}, ("problem", "Tree node not bought: Village Key")),
        ({"event": "Ascend skipped", "reason": "ascend button not found"},
         ("problem", "Ascend skipped: ascend button not found")),
        ({"event": "Shop click retried", "target": "shop"}, ("problem", "Shop click retried")),
    ]:
        assert describe(record, session) == expected, record


def test_ascended_without_a_bonus_reading_is_plain() -> None:
    assert describe({"event": "Ascended"}) == ("ascend", "Ascended")
    assert describe({"event": "Ascended"}, Session()) == ("ascend", "Ascended")


@pytest.mark.parametrize("record", [
    {"event": "routine_start", "name": "auto_upgrade"}, {"event": "routine_end", "name": "auto_upgrade", "ms": 5},
    {"event": "routine_abort", "name": "auto_upgrade", "ms": 5}, {"event": "frame", "label": "x", "path": "p"},
    {"event": "MegaHorde Rage"}, {"event": "AutoUpgrade Active"}, {"event": "Claiming quest"},
    {"event": "AutoUpgrade Done", "upgrades": 0, "equipment": 0, "rounds": 0},
    {"event": "Something new"},
])
def test_noise_is_not_described(record: dict) -> None:
    assert describe(record) is None


def test_the_whole_fixture_is_described_without_errors() -> None:
    session = Session()
    texts = []
    for record in RECORDS:
        shown = describe(record, session)
        apply(session, record)
        if shown:
            texts.append(shown[1])
    assert "Ascended (+21.5% bonus)" in texts and "Bought 6 equipment" in texts
    assert sum(t.startswith("Tree: bought") for t in texts) == 4


def test_tail_reads_only_new_lines(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    tail = EventTail(path)
    assert tail.read_new() == []  # no file yet
    path.write_text('{"event": "a"}\n', encoding="utf-8")
    assert tail.read_new() == [{"event": "a"}]
    assert tail.read_new() == []
    with path.open("a", encoding="utf-8") as f:
        f.write('{"event": "b"}\n{"event": "c"}\n')
    assert [r["event"] for r in tail.read_new()] == ["b", "c"]


def test_tail_waits_for_the_end_of_a_partial_line(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    tail = EventTail(path)
    with path.open("a", encoding="utf-8") as f:
        f.write('{"event": "a"}\n{"event": "b')
    assert [r["event"] for r in tail.read_new()] == ["a"]
    with path.open("a", encoding="utf-8") as f:
        f.write('"}\n')
    assert tail.read_new() == [{"event": "b"}]
    assert tail.read_new() == []


def test_tail_starts_over_after_truncation(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text('{"event": "old one"}\n{"event": "old two"}\n', encoding="utf-8")
    tail = EventTail(path)
    tail.read_new()
    path.write_text('{"event": "new"}\n', encoding="utf-8")
    assert tail.read_new() == [{"event": "new"}]


def test_tail_skips_lines_that_are_not_json_objects(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text('{"event": "a"}\nnot json\n[1, 2]\n\n{"event": "b"}\n', encoding="utf-8")
    assert [r["event"] for r in EventTail(path).read_new()] == ["a", "b"]

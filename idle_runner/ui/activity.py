"""What the window shows of the bot's run, read from `logs/events.jsonl` (no Tk here, so it is testable).

`apply` folds one event into a `Session` (the dashboard's counters and state); `describe` turns an event
into one line of the activity feed; `EventTail` reads the lines the bot appended since the last call.
"""
import json
from dataclasses import dataclass, field, fields
from pathlib import Path

from idle_runner.blackbox import ANOMALIES

# The events that start a minigame (grep 'event("Start' idle_runner/minigames), and the name shown for each.
MINIGAMES = {
    "Start of BonusStage": "Bonus Stage",
    "Chesthunt Started": "Chest Hunt",
    "Start of BossFight Knight": "Knight boss fight",
    "Start of BossFight Victor": "Victor boss fight",
    "Start of Ascending Heights": "Ascending Heights",
}
# What the dashboard says the bot is doing while one of its routines runs (Game.routine's names). The
# Megahorde's rage has none: it lasts 11 ms and fires ~45 times in 2 s at a Megahorde.
DOING = {
    "check_game_settings": "Checking the game's settings",
    "buy_tree": "Checking the Ascension Tree",
    "send_minions": "Checking the minions",
    "auto_upgrade": "Shopping",
    "claim_quests": "Claiming quests",
    "ascend_bonus_sample": "Reading the ascension bonus",
    "auto_ascend": "Ascending",
    "circle_portals": "Taking a portal",
    "bonus_stage": f"Playing {MINIGAMES['Start of BonusStage']}",
    "chest_hunt": f"Playing {MINIGAMES['Chesthunt Started']}",
    "boss_knight": f"Playing {MINIGAMES['Start of BossFight Knight']}",
    "boss_victor": f"Playing {MINIGAMES['Start of BossFight Victor']}",
    "ascending_heights": f"Playing {MINIGAMES['Start of Ascending Heights']}",
}
# Shown as problems when they carry one of these fields: "Sync timeout: BonusStage2-s1".
DETAIL_FIELDS = ("where", "node", "reason", "setting")


@dataclass
class Session:
    state: str = "stopped"  # "stopped" | "running" | "paused" | "game lost"
    detail: str = ""  # why it is paused
    doing: str = ""  # the routine running now, as DOING names it
    started_ts: float | None = None
    upgrades: int = 0
    equipment: int = 0
    ascensions: int = 0
    last_bonus: float | None = None
    tree_nodes: int = 0
    minigames: int = 0
    boxes: int = 0
    quests: int = 0
    problems: int = 0
    nodes_bought: set[str] = field(default_factory=set)  # the names behind `tree_nodes`


def apply(session: Session, record: dict) -> None:
    """Fold one event into the session."""
    name = record.get("event", "")
    if name == "Bot started":
        fresh = Session()  # a new run: counters start again
        for f in fields(Session):
            setattr(session, f.name, getattr(fresh, f.name))
        session.state, session.started_ts = "running", record.get("ts")
    elif name.startswith("Paused: "):
        session.state, session.detail = "paused", name.removeprefix("Paused: ")
    elif name == "Game unavailable":
        session.state, session.detail = "paused", record.get("reason", "")
    elif name in ("Resumed", "Game window found"):
        session.state, session.detail = "running", ""
    elif name == "Game window lost":
        session.state, session.detail = "game lost", ""
    elif name in ("Bot stopped", "Bot stopped after repeated errors"):
        session.state, session.detail, session.doing = "stopped", "", ""
    elif name == "routine_start":
        session.doing = DOING.get(record.get("name", ""), "")
    elif name in ("routine_end", "routine_abort", "tick_crash"):  # a routine that crashes logs no end
        session.doing = ""
    elif name == "AutoUpgrade Done":
        session.upgrades += record.get("upgrades", 0)
        session.equipment += record.get("equipment", 0)
    elif name == "Ascended":
        session.ascensions += 1
    elif name == "Ascend bonus":
        session.last_bonus = record.get("percent")
    elif name == "Tree node bought":
        session.tree_nodes += 1
        session.nodes_bought.add(record.get("node", ""))
    elif name in MINIGAMES:
        session.minigames += 1
    elif name == "Silver Box Collected":
        session.boxes += 1
    elif name == "Quest Claimed":
        session.quests += 1
    if name in ANOMALIES:
        session.problems += 1


def describe(record: dict, session: Session | None = None) -> tuple[str, str] | None:
    """(kind, text) for the activity feed, or None for events that are only noise. kind is one of buy,
    ascend, tree, minigame, box, quest, problem, state. `session` supplies the last "Ascend bonus"."""
    name = record.get("event", "")
    if name in ANOMALIES:
        details = [str(record[key]) for key in DETAIL_FIELDS if key in record]
        return "problem", f"{name}: {', '.join(details)}" if details else name
    if name == "AutoUpgrade Done":
        parts = [f"{record.get('upgrades', 0)} upgrade" + ("s" if record.get("upgrades", 0) != 1 else ""),
                 f"{record.get('equipment', 0)} equipment"]
        parts = [p for p in parts if not p.startswith("0 ")]
        return ("buy", "Bought " + " and ".join(parts)) if parts else None
    if name == "Ascended":
        bonus = session.last_bonus if session else None
        return "ascend", "Ascended" if bonus is None else f"Ascended (+{bonus}% bonus)"
    if name == "Ascend bonus":
        return "ascend", f"Bonus: +{record.get('percent')}%"
    if name == "Tree node bought":
        return "tree", f"Tree: bought {record.get('node')}"
    if name in MINIGAMES:
        return "minigame", f"{MINIGAMES[name]} started"
    if name == "Silver Box Collected":
        return "box", "Silver Box collected"
    if name == "Quest Claimed":
        return "quest", "Quest claimed"
    if name == "Extra daily quests taken":
        return "quest", "Took 2 extra daily quests"
    if name == "Minion claimed":
        return "buy", "A minion came back from its mission"
    if name == "Minion sent":
        return "buy", f"Sent a minion ({record.get('cost')} SP)"
    if name == "Minion not sent" and record.get("reason") == "not enough SP":
        return "buy", f"Minions: not enough SP to send one ({record.get('cost')} SP)"
    if name == "Game settings checked":  # a wrong or missing one is a problem of its own
        return None if record.get("wrong") or record.get("missing") else ("state", "Game settings OK")
    if name == "Game settings check skipped":
        return "state", "Game settings: already checked today"
    if name == "Tree stopped":
        if record.get("reason") == "not enough SP":
            return "tree", f"Tree: next is {record.get('node')}, not enough SP"
        return "tree", f"Tree stopped at {record.get('node')}: {record.get('reason')}"
    if name in ("Bot started", "Bot stopped", "Resumed", "Game window found") or name.startswith("Paused: "):
        return "state", name
    if name == "Game unavailable":
        return "state", f"Game unavailable: {record.get('reason', '')}"
    return None


class EventTail:
    """The records appended to the events file since the last `read_new` call."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.offset = 0  # bytes already consumed: always the end of a complete line

    def read_new(self) -> list[dict]:
        try:
            with self.path.open("rb") as f:
                if f.seek(0, 2) < self.offset:  # the file shrank: it was replaced, start over
                    self.offset = 0
                f.seek(self.offset)
                data = f.read()
        except FileNotFoundError:
            return []
        end = data.rfind(b"\n") + 1  # a partial last line waits for the next call
        self.offset += end
        records = []
        for line in data[:end].splitlines():
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict):
                records.append(record)
        return records

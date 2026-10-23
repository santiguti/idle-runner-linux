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

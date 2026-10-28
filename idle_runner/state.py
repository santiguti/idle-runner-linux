"""What the bot remembers between starts, in `state.json` next to config.toml: the tree nodes it saw bought
(`tree_bought`) and the day the game's settings were last found right (`settings_ok_date`). Losing it costs
only time: a missing or unreadable file is an empty state."""
import json
import os
from pathlib import Path


def state_path(config_path: Path) -> Path:
    return config_path.parent / "state.json"


def load_state(path: Path | None) -> dict:
    """The saved state, or {} when there's no path, no file or no JSON object in it."""
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def update_state(path: Path | None, **changes: object) -> None:
    """Change some keys and keep the rest. Written to a temporary file first, so a stop halfway through
    never leaves half a file."""
    if path is None:
        return
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(load_state(path) | changes, indent=1), encoding="utf-8")
    os.replace(temporary, path)

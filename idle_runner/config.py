"""Settings, read from a TOML file (see config.example.toml)."""
import json
import tomllib
from collections import Counter
from dataclasses import dataclass, fields
from pathlib import Path
from typing import get_origin

from idle_runner.tree_nodes import NODES, RECOMMENDED_ORDER


@dataclass(frozen=True)
class Settings:
    # [game]
    window_name: str = "Idle Slayer"
    offset_x: int = 8
    offset_y: int = 31
    color_tolerance: int = 0
    # [general]
    jump_interval_ms: int = 150
    circle_portals: bool = False
    circle_portals_count: int = 7
    disable_rage_without_soul_bonus: bool = False
    # A new install shops and ascends (Santi, 2026-10-28); the original had both off, every 10 minutes.
    auto_buy_upgrades: bool = True
    auto_buy_minutes: float = 3
    auto_ascend: bool = True
    auto_ascend_minutes: float = 30
    auto_ascend_percent: float = 20
    post_ascend_first_buy_seconds: int = 15
    ascend_bonus_sample_minutes: float = 2.5
    auto_buy_tree: bool = False
    # [tree]
    tree_order: tuple[str, ...] = RECOMMENDED_ORDER
    # [minigames]
    skip_bonus_stage: bool = False
    no_lockpicking: bool = True
    no_reinforced_crystal_saver: bool = False
    perfect_chest_hunt: bool = False
    # [minions]: the Divinities that make missions faster, so the bot knows when each minion is back
    work_benefits: bool = False
    improved_work_conditions: bool = False
    greeks_blessing: bool = False
    # [crafting]
    craft_soul_bonus: bool = False
    craft_rage_pill: bool = False
    craft_dimensional_staff: bool = False
    craft_bidimensional_staff: bool = False
    # [debug]
    log_dir: str = "logs"
    log_level: str = "INFO"
    save_frames: bool = True
    blackbox_fps: float = 4
    blackbox_minutes: float = 60


# Which [section] each setting goes in, in the order of config.example.toml.
SECTIONS: dict[str, tuple[str, ...]] = {
    "game": ("window_name", "offset_x", "offset_y", "color_tolerance"),
    "general": ("jump_interval_ms", "circle_portals", "circle_portals_count", "disable_rage_without_soul_bonus",
                "auto_buy_upgrades", "auto_buy_minutes", "auto_ascend", "auto_ascend_minutes",
                "auto_ascend_percent", "post_ascend_first_buy_seconds", "ascend_bonus_sample_minutes",
                "auto_buy_tree"),
    "tree": ("tree_order",),
    "minigames": ("skip_bonus_stage", "no_lockpicking", "no_reinforced_crystal_saver", "perfect_chest_hunt"),
    "minions": ("work_benefits", "improved_work_conditions", "greeks_blessing"),
    "crafting": ("craft_soul_bonus", "craft_rage_pill", "craft_dimensional_staff", "craft_bidimensional_staff"),
    "debug": ("log_dir", "log_level", "save_frames", "blackbox_fps", "blackbox_minutes"),
}


def load_settings(path: Path) -> Settings:
    """Read a TOML config. Every key is optional; unknown sections or keys, a key in the wrong
    section, wrong types and bad ranges are errors."""
    with path.open("rb") as f:
        data = tomllib.load(f)
    section_of = {key: section for section, keys in SECTIONS.items() for key in keys}
    values: dict[str, object] = {}
    for section, entries in data.items():
        if not isinstance(entries, dict):
            raise ValueError(f"{path}: '{section}' must be a [section] table")
        if section not in SECTIONS:
            raise ValueError(f"{path}: unknown section [{section}]")
        for key, value in entries.items():
            # A key repeated in two sections is always in the wrong one at least once.
            if key in section_of and section_of[key] != section:
                raise ValueError(f"{path}: '{key}' belongs in [{section_of[key]}], not [{section}]")
            values[key] = value

    types = {field.name: field.type for field in fields(Settings)}
    for key, value in values.items():
        if key not in types:
            raise ValueError(f"{path}: unknown setting '{key}'")
        expected = types[key]
        if get_origin(expected) is tuple:  # tree_order: a TOML array of strings
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ValueError(f"{path}: '{key}' must be a list of strings, got {value!r}")
            values[key] = tuple(value)
            continue
        accepted = (int, float) if expected is float else (expected,)
        # bool is a subclass of int in Python, so check it explicitly both ways.
        if isinstance(value, bool) is not (expected is bool) or not isinstance(value, accepted):
            raise ValueError(f"{path}: '{key}' must be {expected.__name__}, got {value!r}")

    settings = Settings(**values)
    check_ranges(path, settings)
    return settings


def check_ranges(path: Path, s: Settings) -> None:
    problems = []
    if not 0 <= s.jump_interval_ms <= 300:
        problems.append("jump_interval_ms must be 0-300")
    if not 1 <= s.circle_portals_count <= 9:
        problems.append("circle_portals_count must be 1-9")
    if s.auto_buy_minutes <= 0 or s.auto_ascend_minutes <= 0:
        problems.append("auto_buy_minutes and auto_ascend_minutes must be > 0")
    if s.ascend_bonus_sample_minutes < 0:
        problems.append("ascend_bonus_sample_minutes must be >= 0")
    if s.auto_ascend_percent < 0:
        problems.append("auto_ascend_percent must be >= 0")
    if s.post_ascend_first_buy_seconds < 0:
        problems.append("post_ascend_first_buy_seconds must be >= 0")
    if not 0 <= s.color_tolerance <= 255:
        problems.append("color_tolerance must be 0-255")
    if s.log_level not in ("DEBUG", "INFO", "WARNING"):
        problems.append("log_level must be DEBUG, INFO or WARNING")
    if not 0 <= s.blackbox_fps <= 30:
        problems.append("blackbox_fps must be 0-30")
    if s.blackbox_minutes <= 0:
        problems.append("blackbox_minutes must be > 0")
    unknown = [name for name in s.tree_order if name not in NODES]
    if unknown:
        problems.append("tree_order: unknown node(s): " + ", ".join(repr(name) for name in unknown))
    problems += [f"tree_order: {name!r} is listed twice" for name, n in Counter(s.tree_order).items() if n > 1]
    if problems:
        raise ValueError(f"{path}: " + "; ".join(problems))


def dump_settings(s: Settings) -> str:
    """`s` as TOML, one [section] per group (what the Idle Runner window saves)."""
    lines = ["# Saved by the Idle Runner window; config.example.toml explains every setting."]
    for section, keys in SECTIONS.items():
        lines += ["", f"[{section}]"]
        for key in keys:
            value = getattr(s, key)
            if isinstance(value, tuple):  # one name per line
                lines += [f"{key} = ["] + [f"    {json.dumps(item)}," for item in value] + ["]"]
                continue
            # json.dumps writes valid TOML for these: true/false, numbers and basic strings.
            lines.append(f"{key} = {json.dumps(value)}")
    return "\n".join(lines) + "\n"

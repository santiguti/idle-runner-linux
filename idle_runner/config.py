"""Settings, read from a TOML file (see config.example.toml)."""
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path


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
    auto_buy_upgrades: bool = False
    auto_buy_minutes: float = 10
    auto_ascend: bool = False
    auto_ascend_minutes: float = 10
    post_ascend_first_buy_seconds: int = 15
    # [minigames]
    skip_bonus_stage: bool = False
    no_lockpicking: bool = True
    no_reinforced_crystal_saver: bool = False
    perfect_chest_hunt: bool = False
    # [crafting]
    craft_soul_bonus: bool = False
    craft_rage_pill: bool = False
    craft_dimensional_staff: bool = False
    craft_bidimensional_staff: bool = False
    # [debug]
    log_dir: str = "logs"
    log_level: str = "INFO"
    save_frames: bool = True


# Which [section] each setting goes in, in the order of config.example.toml.
SECTIONS: dict[str, tuple[str, ...]] = {
    "game": ("window_name", "offset_x", "offset_y", "color_tolerance"),
    "general": ("jump_interval_ms", "circle_portals", "circle_portals_count", "disable_rage_without_soul_bonus",
                "auto_buy_upgrades", "auto_buy_minutes", "auto_ascend", "auto_ascend_minutes",
                "post_ascend_first_buy_seconds"),
    "minigames": ("skip_bonus_stage", "no_lockpicking", "no_reinforced_crystal_saver", "perfect_chest_hunt"),
    "crafting": ("craft_soul_bonus", "craft_rage_pill", "craft_dimensional_staff", "craft_bidimensional_staff"),
    "debug": ("log_dir", "log_level", "save_frames"),
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
        accepted = (int, float) if expected is float else (expected,)
        # bool is a subclass of int in Python, so check it explicitly both ways.
        if isinstance(value, bool) is not (expected is bool) or not isinstance(value, accepted):
            raise ValueError(f"{path}: '{key}' must be {expected.__name__}, got {value!r}")

    settings = Settings(**values)
    _check_ranges(path, settings)
    return settings


def _check_ranges(path: Path, s: Settings) -> None:
    problems = []
    if not 0 <= s.jump_interval_ms <= 300:
        problems.append("jump_interval_ms must be 0-300")
    if not 1 <= s.circle_portals_count <= 9:
        problems.append("circle_portals_count must be 1-9")
    if s.auto_buy_minutes <= 0 or s.auto_ascend_minutes <= 0:
        problems.append("auto_buy_minutes and auto_ascend_minutes must be > 0")
    if s.post_ascend_first_buy_seconds < 0:
        problems.append("post_ascend_first_buy_seconds must be >= 0")
    if not 0 <= s.color_tolerance <= 255:
        problems.append("color_tolerance must be 0-255")
    if s.log_level not in ("DEBUG", "INFO", "WARNING"):
        problems.append("log_level must be DEBUG, INFO or WARNING")
    if problems:
        raise ValueError(f"{path}: " + "; ".join(problems))

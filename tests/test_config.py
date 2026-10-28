from dataclasses import fields
from pathlib import Path

import pytest

from idle_runner.config import SECTIONS, Settings, dump_settings, load_settings
from idle_runner.tree_nodes import RECOMMENDED_ORDER

EXAMPLE = Path(__file__).resolve().parents[1] / "config.example.toml"


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_defaults_match_the_original(tmp_path) -> None:
    s = load_settings(write(tmp_path, ""))
    assert s.jump_interval_ms == 150
    assert s.no_lockpicking is True
    assert s.circle_portals_count == 7


def test_a_new_install_shops_and_ascends(tmp_path) -> None:
    # Santi, 2026-10-28, after trying the Windows download as a new user: the original's defaults (no buying,
    # no ascending) left the bot doing almost nothing.
    s = load_settings(write(tmp_path, ""))
    assert s.auto_buy_upgrades and s.auto_buy_minutes == 3 and s.post_ascend_first_buy_seconds == 15
    assert s.auto_ascend and s.auto_ascend_minutes == 30 and s.auto_ascend_percent == 20
    assert s.ascend_bonus_sample_minutes == 2.5  # the % is only seen when it's read
    assert not s.auto_buy_tree


def test_sections_are_flattened(tmp_path) -> None:
    s = load_settings(write(tmp_path, "[general]\nauto_buy_upgrades = true\nauto_buy_minutes = 2.5\n"))
    assert s.auto_buy_upgrades is True
    assert s.auto_buy_minutes == 2.5


def test_the_old_frame_offset_is_ignored(tmp_path) -> None:
    # The offset (8, 31) only converts the original's coordinates to the game's picture, the same on every PC.
    # It was a setting until 2026-10-28, when a saved 30 silently broke single-pixel checks; old files keep it.
    s = load_settings(write(tmp_path, "[game]\noffset_x = 8\noffset_y = 30\n"))

    assert not hasattr(s, "offset_y")
    assert "offset" not in dump_settings(s)


def test_unknown_key_is_an_error(tmp_path) -> None:
    with pytest.raises(ValueError, match="unknown setting 'auto_bu_upgrades'"):
        load_settings(write(tmp_path, "[general]\nauto_bu_upgrades = true\n"))


def test_wrong_type_is_an_error(tmp_path) -> None:
    with pytest.raises(ValueError, match="'jump_interval_ms' must be int"):
        load_settings(write(tmp_path, '[general]\njump_interval_ms = "fast"\n'))
    with pytest.raises(ValueError, match="'jump_interval_ms' must be int"):
        load_settings(write(tmp_path, "[general]\njump_interval_ms = true\n"))


def test_out_of_range_is_an_error(tmp_path) -> None:
    with pytest.raises(ValueError, match="jump_interval_ms must be 0-300"):
        load_settings(write(tmp_path, "[general]\njump_interval_ms = 301\n"))


def test_ascend_percent_without_bonus_samples_is_allowed(tmp_path) -> None:
    # "Check the bonus every 0" turns ascending at a bonus off, as the Settings page says: the bonus is never
    # read. With the default 20 % it was an error the moment someone set the checks to 0.
    s = load_settings(write(tmp_path, "[general]\nauto_ascend_percent = 10\nascend_bonus_sample_minutes = 0\n"))
    assert s.auto_ascend_percent == 10 and s.ascend_bonus_sample_minutes == 0


def test_tree_buying_is_off_by_default(tmp_path) -> None:
    assert load_settings(write(tmp_path, "")).auto_buy_tree is False
    assert load_settings(write(tmp_path, "[general]\nauto_buy_tree = true\n")).auto_buy_tree is True


def test_example_config_documents_the_defaults() -> None:
    assert load_settings(EXAMPLE) == Settings()


def test_unknown_section_is_an_error(tmp_path) -> None:
    with pytest.raises(ValueError, match=r"unknown section \[generl\]"):
        load_settings(write(tmp_path, "[generl]\nauto_buy_upgrades = true\n"))


def test_key_in_the_wrong_section_is_an_error(tmp_path) -> None:
    with pytest.raises(ValueError, match=r"'auto_buy_upgrades' belongs in \[general\], not \[game\]"):
        load_settings(write(tmp_path, "[game]\nauto_buy_upgrades = true\n"))


def test_key_repeated_across_sections_is_an_error(tmp_path) -> None:
    with pytest.raises(ValueError, match=r"'jump_interval_ms' belongs in \[general\], not \[game\]"):
        load_settings(write(tmp_path, "[general]\njump_interval_ms = 100\n[game]\njump_interval_ms = 200\n"))


def test_every_setting_belongs_to_exactly_one_section() -> None:
    keys = [key for section_keys in SECTIONS.values() for key in section_keys]
    assert sorted(keys) == sorted(field.name for field in fields(Settings))


def test_black_box_settings(tmp_path) -> None:
    s = load_settings(write(tmp_path, "[debug]\nblackbox_fps = 10\nblackbox_minutes = 30\n"))
    assert (s.blackbox_fps, s.blackbox_minutes) == (10, 30)
    assert load_settings(write(tmp_path, "[debug]\nblackbox_fps = 0\n")).blackbox_fps == 0  # off
    with pytest.raises(ValueError, match="blackbox_fps must be 0-30"):
        load_settings(write(tmp_path, "[debug]\nblackbox_fps = 31\n"))
    with pytest.raises(ValueError, match="blackbox_minutes must be > 0"):
        load_settings(write(tmp_path, "[debug]\nblackbox_minutes = 0\n"))


def test_dump_settings_round_trips(tmp_path) -> None:
    settings = Settings(window_name='Idle "Slayer"', auto_buy_upgrades=True, auto_buy_minutes=2.5,
                        jump_interval_ms=120, blackbox_fps=0)

    assert load_settings(write(tmp_path, dump_settings(settings))) == settings


V1_CONFIG = ("[game]\nwindow_name = \"Idle Slayer\"\n[general]\nauto_buy_tree = true\n"
             "[minigames]\nperfect_chest_hunt = true\n")


def test_v1_config_loads_with_the_recommended_order(tmp_path) -> None:
    assert load_settings(write(tmp_path, V1_CONFIG)).tree_order == RECOMMENDED_ORDER


def test_custom_tree_order_round_trips(tmp_path) -> None:
    settings = Settings(tree_order=("Doesn't Matter to Me", "Portals"))
    text = dump_settings(settings)

    assert '[tree]\ntree_order = [\n    "Doesn\'t Matter to Me",\n    "Portals",\n]\n' in text
    assert load_settings(write(tmp_path, text)).tree_order == settings.tree_order


def test_an_empty_tree_order_is_allowed(tmp_path) -> None:
    assert load_settings(write(tmp_path, "[tree]\ntree_order = []\n")).tree_order == ()


def test_unknown_tree_node_is_an_error(tmp_path) -> None:
    with pytest.raises(ValueError, match="tree_order: unknown node.*'Moon Boots'"):
        load_settings(write(tmp_path, '[tree]\ntree_order = ["Portals", "Moon Boots"]\n'))


def test_duplicate_tree_node_is_an_error(tmp_path) -> None:
    with pytest.raises(ValueError, match="tree_order: 'Portals' is listed twice"):
        load_settings(write(tmp_path, '[tree]\ntree_order = ["Portals", "Green Ore", "Portals"]\n'))


def test_tree_order_must_be_a_list_of_strings(tmp_path) -> None:
    with pytest.raises(ValueError, match="'tree_order' must be a list of strings"):
        load_settings(write(tmp_path, '[tree]\ntree_order = "Portals"\n'))
    with pytest.raises(ValueError, match="'tree_order' must be a list of strings"):
        load_settings(write(tmp_path, "[tree]\ntree_order = [1, 2]\n"))


def test_an_array_for_any_other_setting_is_a_type_error(tmp_path) -> None:
    with pytest.raises(ValueError, match="'jump_interval_ms' must be int"):
        load_settings(write(tmp_path, "[general]\njump_interval_ms = [1]\n"))


def test_tree_order_belongs_in_the_tree_section(tmp_path) -> None:
    with pytest.raises(ValueError, match=r"'tree_order' belongs in \[tree\], not \[general\]"):
        load_settings(write(tmp_path, '[general]\ntree_order = ["Portals"]\n'))


def test_minion_divinities_are_off_by_default(tmp_path) -> None:
    path = tmp_path / "config.toml"
    path.write_text("[minions]\nwork_benefits = true\n", encoding="utf-8")
    settings = load_settings(path)

    assert settings.work_benefits and not settings.improved_work_conditions and not settings.greeks_blessing

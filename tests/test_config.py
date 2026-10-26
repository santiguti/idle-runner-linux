from dataclasses import fields
from pathlib import Path

import pytest

from idle_runner.config import SECTIONS, Settings, dump_settings, load_settings

EXAMPLE = Path(__file__).resolve().parents[1] / "config.example.toml"


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(text)
    return path


def test_defaults_match_the_original(tmp_path) -> None:
    s = load_settings(write(tmp_path, ""))
    assert s.jump_interval_ms == 150
    assert s.auto_buy_minutes == 10 and s.auto_ascend_minutes == 10
    assert s.no_lockpicking is True
    assert s.circle_portals_count == 7


def test_sections_are_flattened(tmp_path) -> None:
    s = load_settings(write(tmp_path, "[general]\nauto_buy_upgrades = true\nauto_buy_minutes = 2.5\n"))
    assert s.auto_buy_upgrades is True
    assert s.auto_buy_minutes == 2.5


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


def test_ascend_percent_needs_bonus_samples(tmp_path) -> None:
    with pytest.raises(ValueError, match="auto_ascend_percent needs ascend_bonus_sample_minutes > 0"):
        load_settings(write(tmp_path, "[general]\nauto_ascend_percent = 10\n"))
    s = load_settings(write(tmp_path, "[general]\nauto_ascend_percent = 10\nascend_bonus_sample_minutes = 1\n"))
    assert s.auto_ascend_percent == 10


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

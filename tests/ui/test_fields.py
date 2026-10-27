from dataclasses import fields, replace
from pathlib import Path

import pytest

from idle_runner.config import Settings, check_ranges
from idle_runner.ui.fields import CARDS, FIELDS, friendly


def test_every_setting_has_a_field() -> None:
    assert set(FIELDS) == {f.name for f in fields(Settings)} - {"tree_order"}


def test_every_field_names_a_card() -> None:
    assert {f.card for f in FIELDS.values()} <= set(CARDS)


@pytest.mark.parametrize("key", [k for k, f in FIELDS.items() if f.minimum is not None or f.maximum is not None])
def test_field_limits_pass_check_ranges(key: str) -> None:
    kind = {f.name: f.type for f in fields(Settings)}[key]
    base = Settings(ascend_bonus_sample_minutes=5)  # ascending at a bonus needs the bonus checked
    for limit in (FIELDS[key].minimum, FIELDS[key].maximum):
        if limit is not None:
            check_ranges(Path("x"), replace(base, **{key: kind(limit)}))  # no ValueError


@pytest.mark.parametrize(("key", "value"), [("jump_interval_ms", 301), ("circle_portals_count", 10),
                                            ("color_tolerance", 256), ("blackbox_fps", 31)])
def test_beyond_a_field_limit_check_ranges_complains(key: str, value: int) -> None:
    assert FIELDS[key].maximum == value - 1
    with pytest.raises(ValueError):
        check_ranges(Path("x"), replace(Settings(), **{key: value}))


def test_problems_are_shown_with_field_labels() -> None:
    assert friendly("config.toml: jump_interval_ms must be 0-300") == "“Time between jumps” must be 0-300"

from pathlib import Path

import pytest

from idle_runner.ascend_bonus import read_ascend_bonus
from tests.fakes import read_png

FIXTURES = Path(__file__).parent / "fixtures" / "ascend_bonus"


@pytest.mark.parametrize(("name", "expected"), [
    # Next to the Ultra Ascend button (before the Ultra Ascension); "+4%" and "+1.1%" are drawn bigger.
    ("two-4", 4.0), ("two-10.8", 10.8), ("two-14.6", 14.6), ("two-0.9", 0.9), ("two-1.1", 1.1),
    ("two-15.1", 15.1),
    ("two-0", 0.0),  # "+0": no "% CpS bonus" line, nothing to claim
    # Alone and centred (after it).
    ("one-3", 3.0), ("one-15", 15.0), ("one-0", 0.0),
    # Gold numbers (FFC14D) while the game tags the button "Recommended" (2026-10-28).
    ("one-53.9-gold", 53.9), ("one-62.7-gold", 62.7), ("one-103-gold", 103.0),
])
def test_reads_the_cps_bonus_on_the_ascend_button(game, fake, name: str, expected: float) -> None:
    fake.frame[440:600, 80:450] = read_png(FIXTURES / f"{name}.png")  # client area, as recorded 2026-10-23

    assert read_ascend_bonus(game) == expected


def test_no_ascension_panel_reads_as_none(game, fake) -> None:
    assert read_ascend_bonus(game) is None

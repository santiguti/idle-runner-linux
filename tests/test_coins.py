from pathlib import Path

import pytest

from idle_runner.coins import read_coins
from tests.fakes import read_png

FIXTURES = Path(__file__).parent / "fixtures" / "coins"


@pytest.mark.parametrize(("name", "expected"), [
    ("0", 0.0), ("3", 3.0), ("7.5", 7.5), ("26.3", 26.3), ("63.8", 63.8),
    ("3-banner", None),     # "New entry added to the Bestiary" covers the counter
    ("big-7.11Dd", None),   # big numbers with a suffix aren't needed: only the start of a run
])
def test_reads_the_coin_counter_after_an_ascension(game, fake, name: str, expected: float | None) -> None:
    fake.frame[30:100, 480:800] = read_png(FIXTURES / f"{name}.png")  # client area, as recorded 2026-10-22

    assert read_coins(game) == expected


@pytest.mark.parametrize(("name", "expected"), [
    ("69.5", 69.5), ("97.5", 97.5), ("109", 109.0), ("219", 219.0), ("198", 198.0),  # recorded 2026-10-23
    ("697", 697.0), ("999", 999.0),  # 2026-10-26, two nines in a row
])
def test_reads_nine(game, fake, name: str, expected: float) -> None:
    fake.frame[30:100, 480:800] = read_png(FIXTURES / f"{name}.png")

    assert read_coins(game) == expected


@pytest.mark.parametrize(("name", "expected"), [
    ("1,251", 1251.0), ("8,711", 8711.0), ("4,445", 4445.0),  # after an Ultra Ascension (2026-10-26)
])
def test_reads_thousands_with_a_comma(game, fake, name: str, expected: float) -> None:
    fake.frame[30:100, 480:800] = read_png(FIXTURES / f"{name}.png")

    assert read_coins(game) == expected

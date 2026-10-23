from pathlib import Path

import pytest

from idle_runner.actions import box_on_screen
from tests.fakes import read_png

FIXTURES = Path(__file__).parent / "fixtures" / "boxes"


@pytest.mark.parametrize(("name", "expected"), [
    ("silver-box", True),              # flying in (recorded 2026-10-23, shop open on the right)
    ("silver-box-over-player", True),  # hovering over the player, waiting to be hit
    ("no-box", False),
    ("no-box-wasps", False),
])
def test_floating_silver_box_is_detected(game, fake, name: str, expected: bool) -> None:
    fake.frame[100:480, 0:790] = read_png(FIXTURES / f"{name}.png")  # client area, as recorded

    assert box_on_screen(game) is expected

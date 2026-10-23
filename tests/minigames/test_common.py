from idle_runner.minigames.common import slider
from tests.fakes import OFFSET


def test_slider_drags_the_handle_across(game, fake) -> None:
    fake.paint(442, 560, 0x007E00)  # handle found by the "top left" search
    slider(game)

    assert fake.clicks() == [(840, 560)]                       # pressed at the drag start
    assert fake.pointer == (450 - OFFSET[0], 560 - OFFSET[1])  # released at the drag end

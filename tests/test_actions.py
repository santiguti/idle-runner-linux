from pathlib import Path

import pytest

from idle_runner.actions import collect_minions, box_on_screen, close_all
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


def test_close_all_does_not_blind_the_main_loop(game, fake) -> None:
    start = fake.t

    close_all(game)

    assert fake.t - start < 100  # the original slept 2 s here, every 5 s


def open_panel_on_click(fake, minions_tab: bool) -> None:
    """The ascension panel opens on its Ascension tab (2026-10-26); the Minions tab, when the node is
    bought, turns the selected shade when clicked. Without it, (332, 676) is the empty tab bar (3E260A)."""
    def act(action: tuple) -> None:
        if action == ("click", 95 - 8, 90 - 31):
            fake.paint(538, 681, 0xAD1111)
            fake.paint(260, 480, 0x58188D)
        elif action == ("click", 332 - 8, 680 - 31):
            fake.paint(332, 676, 0x5E261B if minions_tab else 0x3E260A)
    fake.on_action = act


def test_collect_minions_claims_nothing_without_the_minions_tab(game, fake, event_names) -> None:
    # After an Ultra Ascension there is no Minions tab until the node is bought again, but the trigger still
    # fired (2026-10-26) and the claim clicks landed in the Ascension Tree.
    open_panel_on_click(fake, minions_tab=False)
    collect_minions(game)

    assert (318, 182) not in fake.clicks() and (320, 280) not in fake.clicks()
    assert "Minions tab not shown" in event_names()
    assert fake.clicks()[-1] == (570, 694)


def test_collect_minions_claims_on_the_minions_tab(game, fake, event_names) -> None:
    open_panel_on_click(fake, minions_tab=True)
    collect_minions(game)

    assert fake.clicks().count((318, 182)) == 10
    assert "Minions Collect" in event_names()

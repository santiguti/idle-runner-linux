from dataclasses import replace
from pathlib import Path

import pytest

from idle_runner import minions
from idle_runner.config import Settings
from idle_runner.minions import mission_ms, read_available_sp, read_mission_cost, send_buttons, send_minions
from tests.fakes import OFFSET, read_png

FIXTURES = Path(__file__).parent / "fixtures" / "minions"
# The two minions' buttons in send-526.png (black box 2026-10-28 00:17:10): AutoIt y of their top edge.
WHITE_KNIGHT, DARK_WIZARD = 222 + 31, 372 + 31


def show_panel(fake, name: str) -> None:
    """A Minions tab recorded live (client x 0-639): "send-526" with both minions ready to send and
    526 SP available (black box 2026-10-28), "away-1676" with both on a mission (Santi's screenshot)."""
    fake.frame[:, :640] = read_png(FIXTURES / f"{name}.png")


@pytest.mark.parametrize(("name", "expected"), [("send-526", 526), ("away-1676", 1_676)])
def test_reads_the_available_sp_in_the_minions_tab(game, fake, name: str, expected: int) -> None:
    show_panel(fake, name)

    assert read_available_sp(game) == expected


def test_reads_an_available_sp_with_a_thousands_comma(game, fake) -> None:
    # The tree tab's header ("21,048 available", black box 2026-10-28 00:45:11) sits further right.
    fake.frame[20:65, :640] = read_png(FIXTURES / "tree-header-21048.png")

    assert read_available_sp(game) == 21_048


def test_no_panel_reads_no_sp(game, fake) -> None:
    assert read_available_sp(game) is None


def test_finds_whole_send_buttons_and_reads_their_cost(game, fake) -> None:
    show_panel(fake, "send-526")

    assert send_buttons(game) == [WHITE_KNIGHT, DARK_WIZARD]
    assert [read_mission_cost(game, top) for top in send_buttons(game)] == [10, 150]


def test_minions_on_a_mission_have_no_send_button(game, fake) -> None:
    show_panel(fake, "away-1676")

    assert send_buttons(game) == []


def in_button(click: tuple[int, int], top: int) -> bool:
    return 423 <= click[0] <= 621 and top <= click[1] <= top + 122


def play_minions_tab(fake, monkeypatch, available: int | None, takes_effect: bool = True) -> list[int]:
    """The ascension panel opens, its Minions tab shows send-526, and a click on a send button sends that
    minion: the button turns "On a Mission..." and its cost leaves the header's SP. Returns the costs sent."""
    sent: list[int] = []
    costs = {WHITE_KNIGHT: 10, DARK_WIZARD: 150}

    def act(action: tuple) -> None:
        if action[0] != "click":
            return
        click = (action[1] + OFFSET[0], action[2] + OFFSET[1])
        if click == (95, 90):  # the ascension button opens the panel on its Ascension tab
            fake.paint(538, 681, 0xAD1111)
            fake.paint(260, 480, 0x58188D)
        elif click == (332, 680):  # the Minions tab
            show_panel(fake, "send-526")
        for top, cost in costs.items():
            if in_button(click, top) and takes_effect:
                fake.paint(438, top, 0x975DCA, w=1, h=123)
                sent.append(cost)

    fake.on_action = act
    monkeypatch.setattr(minions, "read_available_sp",
                        lambda game: None if available is None else available - sum(sent))
    return sent


def test_sends_every_minion_the_sp_covers(game, fake, monkeypatch, event_names) -> None:
    sent = play_minions_tab(fake, monkeypatch, available=526)

    assert send_minions(game) == [10, 150]  # the costs it sent: they tell when each mission ends
    assert sent == [10, 150]
    assert event_names().count("Minion sent") == 2
    assert fake.clicks()[-1] == (570, 694)  # closed the panel


def test_never_clicks_a_mission_the_sp_does_not_cover(game, fake, monkeypatch, events) -> None:
    # Without enough SP the game may offer to pay the rest with jewels, as the tree did on 2026-10-26.
    sent = play_minions_tab(fake, monkeypatch, available=100)
    send_minions(game)

    assert sent == [10]
    assert not [c for c in fake.clicks() if in_button(c, DARK_WIZARD)]
    skipped = [r for r in events() if r["event"] == "Minion not sent"]
    assert skipped and skipped[-1]["reason"] == "not enough SP" and skipped[-1]["cost"] == 150


def test_unreadable_sp_sends_nothing(game, fake, monkeypatch, event_names) -> None:
    play_minions_tab(fake, monkeypatch, available=None)
    send_minions(game)

    assert not [c for c in fake.clicks() if in_button(c, WHITE_KNIGHT) or in_button(c, DARK_WIZARD)]
    assert "Minions SP not readable" in event_names()


def test_a_send_without_effect_is_not_clicked_again(game, fake, monkeypatch, events) -> None:
    play_minions_tab(fake, monkeypatch, available=526, takes_effect=False)
    send_minions(game)

    assert len([c for c in fake.clicks() if in_button(c, WHITE_KNIGHT) or in_button(c, DARK_WIZARD)]) == 1
    assert any(r["event"] == "Minion not sent" and r["reason"] == "no effect" for r in events())


def test_nothing_is_clicked_without_the_minions_tab(game, fake, event_names) -> None:
    # After an Ultra Ascension there is no Minions tab until the node is bought again: (332, 680) is the
    # empty tab bar (3E260A), and clicks meant for minions would land in the tree.
    def act(action: tuple) -> None:
        if action == ("click", 95 - 8, 90 - 31):
            fake.paint(538, 681, 0xAD1111)
            fake.paint(260, 480, 0x58188D)
        elif action == ("click", 332 - 8, 680 - 31):
            fake.paint(332, 676, 0x3E260A)

    fake.on_action = act
    send_minions(game)

    assert fake.clicks() == [(95, 90), (93, 680), (332, 680), (570, 694)]
    assert "Minions tab not shown" in event_names()


def test_a_tab_without_known_buttons_is_kept_for_a_look(game, fake, monkeypatch, events) -> None:
    # Buttons that are neither Send, On a Mission nor Claim: keep a frame to see what they are.
    play_minions_tab(fake, monkeypatch, available=526)
    send_panel = fake.on_action

    def other_buttons(action: tuple) -> None:
        send_panel(action)
        if action == ("click", 332 - 8, 680 - 31):
            fake.paint(438, WHITE_KNIGHT, 0x7A7A7A, w=1, h=123)
            fake.paint(438, DARK_WIZARD, 0x7A7A7A, w=1, h=123)

    fake.on_action = other_buttons
    send_minions(game)

    assert "Minions buttons unknown" in [r["event"] for r in events()]
    assert any(r["event"] == "frame" and r["label"] == "minions-buttons-unknown" for r in events())


def finished_white_knight(fake, monkeypatch, claim_takes_effect: bool = True) -> list[int]:
    """send-526 with the White Knight back from its mission: a green "Claim" button (11A622, Santi
    2026-10-28: the shop's Unlock green). Claiming turns it into "Send on Mission"."""
    sent = play_minions_tab(fake, monkeypatch, available=526)
    send_panel = fake.on_action

    def act(action: tuple) -> None:
        click = (action[1] + OFFSET[0], action[2] + OFFSET[1]) if action[0] == "click" else None
        if click and in_button(click, WHITE_KNIGHT) and fake.frame[WHITE_KNIGHT - 31, 430][1] == 0xA6:
            if claim_takes_effect:
                fake.paint(438, WHITE_KNIGHT, 0x541787, w=1, h=123)
            return
        send_panel(action)
        if action == ("click", 332 - 8, 680 - 31):
            fake.paint(438, WHITE_KNIGHT, 0x11A622, w=1, h=123)

    fake.on_action = act
    return sent


def test_claims_a_finished_mission_then_sends_the_minion_again(game, fake, monkeypatch, event_names) -> None:
    sent = finished_white_knight(fake, monkeypatch)
    send_minions(game)

    knight_clicks = [c for c in fake.clicks() if in_button(c, WHITE_KNIGHT)]
    assert len(knight_clicks) == 2  # the claim, then the send
    assert "Minion claimed" in event_names()
    assert sent == [10, 150]


def test_a_claim_without_effect_is_not_clicked_again(game, fake, monkeypatch, event_names) -> None:
    finished_white_knight(fake, monkeypatch, claim_takes_effect=False)
    send_minions(game)

    assert len([c for c in fake.clicks() if in_button(c, WHITE_KNIGHT)]) == 1
    assert "Minion not claimed" in event_names()


@pytest.mark.parametrize(("divinities", "minutes"), [
    ((), 180),
    (("work_benefits", "improved_work_conditions"), 117),  # wiki: "under 2 hours" with these two
    (("work_benefits", "improved_work_conditions", "greeks_blessing"), 72),
])
def test_a_white_knight_mission_lasts_3_hours_less_the_divinities(divinities: tuple[str, ...], minutes: int) -> None:
    settings = replace(Settings(), **{name: True for name in divinities})

    assert mission_ms(10, settings) == pytest.approx(minutes * 60_000)


def test_each_mission_cost_tells_its_length() -> None:
    # Wiki, Minions: White Knight 10 SP 3h00m, Dark Wizard 150 SP 6h30m, Skeleton 1,000 SP 3h00m,
    # Goo Mutant 1,500 SP 4h30m, Stone Golem 3,000 SP 23h00m.
    assert [mission_ms(cost, Settings()) for cost in (10, 150, 1_000, 1_500, 3_000)] == [
        m * 60_000 for m in (180, 390, 180, 270, 1_380)]
    assert mission_ms(42, Settings()) is None


def test_minions_right_after_the_tree_reuse_its_open_panel(game, fake, monkeypatch) -> None:
    # The tree leaves the panel open; the ascension button there is the tree's "Buy on Click" toggle.
    sent = play_minions_tab(fake, monkeypatch, available=526)
    fake.paint(538, 681, 0xAD1111)  # the panel's X tab: open, on the tree tab
    fake.paint(260, 480, 0x58188D)  # what the Ascension tab shows once clicked
    send_minions(game)

    assert (95, 90) not in fake.clicks()
    assert fake.clicks()[0] == (93, 680) and sent == [10, 150]


def test_waits_for_the_minions_tab_to_fade_in(game, fake, monkeypatch) -> None:
    # Live 2026-10-28 02:43: right after the tree, the Ascension and Minions tab clicks came 28 ms apart; the
    # Minions list showed, but 200 ms after the click its tab wasn't the selected shade yet.
    sent = play_minions_tab(fake, monkeypatch, available=526)
    act, grab, due = fake.on_action, fake.grab, []

    def tab_late(action: tuple) -> None:
        if action[0] == "click" and (action[1] + OFFSET[0], action[2] + OFFSET[1]) == (332, 680):
            due.append(fake.t + 400)
            return
        act(action)

    def grab_late(x: int, y: int, w: int, h: int):
        if due and fake.t >= due[0]:
            due.clear()
            show_panel(fake, "send-526")
        return grab(x, y, w, h)

    fake.on_action, fake.grab = tab_late, grab_late
    send_minions(game)

    assert sent == [10, 150]

import pytest

from idle_runner.shop import QUEST_REWARD_BLUE, BoxOnScreen, Shop, scroll_to_top
from tests.fakes import OFFSET


def client_click(x: int, y: int) -> tuple:
    """The FakeBackend action recorded for a click at AutoIt (x, y)."""
    return ("click", x - OFFSET[0], y - OFFSET[1])


def show_tab(fake, tab: str) -> None:
    """Paint the shop's tab bar as measured on 2026-10-22: the selected tab is darker, and only the
    Upgrades tab has the grey "Buy all available" bar at (1180, 636)."""
    if tab == "upgrades":
        fake.paint(897, 700, 0x5A251A)
        fake.paint(1180, 636, 0xA8A8A8)
    elif tab == "armor":
        fake.paint(820, 700, 0x5E261B)
        fake.paint(1180, 636, 0x898989)


ROW_ICONS = {"vm": 0xF4B41B, "svm": 0xE478FF}  # Vertical Magnet / Special Vertical Magnet icon colours


def paint_rows(fake, kinds: list, first_separator: int = 153, icon_rows: tuple[int, int] = (40, 50)) -> None:
    """Upgrades rows as measured on 2026-10-22: a black separator every 96 px (the first at y = 153 at
    the list's top), background 454545, an icon colour in x 885-905 for excluded rows, and the buy
    button at x 1160-1199, green for "buy", "vm" and "svm" rows, red for "red". Only y 153-609 shows.
    Each row also gets its own text colour (like its name in the game); a kind can be (kind, id)."""
    def band(x: int, y0: int, y1: int, w: int, color: int) -> None:
        y0, y1 = max(y0, 153), min(y1, 609)
        if y0 <= y1:
            fake.paint(x, y0, color, w=w, h=y1 - y0 + 1)

    band(800, 153, 609, 472, 0x454545)
    for i, item in enumerate(kinds):
        kind, ident = item if isinstance(item, tuple) else (item, i)
        top = first_separator + 96 * i
        band(800, top, top + 2, 472, 0x000000)
        band(950, top + 30, top + 40, 40, 0x203040 + 0x10 * ident)  # the row's own "name"
        band(1160, top + 3, top + 95, 40, 0xA91111 if kind == "red" else 0x11A622)
        if kind in ROW_ICONS:
            band(885, top + icon_rows[0], top + icon_rows[1], 20, ROW_ICONS[kind])
    band(800, first_separator + 96 * len(kinds), first_separator + 96 * len(kinds) + 2, 472, 0x000000)


def buying_removes_rows(fake, kinds: list[str], first_separator: int = 153) -> list[str]:
    """Each click on a row's button buys it: the row disappears and the rows below move up."""
    rows = [(kind, i) for i, kind in enumerate(kinds)]
    paint_rows(fake, rows, first_separator)

    def on_action(action: tuple) -> None:
        if action[0] != "click":
            return
        x, y = action[1] + OFFSET[0], action[2] + OFFSET[1]
        index = (y - first_separator) // 96
        if 1160 <= x <= 1199 and 0 <= index < len(rows) and rows[index][0] != "red":
            del rows[index]
            paint_rows(fake, rows, first_separator)

    fake.on_action = on_action
    return rows


def test_buy_upgrade_clicks_green_rows_until_none_is_left(game, fake) -> None:
    show_tab(fake, "upgrades")
    buying_removes_rows(fake, ["buy", "buy", "buy", "red"])
    shop = Shop(game)
    shop.loop_amount = 6  # no equipment round: the shop closes right away
    shop.buy_upgrade()

    assert fake.clicks().count((1180, 170)) == 3
    assert fake.clicks()[-1] == (1222, 677)
    assert shop.upgrades_bought == 3


def test_buy_upgrade_skips_the_excluded_upgrades(game, fake) -> None:
    show_tab(fake, "upgrades")
    buying_removes_rows(fake, ["vm", "buy", "red"])
    shop = Shop(game)
    shop.loop_amount = 6
    shop.buy_upgrade()

    assert fake.clicks().count((1180, 266)) == 1
    assert (1180, 170) not in fake.clicks()


def test_auto_upgrade_logs_when_the_shop_does_not_open(game, fake, event_names) -> None:
    Shop(game).auto_upgrade()

    assert fake.clicks() == [(1244, 712), (1163, 655), (1163, 655)]  # the second: a lost click is retried once
    assert "AutoUpgrade shop not open" in event_names()
    assert "AutoUpgrade Done" in event_names()


def test_stuck_scrollbar_is_reported_instead_of_looping_forever(game, fake, events) -> None:
    show_tab(fake, "upgrades")
    fake.paint(1254, 167, 0xA0A0A0)  # the scrollbar's track, at its top, never goes away
    shop = Shop(game)
    shop.loop_amount = 6
    shop.buy_upgrade()

    assert any(r["event"] == "stuck" and r["where"] == "buy_upgrade.scroll_top" for r in events())


def test_claim_quests_clicks_green_claim_buttons(game, fake, event_names) -> None:
    fake.paint(807, 145, 0xFFFFFF)  # the shop is open
    fake.paint(1160, 300, 0x11A622)
    fake.on_action = lambda a: fake.paint(1160, 300, 0) if a == client_click(1160, 300) else None
    Shop(game).claim_quests()

    assert (1160, 300) in fake.clicks()
    assert event_names().count("Quest Claimed") == 1
    assert fake.clicks()[-1] == (1244, 712)


def test_auto_ascend_when_the_panel_is_already_open(game, fake, event_names) -> None:
    fake.paint(260, 600, 0x58188D)

    assert Shop(game).auto_ascend() is True
    assert fake.clicks()[:4] == [(260, 600), (550, 580), (1244, 712), (1163, 655)]
    assert "Ascended" in event_names()


def test_auto_ascend_logs_and_saves_a_frame_when_the_button_is_missing(game, fake, event_names) -> None:
    assert Shop(game).auto_ascend() is False
    assert fake.clicks() == [(95, 90), (93, 680)]
    assert "Ascend skipped" in event_names()
    assert "frame" in event_names()


def test_claim_quests_saves_frames_of_what_it_saw(game, fake, events) -> None:
    fake.paint(807, 145, 0xFFFFFF)  # the shop is open, with nothing to claim
    Shop(game).claim_quests()

    labels = [r["label"] for r in events() if r["event"] == "frame"]
    assert labels == ["claim-quests-start", "claim-quests-end"]


def paint_upgrades(fake, quest_rewards: int, offset: int, buyable: bool = True) -> None:
    """The Upgrades list scrolled down `offset` px, as measured on 2026-10-22: separators every 96 px
    (the first at y = 153 when the list is at its top), `quest_rewards` blue event rows with a grey
    "Quest Reward" button, then rows with a green buy button."""
    def band(x: int, y0: int, y1: int, w: int, color: int) -> None:
        y0, y1 = max(y0, 153), min(y1, 609)  # the visible list
        if y0 <= y1:
            fake.paint(x, y0, color, w=w, h=y1 - y0 + 1)

    band(800, 153, 609, 472, 0x454545)
    for i in range(quest_rewards + 6):
        top = 153 + 96 * i - offset
        reward = i < quest_rewards
        band(800, top, top + 2, 472, 0x000000)
        band(1100, top + 3, top + 95, 50, QUEST_REWARD_BLUE if reward else 0x454545)
        band(1160, top + 3, top + 95, 40, 0x7A7A7A if reward or not buyable else 0x11A622)


def test_buy_upgrade_scrolls_past_the_event_quest_reward_rows(game, fake) -> None:
    show_tab(fake, "upgrades")
    state = {"offset": 0, "buyable": True}

    def scroll_or_buy(action: tuple) -> None:
        if action == ("button", 5, True):  # wheel down
            state["offset"] += 50
        elif action == ("button", 4, True):  # wheel up
            state["offset"] = max(0, state["offset"] - 50)
        elif action == client_click(1180, 192):
            state["buyable"] = False
        else:
            return
        paint_upgrades(fake, 7, state["offset"], state["buyable"])

    paint_upgrades(fake, 7, 0)
    fake.on_action = scroll_or_buy
    shop = Shop(game)
    shop.loop_amount = 6
    shop.buy_upgrade()

    # 7 rows of 96 px: 13 notches of 50 px leave the first buyable row's separator at 153 + 672 - 650 = 175
    assert state["offset"] == 650
    assert fake.clicks().count((1180, 192)) == 1 and shop.upgrades_bought == 1


def test_buy_upgrade_uses_the_visible_row_when_the_list_cannot_scroll_further(game, fake) -> None:
    show_tab(fake, "upgrades")
    paint_upgrades(fake, 1, 0)  # the wheel changes nothing: the list is already at its end
    fake.on_action = lambda a: paint_upgrades(fake, 1, 0, buyable=False) if a == client_click(1180, 266) else None
    shop = Shop(game)
    shop.loop_amount = 6
    shop.buy_upgrade()

    assert fake.clicks().count((1180, 266)) == 1


def open_shop_late(fake, delay_ms: float) -> None:
    """The shop's corner turns white `delay_ms` after the click on the shop button (seen live: 110-210 ms)."""
    opened_at: list[float] = []
    fake.on_action = lambda a: opened_at.append(fake.t + delay_ms) if a == client_click(1163, 655) else None
    real_grab = fake.grab

    def grab(x: int, y: int, w: int, h: int):
        if opened_at and fake.t >= opened_at[0]:
            fake.paint(807, 140, 0xFFFFFF, h=16)
        return real_grab(x, y, w, h)

    fake.grab = grab


def test_auto_upgrade_waits_for_a_slow_shop(game, fake, event_names, monkeypatch) -> None:
    open_shop_late(fake, 300)
    shop = Shop(game)
    bought = []
    monkeypatch.setattr(shop, "buy_upgrade", lambda: bought.append(True))
    shop.auto_upgrade()

    assert bought and "AutoUpgrade shop not open" not in event_names()


def test_claim_quests_waits_for_a_slow_shop_before_clicking_tabs(game, fake) -> None:
    open_shop_late(fake, 300)
    opening = fake.on_action
    shop_open_at_first_tab = []

    def on_action(action: tuple) -> None:
        opening(action)
        if action == client_click(850, 690):  # armor tab, the first tab click
            shop_open_at_first_tab.append(game.pixel_is(807, 145, 0xFFFFFF))

    fake.on_action = on_action
    Shop(game).claim_quests()

    assert shop_open_at_first_tab == [True]


def test_claim_quests_stops_when_the_shop_never_opens(game, fake, event_names) -> None:
    Shop(game).claim_quests()

    assert fake.clicks() == [(1244, 712), (1163, 655), (1163, 655)]  # the second: a lost click is retried once
    assert "Claim quests: shop not open" in event_names()


def test_scroll_to_top_wheels_until_the_thumb_covers_the_top(game, fake) -> None:
    fake.paint(1254, 167, 0xA0A0A0)  # track: the list isn't at its top (the original expected D6D6D6)
    notches = []

    def thumb_reaches_the_top(action: tuple) -> None:
        if action == ("button", 4, True):
            notches.append(1)
            if len(notches) == 45:
                fake.paint(1254, 167, 0xB7B7B7)  # thumb

    fake.on_action = thumb_reaches_the_top
    scroll_to_top(game, 1254, 167, "test")

    assert len(notches) == 60  # three rounds of 20: a long list needs more than one


def test_buy_equipment_does_not_click_max_while_the_upgrades_tab_shows(game, fake, event_names) -> None:
    show_tab(fake, "upgrades")  # the click on the armor tab hasn't taken effect
    shop = Shop(game)
    shop.loop_amount = 6
    shop.buy_equipment()

    assert (1180, 636) not in fake.clicks()  # on the Upgrades tab that is "Buy all available"
    assert "Shop tab not shown" in event_names()


def test_buy_upgrade_does_not_click_while_another_tab_shows(game, fake) -> None:
    show_tab(fake, "armor")
    fake.paint(1180, 180, 0x11A622)
    shop = Shop(game)
    shop.loop_amount = 6
    shop.buy_upgrade()

    assert (1180, 170) not in fake.clicks()


def test_claim_quests_never_clicks_green_on_a_buying_tab(game, fake, event_names) -> None:
    fake.paint(807, 145, 0xFFFFFF)  # the shop is open...
    show_tab(fake, "upgrades")      # ...but still on Upgrades: its green buttons buy things
    fake.paint(1160, 300, 0x11A622)
    Shop(game).claim_quests()

    assert (1160, 300) not in fake.clicks()
    assert "Shop tab not shown" in event_names()


def test_buy_upgrade_skips_excluded_rows_in_any_order(game, fake) -> None:
    show_tab(fake, "upgrades")
    buying_removes_rows(fake, ["svm", "vm", "buy", "red"])  # the original checks the VM colour first
    shop = Shop(game)
    shop.loop_amount = 6
    shop.buy_upgrade()

    assert fake.clicks().count((1180, 362)) == 1
    assert (1180, 170) not in fake.clicks() and (1180, 266) not in fake.clicks()


def test_selected_tab_shades_measured_live_are_recognised(game, fake) -> None:
    shop = Shop(game)
    fake.paint(1180, 636, 0xFFFFFF)  # Equipment's "Max" button
    for shade, expected in ((0x5A251A, True), (0x5E261B, True), (0x62271C, True), (0x6A281C, False), (0x8E3625, False)):
        fake.paint(820, 700, shade)
        assert shop.tab_shown("armor") is expected, hex(shade)


def test_buy_upgrade_runs_one_equipment_round_even_when_no_upgrade_is_affordable(game, fake) -> None:
    show_tab(fake, "upgrades")  # no green upgrade: right after an ascension only equipment is affordable

    def switch_to_armor(action: tuple) -> None:
        if action == client_click(850, 690):
            fake.paint(897, 700, 0x883424)  # upgrades tab no longer selected
            show_tab(fake, "armor")

    fake.on_action = switch_to_armor
    Shop(game).buy_upgrade()

    assert (1180, 636) in fake.clicks()  # the equipment round ran ("max" buy amount)


def ignore_first_click_at(fake, x: int, y: int, then) -> None:
    """The first click at AutoIt (x, y) doesn't reach the game (seen live on 2026-10-22); `then` runs on the next."""
    seen = []

    def on_action(action: tuple) -> None:
        if action == client_click(x, y):
            seen.append(1)
            if len(seen) == 2:
                then()

    fake.on_action = on_action


def test_auto_upgrade_clicks_the_shop_button_again_when_a_click_is_lost(game, fake, event_names,
                                                                        monkeypatch) -> None:
    ignore_first_click_at(fake, 1163, 655, lambda: fake.paint(807, 145, 0xFFFFFF))
    shop = Shop(game)
    bought = []
    monkeypatch.setattr(shop, "buy_upgrade", lambda: bought.append(True))
    shop.auto_upgrade()

    assert bought and fake.clicks().count((1163, 655)) == 2
    assert "Shop click retried" in event_names()


def test_buy_upgrade_clicks_the_tab_again_when_a_click_is_lost(game, fake, event_names) -> None:
    ignore_first_click_at(fake, 927, 683, lambda: show_tab(fake, "upgrades"))
    shop = Shop(game)
    shop.loop_amount = 6
    shop.buy_upgrade()

    assert fake.clicks().count((927, 683)) == 2
    assert "Shop click retried" in event_names() and "Shop tab not shown" not in event_names()


def test_claim_quests_stops_scrolling_up_while_the_list_bounces_at_the_top(game, fake) -> None:
    fake.paint(807, 145, 0xFFFFFF)  # shop open, Quests tab showing (the blank fake has no buying tab)
    fake.paint(1254, 160, 0xB7B7B7)  # thumb at the top of the track...
    fake.paint(1254, 267, 0xA0A0A0)  # ...but shrunk by the elastic overscroll, so 267 shows the track
    notches_up = []
    fake.on_action = lambda a: notches_up.append(1) if a == ("button", 4, True) else None
    Shop(game).claim_quests()

    assert len(notches_up) == 20  # one round; the original's check at y = 267 kept wheeling (blank panel)


def paint_box(fake) -> None:
    """A floating silver Random Box over the player (its slate frame, 5F6D95)."""
    fake.paint(140, 310, 0x5F6D95, w=20, h=10)


def test_buy_upgrade_stops_for_a_floating_box(game, fake) -> None:
    show_tab(fake, "upgrades")
    buying_removes_rows(fake, ["buy", "buy", "buy", "red"])
    removing = fake.on_action

    def box_after_first_buy(action: tuple) -> None:
        removing(action)
        if action == client_click(1180, 170):
            paint_box(fake)

    fake.on_action = box_after_first_buy
    shop = Shop(game)
    shop.loop_amount = 6

    with pytest.raises(BoxOnScreen):
        shop.buy_upgrade()
    assert fake.clicks().count((1180, 170)) == 1  # it stopped buying after the box appeared


def test_auto_upgrade_closes_the_shop_and_reports_a_box(game, fake, event_names, monkeypatch) -> None:
    fake.paint(807, 145, 0xFFFFFF)  # the shop opens
    shop = Shop(game)

    def buy_until_a_box() -> None:
        raise BoxOnScreen

    monkeypatch.setattr(shop, "buy_upgrade", buy_until_a_box)

    assert shop.auto_upgrade() is False
    assert fake.clicks()[-1] == (1222, 677)  # closed the shop so the player can jump
    assert "Shopping stopped for a Random Box" in event_names()


def test_buy_equipment_stops_for_a_floating_box(game, fake) -> None:
    show_tab(fake, "upgrades")

    def switch_to_armor(action: tuple) -> None:
        if action == client_click(850, 690):
            fake.paint(897, 700, 0x883424)
            show_tab(fake, "armor")
            paint_box(fake)

    fake.on_action = switch_to_armor
    with pytest.raises(BoxOnScreen):
        Shop(game).buy_equipment()

    assert (1180, 636) not in fake.clicks()  # no "Max" and no equipment bought once the box showed


def test_buy_upgrade_checks_the_whole_row_it_clicks(game, fake) -> None:
    """The list scrolled by one notch: the row under the click point (y = 170) is cut off at the
    list's top, and its Vertical Magnet icon is above the original's check box (y 170-242)."""
    show_tab(fake, "upgrades")
    buying_removes_rows(fake, ["vm", "buy", "red"], first_separator=103)  # separators at 103 (hidden), 199, 295
    paint_rows(fake, ["vm", "buy", "red"], first_separator=103)
    fake.paint(885, 155, 0xF4B41B, w=20, h=6)  # the visible tail of the magnet icon, at the list's top
    shop = Shop(game)
    shop.loop_amount = 6
    shop.buy_upgrade()

    assert (1180, 170) not in fake.clicks()  # never click a row it can't see whole
    assert fake.clicks().count((1180, 266)) == 1  # the next, fully visible row


def test_buy_upgrade_waits_for_the_list_to_update_after_a_click(game, fake) -> None:
    show_tab(fake, "upgrades")
    rows = ["buy", "vm", "red"]
    paint_rows(fake, rows)
    pending: list[float] = []
    fake.on_action = lambda a: pending.append(fake.t + 300) if a == client_click(1180, 170) else None
    real_grab = fake.grab

    def grab(x: int, y: int, w: int, h: int):
        if pending and fake.t >= pending[0]:  # the game removes the bought row 300 ms later
            pending.clear()
            del rows[0]
            paint_rows(fake, rows)
        return real_grab(x, y, w, h)

    fake.grab = grab
    shop = Shop(game)
    shop.loop_amount = 6
    shop.buy_upgrade()

    assert fake.clicks().count((1180, 170)) == 1  # not clicked again before the list moved up


def test_row_around_rejects_a_click_point_outside_the_row_it_found(game, fake) -> None:
    show_tab(fake, "upgrades")
    paint_rows(fake, ["buy"])  # one row (156-248) and its closing separator (249-251)...
    fake.paint(800, 249, 0x454545, w=472, h=3)  # ...here hidden, as seen at the end of a short list

    assert Shop(game).row_around(170) == (156, 248)
    assert Shop(game).row_around(266) is None  # the nearest separator above belongs to another row

from idle_runner.tree import ORDER, Tree
from tests.fakes import OFFSET


class FakeTree:
    """The ascension panel and its tree tab as measured on 2026-10-26, in AutoIt coordinates.

    A node click opens a modal: green Buy (468, 571) for a node whose prerequisites are met, red with the
    wide "Can't buy yet" text (white at 580, 582) for a locked one, red with "Close" for a bought one.
    Buy unlocks the node and closes the modal. For nodes in `poor` (not enough SP) it opens the offer to pay
    the difference with jewels instead (live, 2026-10-26): an unticked "I understand" box (white at 583, 521),
    the jewel button (094309 at 468, 571) and Close (758, 582). The modal dims the panel (its X tab at
    538, 681 turns 150202), and the dimming fades out for FADE_MS after the modal closes: clicks meanwhile
    are lost (live, 2026-10-26: the check after Village Key's Buy, 222 ms later).

    Hovering a node shows its tooltip: a 262626 box from x + 43, centred on the pointer, with "Cost: N" in
    11AA23 when the SP is enough and AD1111 when it isn't, next to the SP icon (6A31CA); a bought node's
    says "Unlocked", also 11AA23 (measured 2026-10-25). `tooltips=False` hides them; `lying_tooltips`
    shows green for every node.
    """

    FADE_MS = 300

    def __init__(self, fake, bought=(), locked=(), poor=(), tooltips: bool = True,
                 lying_tooltips: bool = False) -> None:
        self.fake = fake
        self.bought, self.locked, self.poor = set(bought), set(locked), set(poor)
        self.tooltips, self.lying_tooltips = tooltips, lying_tooltips
        self.modal_for: str | None = None
        self.jewel_offer = False
        self.box_ticked = False
        self.tooltip_at: tuple[int, int] | None = None
        self.panel_open = False
        self.fade_until = -1.0
        fake.on_action = self.act
        grab = fake.grab

        def grab_after_fade(x: int, y: int, w: int, h: int):
            if self.panel_open and self.modal_for is None and fake.t >= self.fade_until:
                fake.paint(538, 681, 0xAD1111)
            return grab(x, y, w, h)

        fake.grab = grab_after_fade

    def act(self, action: tuple) -> None:
        if action[0] == "move":
            self.hover(action[1] + OFFSET[0], action[2] + OFFSET[1])
        if action[0] != "click" or self.fake.t < self.fade_until:
            return
        x, y = action[1] + OFFSET[0], action[2] + OFFSET[1]
        if (x, y) == (583, 521):
            self.box_ticked = True
        if (x, y) == (95, 90):  # the panel opens on its Ascension tab
            self.panel_open = True
            self.fake.paint(538, 681, 0xAD1111)
            self.fake.paint(260, 480, 0x58188D)
        elif (x, y) == (205, 696):
            self.fake.paint(158, 676, 0x5E261B)  # tree tab selected
        elif (x, y) == (570, 694):
            self.panel_open = False
            self.fake.frame[:] = 0  # panel closed
        elif self.modal_for is None:
            name = next((n for n, point in ORDER if point == (x, y)), None)
            if name:
                self.show(name)
        elif (x, y) == (534, 582) and not self.jewel_offer:  # Buy
            if self.modal_for in self.poor:
                self.jewel_offer = True
                self.fake.paint(468, 571, 0x094309)
                self.fake.paint(583, 521, 0xFFFFFF)
            else:
                self.bought.add(self.modal_for)
                self.hide()
        elif (x, y) in ((648, 582), (758, 582)):  # a red modal's wide button / Close
            self.hide()

    def show(self, name: str) -> None:
        self.modal_for = name
        self.fake.paint(538, 681, 0x150202)
        if name in self.bought or name in self.locked:
            self.fake.paint(468, 571, 0xAF0000)
            if name in self.locked:
                self.fake.paint(580, 582, 0xFFFFFF)
        else:
            self.fake.paint(468, 571, 0x00A400)

    def hover(self, x: int, y: int) -> None:
        if self.tooltip_at:  # the old tooltip goes away
            tx, ty = self.tooltip_at
            self.fake.paint(tx + 43, ty - 30, 0, w=200, h=61)
            self.tooltip_at = None
        name = next((n for n, point in ORDER if point == (x, y)), None)
        if name is None or not self.tooltips or self.modal_for:
            return
        self.tooltip_at = (x, y)
        self.fake.paint(x + 43, y - 30, 0x262626, w=200, h=61)
        if name not in self.bought:
            poor = name in self.poor and not self.lying_tooltips
            self.fake.paint(x + 80, y + 15, 0xAD1111 if poor else 0x11AA23, w=8, h=8)  # "Cost: N"...
            self.fake.paint(x + 95, y + 15, 0x6A31CA, w=8, h=8)  # ...and the SP icon
        else:
            self.fake.paint(x + 80, y + 15, 0x11AA23, w=30, h=8)  # "Unlocked": green too, no SP icon

    def hide(self) -> None:
        self.modal_for = None
        self.jewel_offer = False
        self.fake.paint(583, 521, 0)
        self.fade_until = self.fake.t + self.FADE_MS
        self.fake.paint(538, 681, 0x3C0606)
        self.fake.paint(468, 571, 0)
        self.fake.paint(580, 582, 0)


def nodes_clicked(fake) -> list[str]:
    names = {point: name for name, point in ORDER}
    return [names[c] for c in fake.clicks() if c in names]


def test_buys_in_order_skips_bought_nodes_and_stops_at_a_locked_one(game, fake, events) -> None:
    tree = FakeTree(fake, bought={"Village Key"}, locked={"Blessing of Cronus"})
    Tree(game).buy()

    assert tree.bought == {"Village Key", "Idle Earrings I", "Idle Earrings II"}
    assert [r["node"] for r in events() if r["event"] == "Tree node bought"] == ["Idle Earrings I", "Idle Earrings II"]
    assert "Portals" not in nodes_clicked(fake)
    assert fake.clicks()[-1] == (570, 694)  # the panel is closed again


def test_zooms_all_the_way_out_before_clicking_a_node(game, fake) -> None:
    FakeTree(fake, locked={"Village Key"})
    Tree(game).buy()

    wheel_downs = [i for i, a in enumerate(fake.actions) if a == ("button", 5, True)]
    first_node = next(i for i, a in enumerate(fake.actions) if a == ("click", 118 - 8, 213 - 31))
    assert len(wheel_downs) == 20 and wheel_downs[-1] < first_node


def test_never_opens_a_node_whose_tooltip_shows_the_cost_in_red(game, fake, events) -> None:
    # Buy without enough SP offers to pay the difference with jewels, bought with real money (2026-10-26).
    tree = FakeTree(fake, poor={"Village Key"})
    Tree(game).buy()

    assert (534, 582) not in fake.clicks()
    assert nodes_clicked(fake) == []
    assert [r["reason"] for r in events() if r["event"] == "Tree stopped"] == ["not enough SP"]
    assert not tree.box_ticked


def test_never_clicks_buy_without_seeing_the_cost_in_green(game, fake, events) -> None:
    tree = FakeTree(fake, tooltips=False)
    Tree(game).buy()

    assert (534, 582) not in fake.clicks()
    assert (758, 582) in fake.clicks()  # the modal's Close
    assert tree.bought == set()
    assert [r["reason"] for r in events() if r["event"] == "Tree stopped"] == ["cost not read"]


def test_closes_a_jewel_offer_at_once_and_never_ticks_its_box(game, fake, event_names) -> None:
    tree = FakeTree(fake, poor={"Village Key"}, lying_tooltips=True)
    Tree(game).buy()

    assert "Tree jewel offer closed" in event_names()
    assert fake.clicks().count((534, 582)) == 1  # Buy, once
    assert fake.clicks()[fake.clicks().index((534, 582)) + 1] == (758, 582)  # then straight to Close
    assert not tree.box_ticked and tree.bought == set()


def test_a_bought_node_is_recognised_from_its_tooltip_without_opening_it(game, fake) -> None:
    # After a restart the bot checked every bought node by hovering 1.5 s and opening it (2026-10-26).
    FakeTree(fake, bought={"Village Key", "Idle Earrings I"}, locked={"Idle Earrings II"})
    start = fake.t
    Tree(game).buy()

    assert nodes_clicked(fake) == ["Idle Earrings II"]
    assert fake.t - start < 5_000


def test_bought_nodes_are_not_clicked_again_in_the_next_run(game, fake) -> None:
    FakeTree(fake, bought={"Village Key"}, locked={"Idle Earrings I"})
    tree = Tree(game)
    tree.buy()
    fake.actions.clear()
    tree.buy()

    assert nodes_clicked(fake) == ["Idle Earrings I"]


def test_nothing_is_clicked_in_the_tree_when_its_tab_does_not_show(game, fake, event_names) -> None:
    tree = FakeTree(fake)
    fake.on_action = lambda a: None if a == ("click", 205 - 8, 696 - 31) else tree.act(a)
    Tree(game).buy()

    assert nodes_clicked(fake) == []
    assert "Tree not shown" in event_names()
    assert fake.clicks()[-1] == (570, 694)

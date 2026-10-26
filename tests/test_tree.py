from idle_runner.tree import ORDER, Tree
from tests.fakes import OFFSET


class FakeTree:
    """The ascension panel and its tree tab as measured on 2026-10-26, in AutoIt coordinates.

    A node click opens a modal: green Buy (468, 571) for a node whose prerequisites are met, red with the
    wide "Can't buy yet" text (white at 580, 582) for a locked one, red with "Close" for a bought one.
    Buy unlocks the node and closes the modal, except for nodes in `poor` (not enough SP).
    """

    def __init__(self, fake, bought=(), locked=(), poor=()) -> None:
        self.fake = fake
        self.bought, self.locked, self.poor = set(bought), set(locked), set(poor)
        self.modal_for: str | None = None
        fake.on_action = self.act

    def act(self, action: tuple) -> None:
        if action[0] != "click":
            return
        x, y = action[1] + OFFSET[0], action[2] + OFFSET[1]
        if (x, y) == (95, 90):  # the panel opens on its Ascension tab
            self.fake.paint(538, 681, 0xAD1111)
            self.fake.paint(260, 480, 0x58188D)
        elif (x, y) == (205, 696):
            self.fake.paint(158, 676, 0x5E261B)  # tree tab selected
        elif (x, y) == (570, 694):
            self.fake.frame[:] = 0  # panel closed
        elif self.modal_for is None:
            name = next((n for n, point in ORDER if point == (x, y)), None)
            if name:
                self.show(name)
        elif (x, y) == (534, 582):  # Buy
            if self.modal_for not in self.poor:
                self.bought.add(self.modal_for)
                self.hide()
        elif (x, y) in ((648, 582), (758, 582)):  # a red modal's wide button / Close
            self.hide()

    def show(self, name: str) -> None:
        self.modal_for = name
        if name in self.bought or name in self.locked:
            self.fake.paint(468, 571, 0xAF0000)
            if name in self.locked:
                self.fake.paint(580, 582, 0xFFFFFF)
        else:
            self.fake.paint(468, 571, 0x00A400)

    def hide(self) -> None:
        self.modal_for = None
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


def test_stops_when_buy_has_no_effect(game, fake, event_names) -> None:
    tree = FakeTree(fake, poor={"Village Key"})  # not enough SP
    Tree(game).buy()

    assert tree.bought == set()
    assert "Tree node not bought" in event_names()
    assert fake.clicks().count((534, 582)) == 1  # Buy, once
    assert (758, 582) in fake.clicks()  # then Close
    assert nodes_clicked(fake) == ["Village Key"]


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

"""Buy Ascension Tree nodes in the user's order. Not in the original (user's request, 2026-10-26).

Measured 2026-10-26 (docs/next-steps.md, "Tree session"): the tree keeps its last pan and zoom, but at
its minimum zoom every node is always at the same place, so the routine zooms all the way out first.
Clicking a node ("Buy on Click" off) opens a modal whose pixel at (468, 571) tells its state: green = Buy
(the prerequisites are met, not necessarily the SP), red = one wide button, "Can't buy yet" (a
prerequisite is missing) or "Close" (bought); the wider text tells them apart.
"""
from idle_runner.actions import TAB_SELECTED, open_ascension_tab
from idle_runner.game import Game
from idle_runner.log import event

# The user's order (2026-10-26): the wiki's Ultra Ascension guide (the way to Blessing of Cronus and souls
# first, CpS later) plus Portals and Portal Traveler, needed for jellies. A node's prerequisites come
# before it: the routine stops at the first node it can't buy. Points are node centres at minimum zoom.
ORDER: list[tuple[str, tuple[int, int]]] = [
    ("Village Key", (118, 213)),
    ("Idle Earrings I", (148, 273)),
    ("Idle Earrings II", (148, 303)),
    ("Blessing of Cronus", (118, 303)),
    ("Portals", (248, 153)),
    ("Green Ore", (308, 248)),
    ("Pink Ore", (338, 248)),
    ("Soul Gem", (368, 248)),
    ("Portal Traveler", (278, 153)),
    ("Legendary Belt", (248, 333)),
    ("Sacred Book of Projectiles", (308, 333)),  # the Bow
    ("Dangerous While Alone", (118, 243)),
    ("Orange Ore", (268, 228)),
    ("Yellow Ore", (348, 228)),
    ("Money Laundering", (178, 153)),
]
MODAL_STATE = (468, 571)
BUY_GREEN = 0x00A400
MODAL_RED = 0xAF0000


class Tree:
    def __init__(self, game: Game) -> None:
        self.game = game
        # Nodes seen bought during this run of the bot, so they aren't clicked again. An Ultra Ascension by
        # hand while the bot runs makes this stale: restart the bot after one.
        self.bought: set[str] = set()

    def buy(self) -> None:
        g = self.game
        if self.open_tree():
            for name, point in ORDER:
                if name not in self.bought and not self.buy_node(name, point):
                    break
        g.click(570, 694)  # close the panel (its X tab, as CollectMinion does)

    def open_tree(self) -> bool:
        g = self.game
        if open_ascension_tab(g):
            g.click(205, 696)  # tree tab
            deadline = g.now() + 2000
            while g.now() <= deadline:
                if g.pixel_search(158, 676, 158, 676, TAB_SELECTED, variation=6):
                    g.move(328, 411)  # over the tree
                    g.wheel(up=False, notches=20)  # minimum zoom: 10 notches were already enough
                    g.sleep(600)  # measured: settled 0.6 s after the wheel
                    return True
                g.sleep(10)
        event("Tree not shown")
        g.save_frame("tree-not-shown")
        return False

    def buy_node(self, name: str, point: tuple[int, int]) -> bool:
        """Buy one node if it isn't bought yet. False when the routine must stop here."""
        g = self.game
        state = self.open_modal(point)
        if state == "bought":
            self.bought.add(name)
            return self.close_modal(648, 582)  # its wide "Close" button
        if state != "buy":
            event("Tree stopped", node=name, reason=state or "no modal")
            g.save_frame("tree-stopped")
            if state:
                self.close_modal(648, 582)  # "Can't buy yet"
            return False
        g.click(534, 582)  # Buy
        if self.wait_modal_gone() and self.open_modal(point) == "bought":  # check it took
            self.bought.add(name)
            event("Tree node bought", node=name)
            return self.close_modal(648, 582)
        event("Tree node not bought", node=name)  # not enough SP, most likely
        g.save_frame("tree-not-bought")
        state = self.modal()
        if state == "buy":
            self.close_modal(758, 582)  # Close
        elif state:
            self.close_modal(648, 582)
        return False

    def modal(self) -> str | None:
        """"buy", "locked", "bought", or None when no modal shows."""
        g = self.game
        if g.pixel_is(*MODAL_STATE, BUY_GREEN):
            return "buy"
        if g.pixel_is(*MODAL_STATE, MODAL_RED):
            text = g.grab(564, 576, 608, 588)  # "Can't buy yet" is wider than "Close"
            return "locked" if bool((text > 200).all(axis=2).any()) else "bought"
        return None

    def open_modal(self, point: tuple[int, int]) -> str | None:
        """Click a node and wait up to 2 s for its modal; two equal reads 100 ms apart (it opens animated)."""
        g = self.game
        g.click(*point)
        deadline = g.now() + 2000
        while g.now() <= deadline:
            state = self.modal()
            if state:
                g.sleep(100)
                if self.modal() == state:
                    return state
            g.sleep(10)
        return None

    def wait_modal_gone(self) -> bool:
        g = self.game
        deadline = g.now() + 2000
        while self.modal() and g.now() <= deadline:
            g.sleep(10)
        g.sleep(200)  # let it finish closing: a click during a panel's close can be lost (2026-10-25)
        return self.modal() is None

    def close_modal(self, x: int, y: int) -> bool:
        self.game.click(x, y)
        return self.wait_modal_gone()

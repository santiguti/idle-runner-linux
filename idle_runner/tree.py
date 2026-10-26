"""Buy Ascension Tree nodes in the user's order. Not in the original (user's request, 2026-10-26).

Measured 2026-10-26 (docs/next-steps.md, "Tree session"): the tree keeps its last pan and zoom, but at
its minimum zoom every node is always at the same place, so the routine zooms all the way out first.
Clicking a node ("Buy on Click" off) opens a modal whose pixel at (468, 571) tells its state: green = Buy
(the prerequisites are met, not necessarily the SP), red = one wide button, "Can't buy yet" (a
prerequisite is missing) or "Close" (bought); the wider text tells them apart.

**Buy without enough SP offers to pay the difference with jewels**, bought with real money (2026-10-26).
So Buy is clicked only after the node's tooltip showed its cost in green (enough SP), and that offer is
closed at once if it shows anyway. Its jewel button needs its "I understand" box ticked first; nothing in
the bot clicks that box.
"""
import numpy as np

from idle_runner.actions import PANEL_X_RED, TAB_SELECTED, open_ascension_tab
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
JEWEL_BUTTON = 0x094309  # at MODAL_STATE in the jewel offer; its box at (583, 521) is white (2026-10-26)
# A node's tooltip (measured 2026-10-25/26 on 34 tooltips, all read right): a 262626 box from x + 43,
# centred on the pointer, up to ±122 px tall. Its cost line ends with the SP icon (6A31CA) and the digits
# are 11AA23 with enough SP, AD1111 without. A bought node's says "Unlocked", 11AA23 on a row without it.
TOOLTIP_BG = (0x26, 0x26, 0x26)
SP_ICON = (0x6A, 0x31, 0xCA)
COST_GREEN = (0x11, 0xAA, 0x23)
COST_RED = (0xAD, 0x11, 0x11)


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
        tooltip = self.tooltip(point)
        if tooltip == "unlocked":
            self.bought.add(name)
            return True
        if tooltip == "not enough":
            event("Tree stopped", node=name, reason="not enough SP")
            return False
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
        if tooltip != "enough":  # the tooltip's cost wasn't read: never Buy blind
            event("Tree stopped", node=name, reason="cost not read")
            g.save_frame("tree-cost-not-read")
            self.close_modal(758, 582)  # Close
            return False
        g.click(534, 582)  # Buy
        if self.jewel_offer_closed(name):
            return False
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

    def tooltip(self, point: tuple[int, int]) -> str | None:
        """Hover the node and read its tooltip: "enough" (cost in green), "not enough" (in red), "unlocked"
        (bought), or None if none of them shows within 1.5 s. Two equal reads 100 ms apart (it fades in)."""
        g = self.game
        x, y = point
        g.move(x, y)
        g.sleep(200)  # the previous node's tooltip goes; this one needs ~0.5 s of hovering
        deadline = g.now() + 1500
        while g.now() <= deadline:
            state = self.read_tooltip(x, y)
            if state:
                g.sleep(100)
                if self.read_tooltip(x, y) == state:
                    return state
            g.sleep(50)
        return None

    def read_tooltip(self, x: int, y: int) -> str | None:
        # x 647, y 31 and 750: the panel's right edge and the client area's top and bottom
        region = self.game.grab(x + 43, max(y - 170, 31), min(x + 343, 647), min(y + 170, 750))
        background = (region == TOOLTIP_BG).all(axis=2)
        if not background.any():
            return None
        ys, xs = np.nonzero(background)
        box = region[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        icon_rows = (box == SP_ICON).all(axis=2).any(axis=1)
        green_rows = (box == COST_GREEN).all(axis=2).any(axis=1)
        if (green_rows & icon_rows).any():
            return "enough"
        if ((box == COST_RED).all(axis=2).any(axis=1) & icon_rows).any():
            return "not enough"
        if (green_rows & ~icon_rows).any():
            return "unlocked"
        return None

    def jewel_offer_closed(self, name: str) -> bool:
        """After Buy: if the jewel offer shows within 1 s, click its Close (never its box or its jewel
        button) and return True."""
        g = self.game
        deadline = g.now() + 1000
        while g.now() <= deadline:
            if g.pixel_is(*MODAL_STATE, JEWEL_BUTTON) or g.pixel_is(583, 521, 0xFFFFFF):
                g.click(758, 582)  # Close
                event("Tree jewel offer closed", node=name)
                g.save_frame("tree-jewel-offer")
                self.wait_modal_gone()
                return True
            if self.modal() is None:
                return False
            g.sleep(10)
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
        """Wait up to 2 s until the modal is gone and the panel's dimming has faded out: its X tab is
        AD1111 again (150202 under the modal, 3C0606 while it fades). A click meanwhile is lost: live on
        2026-10-26, the check 222 ms after Village Key's Buy."""
        g = self.game
        deadline = g.now() + 2000
        while g.now() <= deadline:
            if self.modal() is None and g.pixel_is(538, 681, PANEL_X_RED):
                return True
            g.sleep(10)
        return False

    def close_modal(self, x: int, y: int) -> bool:
        self.game.click(x, y)
        return self.wait_modal_gone()

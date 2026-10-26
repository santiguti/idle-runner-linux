"""Buy Ascension Tree nodes in the user's order. Not in the original (user's request, 2026-10-26).

Measured 2026-10-26 (docs/next-steps.md, "Tree session"): the tree keeps its last pan and zoom, but at
its minimum zoom every node is always at the same place, so the routine zooms all the way out first.
Clicking a node ("Buy on Click" off) opens a modal whose pixel at (468, 571) tells its state: green = Buy
(the prerequisites are met, not necessarily the SP), red = one wide button, "Can't buy yet" (a
prerequisite is missing) or "Close" (bought); the wider text tells them apart.

The order is the wiki's, which doesn't follow the tree's links: a node whose prerequisite comes later is
skipped until a purchase may have unlocked it. A node that can be bought but costs more SP than there is
stops the routine, so SP is saved in the wiki's order.

**Buy without enough SP offers to pay the difference with jewels**, bought with real money (2026-10-26).
So Buy is clicked only after the node's tooltip showed its cost in green (enough SP), and that offer is
closed at once if it shows anyway. Its jewel button needs its "I understand" box ticked first; nothing in
the bot clicks that box.
"""
import numpy as np

from idle_runner.actions import PANEL_X_RED, TAB_SELECTED, open_ascension_tab
from idle_runner.game import Game
from idle_runner.log import event

# The wiki's order (user's request, 2026-10-26: "respetemos lo que diga la wiki"), as surveyed in the game
# on 2026-10-26: every point was clicked and its modal's name read. Points are node centres at minimum zoom,
# in AutoIt coordinates; costs as the game shows them.
ORDER: list[tuple[str, tuple[int, int]]] = [
    # 1. What's left of the wiki's Ultra Ascension guide: Portal Traveler (jellies), the way to the Bow,
    #    then Stability and Triple Shot (Ancient Quests and Hot Desert come first there, but sit under the
    #    header at minimum zoom: not located yet).
    ('Portal Traveler', (278, 152)),  # 200
    ('Legendary Belt', (248, 333)),  # 350
    ('Sacred Book of Projectiles', (308, 333)),  # 1,000
    ('Stability', (337, 333)),  # 3,000
    ('Triple Shot', (337, 362)),  # 4,000
    # 2. The cheap nodes the tier list's "First Ultra Ascension" section lists right after Blessing of Cronus.
    ('Orange Ore', (267, 227)),  # 5
    ('Yellow Ore', (348, 227)),  # 5
    ('Dangerous While Alone', (118, 242)),  # 35
    # 3. The tier list, tiers 1-10 in the wiki's order (Bullet Time and Map: not located yet).
    ("Doesn't Matter to Me", (307, 303)),  # 150
    ('Soul Slash', (247, 363)),  # 450
    ('Axe Edge', (247, 393)),  # 600
    ('Minions', (250, 423)),  # 1,200
    ('Money Laundering', (178, 152)),  # 25
    ('Purple Ore', (278, 249)),  # 40
    ('Cheap Darkness', (308, 217)),  # 30
    ('Dagger Edge', (178, 303)),  # 75
    ('Stocks Buyer', (207, 151)),  # 50
    ('Every Day Counts', (308, 274)),  # 50
    ('Idle Earrings III', (147, 332)),  # 100
    ('Idle Earrings IV', (178, 333)),  # 250
    ('Idle Earrings of Death', (207, 333)),  # 250
    ('Bring Hell', (338, 303)),  # 600
    ('Mystic Valley', (277, 363)),  # 1,200
    ('Enchanted Arrows', (308, 363)),  # 600
    ('Dark Wand', (248, 452)),  # 2,000
    ('Dark Wizard', (276, 454)),  # 2,500
    ('Ethereal Wand', (219, 452)),  # 500
    ('Dual Randomness', (218, 393)),  # 300
    ('Coins In The Box', (217, 422)),  # 350
    ('Royalties', (217, 362)),  # 400
    ('Lunar Idle Earrings', (189, 366)),  # 950
    ('Solar Idle Earrings', (187, 392)),  # 1,000
    ('Book of Efficiency I', (119, 441)),  # 500
    ('Silver Money Amulet', (278, 393)),  # 1,600
    ('Golden Money Amulet', (308, 393)),  # 2,000
    ('Soul Reaper II', (307, 421)),  # 1,000
    ('Soul Amulet', (338, 393)),  # 3,000
    ('Rock And Stone', (248, 523)),  # 10,000
    ('Embrace The Fear', (337, 421)),  # 6,500
    ('Skeleton', (338, 453)),  # 8,000
    ('Safety First', (148, 363)),  # 8,000
    ('Chest Hunt Saver', (118, 333)),  # 5,000
    ('Sword Edge II', (147, 393)),  # 1,850
    ('Shinies', (118, 393)),  # 500
    ('Golden Invasion', (88, 392)),  # 650
    ('Saved', (368, 322)),  # 2,500
    ('Book of Efficiency II', (120, 473)),  # 5,000
    ('Bonus Stage 2', (367, 485)),  # 5,000
    ('Doomed', (368, 283)),  # 2,500
    ('Permanent Supply Boxes', (188, 422)),  # 4,000
    ('King of The Sea', (367, 207)),  # 6,500
    ('ASHPD', (307, 152)),  # 5,000
    ('Wall Breaker', (276, 421)),  # 3,500
    ('Tornado of Souls', (398, 207)),  # 20,000
    ('Gemstone Rush', (398, 303)),  # 10,000
    ('Bag', (430, 333)),  # 10,000
    ('Terra Idle Earrings', (148, 443)),  # 7,500
    ('Roll The Dice', (398, 173)),  # 16,500
    ('Premium Time', (368, 173)),  # 25,000
    ('Knight Services', (247, 481)),  # 7,500
    ('High Alchemy', (306, 452)),  # 12,000
    ('Blue Sparkle', (398, 248)),  # 6,000
    ('Factory', (367, 392)),  # 140,000
    ('Human After All', (368, 423)),  # 60,000
    ('Protect', (398, 513)),  # 15,000
    ('Oblivion Idle Earrings', (168, 463)),  # 23,000
    ('Boost Blood', (447, 207)),  # 50,000
    ('Augmented Boost Kill', (447, 234)),  # 100,000
    ('Super Chest Souls', (477, 208)),  # 35,000
    ('Soul Silver', (392, 146)),  # 35,000
    ('Muscle Memory', (367, 362)),  # 35,000
    ('Book of Efficiency III', (118, 503)),  # 50,000
    ('Idle Earrings of Unity', (148, 483)),  # 45,000
    ('Mega Horde', (437, 303)),  # 175,000
    ('Blessing of Kratos', (397, 352)),  # 95,000
    ('Divinities', (398, 393)),  # 200,000
    ('Critical Culling', (207, 526)),  # 150,000
    ('Bonus Rewards+', (427, 172)),  # 1,250,000
    ('Mega Chest Souls', (428, 143)),  # 1,500,000
    ('Book of Efficiency IV', (119, 529)),  # 500,000
    # 4. The rest of the "First Ultra Ascension" section, in its order; the Ultra Ascension node last (it
    #    brings the Ultra Ascend button back, which the bot never clicks).
    ('Inner Power', (276, 524)),  # 5,000
    ('3 Rows', (457, 173)),  # 350,000
    ('Critical Training', (178, 493)),  # 350,000
    ('Critical Practice', (178, 553)),  # 350,000
    ('Critical Study', (178, 523)),  # 350,000
    ('Perfect Prestige', (466, 422)),  # 2,500,000
    ('Rage Mode', (210, 564)),  # 30,000,000
    ('Already Enraged', (238, 563)),  # 100
    ('Outrage', (268, 563)),  # 200
    ('Fury', (237, 592)),  # 10
    ("Gala's Bone", (338, 491)),  # 600,000
    ('Climbing Boots', (368, 513)),  # 75,000
    ('Book of Efficiency V', (148, 533)),  # 5,000,000
    ('Giant Horde', (497, 332)),  # 50,000,000
    ('Careful Slayer', (457, 333)),  # 12,500,000
    ('Master Chest Souls', (118, 363)),  # 150 M
    ('Advanced Cooking', (448, 272)),  # 2,000,000
    ('Ramen', (477, 242)),  # 3,500,000
    ('Stew', (477, 302)),  # 4,000,000
    ('Bonus Sphere Control', (367, 542)),  # 5,000,000
    ('Astral Slayer', (507, 271)),  # 500 M
    ('Ultra Ascension', (450, 392)),  # 2,000,000
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
        # Nodes seen locked ("Can't buy yet") since the last purchase: only a purchase unlocks a node.
        self.locked: set[str] = set()

    def buy(self) -> None:
        g = self.game
        if self.open_tree():
            for name, point in ORDER:
                if name not in self.bought | self.locked and not self.buy_node(name, point):
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
        state = self.open_modal(point)
        if state == "bought":
            self.bought.add(name)
            return self.close_modal(648, 582)  # its wide "Close" button
        if state == "locked":  # a prerequisite comes later in the wiki's order: go on
            self.locked.add(name)
            return self.close_modal(648, 582)  # "Can't buy yet"
        if state != "buy":
            event("Tree stopped", node=name, reason="no modal")
            g.save_frame("tree-stopped")
            return False
        if tooltip == "not enough":  # wait for the SP, in the wiki's order
            event("Tree stopped", node=name, reason="not enough SP")
            self.close_modal(758, 582)  # Close
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
            self.locked.clear()  # it may have unlocked nodes earlier in the order
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

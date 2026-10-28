"""Send minions on missions from the ascension panel's Minions tab. Replaces the original's MinionsCollect.

On the current game version (measured 2026-10-28) every minion has its own button: "Send on Mission (-N SP)",
"On a Mission..." or, once the mission is over, a green "Claim". The SP a mission brings is collected by
ascending (wiki). The original's "claim all /
send all" clicks land on the Daily Bonus banner, and its trigger, yellow at (99, 113), is the Ascension
button's glow (it glows while ascending is "Recommended"), not minions coming back.
"""
from idle_runner.actions import TAB_SELECTED, open_ascension_tab
from idle_runner.ascend_bonus import sp_amount
from idle_runner.config import Settings
from idle_runner.game import Game
from idle_runner.log import event

SEND = (0x54, 0x17, 0x87)           # "Send on Mission (-N SP)"
AWAY = (0x97, 0x5D, 0xCA)           # "On a Mission..."
# "Claim" when a mission is over: the shop's Unlock green (Santi, 2026-10-28; no screenshot of it yet).
CLAIM = (0x11, 0xA6, 0x22)
HEADER_DIGITS = (0xA6, 0x75, 0xFE)  # the header's "N available"
BUTTON_X = 438                      # the buttons' left part, clear of their text
LIST_TOP, LIST_BOTTOM = 136, 659    # the list between the header and the tab bar (client y 105-628)
BUTTON_HEIGHT = 120                 # a whole button shows 123 px of its colour (client y 222-344)
MAX_CLICKS = 10
# Mission minutes by cost in SP, which is fixed per minion (wiki, Minions): White Knight, Dark Wizard, Skeleton,
# Goo Mutant, Stone Golem. The Ninja and the Cyclops cost "50 B" and "100 B", which never read.
MISSION_MINUTES = {10: 180, 150: 390, 1_000: 180, 1_500: 270, 3_000: 1_380}
# Divinities that make missions faster. They add up and shorten the mission: with the first two the White
# Knight takes "under 2 hours" (wiki), 3 h x (1 - 0.35).
SPEEDUPS = {"work_benefits": 0.15, "improved_work_conditions": 0.20, "greeks_blessing": 0.25}


def mission_ms(cost: int, settings: Settings) -> float | None:
    """How long the mission that costs `cost` SP takes, or None for a cost the table doesn't have."""
    minutes = MISSION_MINUTES.get(cost)
    if minutes is None:
        return None
    return minutes * 60_000 * (1 - sum(share for name, share in SPEEDUPS.items() if getattr(settings, name)))


def read_available_sp(game: Game) -> int | None:
    """The unspent SP in the panel's header ("21,048 available"), or None."""
    band = game.grab(28, 59, 638, 88)  # client x 20-629, y 28-57
    return sp_amount((band == HEADER_DIGITS).all(axis=2), band)


def read_mission_cost(game: Game, top: int) -> int | None:
    """The cost on the send button whose top edge is at `top`: its third line, "(-10 SP)" in white."""
    line = game.grab(428, top + 79, 618, top + 97)  # client x 420-609
    white = (line == 255).all(axis=2)
    columns = white.any(axis=0)
    x = 0
    while x < len(columns):
        if not columns[x]:
            x += 1
            continue
        start = x
        while x < len(columns) and columns[x]:
            x += 1
        rows = white[:, start:x].any(axis=1).nonzero()[0]
        if rows[-1] - rows[0] <= 1:  # the "-", 1 px tall: the digits follow
            return sp_amount(white[:, x:], line[:, x:])
    return None


def send_buttons(game: Game, color: tuple[int, int, int] = SEND) -> list[int]:
    """The top edges of the send buttons (or of buttons of `color`) wholly inside the list, from the top."""
    column = (game.grab(BUTTON_X, LIST_TOP, BUTTON_X, LIST_BOTTOM)[:, 0] == color).all(axis=1)
    tops, y = [], 0
    while y < len(column):
        if column[y]:
            start = y
            while y < len(column) and column[y]:
                y += 1
            if y - start >= BUTTON_HEIGHT:
                tops.append(LIST_TOP + start)
        y += 1
    return tops


def send_minions(game: Game) -> list[int]:
    """Claim the minions back from their missions, then send every minion whose mission the unspent SP
    covers. Claims cost nothing; each send is checked against the header's SP:
    without enough, the game may offer to pay the rest with jewels (the tree did, 2026-10-26). The list
    moves when a minion leaves (the Daily Bonus banner above it changes), so the buttons are found again
    after each send. Only the buttons on screen are seen: the list holds two whole ones, enough for the
    White Knight and the Dark Wizard (the Daily Bonus isn't taken yet). Returns the costs of the missions sent."""
    sent: list[int] = []
    if not open_ascension_tab(game):
        game.click(570, 694)  # exit
        return sent
    game.click(332, 680)  # minions tab
    # Its shade fades in: 200 ms after the click it still hadn't when the tree had just switched tabs (live,
    # 2026-10-28 02:43), so wait for it as Shop.tab_shown does.
    deadline = game.now() + 2000
    while game.pixel_search(332, 676, 332, 676, TAB_SELECTED, variation=6) is None and game.now() < deadline:
        game.sleep(20)
    if game.pixel_search(332, 676, 332, 676, TAB_SELECTED, variation=6) is None:
        event("Minions tab not shown")
        game.click(570, 694)  # exit
        return sent
    if not any(send_buttons(game, color) for color in (SEND, AWAY, CLAIM)):
        event("Minions buttons unknown")
        game.save_frame("minions-buttons-unknown")
    for _ in range(MAX_CLICKS):
        claims = send_buttons(game, CLAIM)
        if claims:
            game.click(522, claims[0] + 62)  # the button's middle
            deadline = game.now() + 2000
            while len(send_buttons(game, CLAIM)) >= len(claims):
                if game.now() > deadline:
                    event("Minion not claimed")
                    game.save_frame("minion-claim-no-effect")
                    game.click(570, 694)  # exit
                    return sent
                game.sleep(50)
            event("Minion claimed")
            continue
        available = read_available_sp(game)
        if available is None:
            event("Minions SP not readable")
            game.save_frame("minions-sp-unreadable")
            break
        costs = [(top, read_mission_cost(game, top)) for top in send_buttons(game)]
        affordable = [(top, cost) for top, cost in costs if cost is not None and cost <= available]
        if not affordable:
            for top, cost in costs:
                if cost is None:
                    event("Minion not sent", reason="cost not readable")
                    game.save_frame("minion-cost-unreadable")
                else:
                    event("Minion not sent", reason="not enough SP", cost=cost, available=available)
            break
        top, cost = affordable[0]
        game.click(522, top + 62)  # the button's middle
        deadline = game.now() + 2000
        while read_available_sp(game) != available - cost:
            if game.now() > deadline:
                event("Minion not sent", reason="no effect", cost=cost)
                game.save_frame("minion-send-no-effect")
                game.click(570, 694)  # exit
                return sent
            game.sleep(50)
        event("Minion sent", cost=cost)
        sent.append(cost)
    game.click(570, 694)  # exit
    return sent

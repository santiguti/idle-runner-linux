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
from idle_runner.game_settings import _bands
from idle_runner.log import event

SEND = (0x54, 0x17, 0x87)           # "Send on Mission (-N SP)"
AWAY = (0x97, 0x5D, 0xCA)           # "On a Mission..."
# "Claim" when a mission is over: the shop's Unlock green (Santi, 2026-10-28; no screenshot of it yet).
CLAIM = (0x11, 0xA6, 0x22)
HEADER_DIGITS = (0xA6, 0x75, 0xFE)  # the header's "N available"
# The buttons' left margin (client x 402-428): each of their rows has the button's colour somewhere in it, clear of
# the text in English and Spanish ("Realizando una Misión ..." starts at client x 428 and crossed the single
# column at 430 used before; 2026-10-28).
BUTTON_LEFT, BUTTON_RIGHT = 410, 436
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
    """The cost on the send button whose top edge is at `top`: the white line with "(-10 SP)", the button's third
    line in English and its second in Spanish ("Dar Misión (-1,000 SP)", 2026-10-28)."""
    # Client x 415-591: inside the button in both layouts (English 415-613, Spanish 398-597), clear of the reward bar
    # beside it and of the list's scrollbar right of the Spanish one.
    button = game.grab(423, top, 599, top + BUTTON_HEIGHT)
    white = (button == 255).all(axis=2)
    for first, end in _bands(white):
        line, mask = button[first:end], white[first:end]
        columns = mask.any(axis=0)
        x = 0
        while x < len(columns):
            if not columns[x]:
                x += 1
                continue
            start = x
            while x < len(columns) and columns[x]:
                x += 1
            rows = mask[:, start:x].any(axis=1).nonzero()[0]
            if rows[-1] - rows[0] <= 1:  # the "-", 1 px tall: the digits follow
                cost = sp_amount(mask[:, x:], line[:, x:])
                if cost is not None:
                    return cost  # else a 1 px piece of another glyph ("(" has one): the dash may follow
    return None


def send_buttons(game: Game, color: tuple[int, int, int] = SEND) -> list[int]:
    """The top edges of the send buttons (or of buttons of `color`) wholly inside the list, from the top."""
    column = (game.grab(BUTTON_LEFT, LIST_TOP, BUTTON_RIGHT, LIST_BOTTOM) == color).all(axis=2).any(axis=1)
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


def minions_shown(game: Game) -> bool:
    """Wait up to 2 s for the Minions tab: its shade and a button of a known colour. The shade fades in (200 ms
    after the click it still hadn't when the tree had just switched tabs, live 2026-10-28 02:43), and alone it
    misled once: it stayed on Minions over the Ascension tab's list after a lost click (19:25)."""
    deadline = game.now() + 2000
    while game.now() <= deadline:
        if (game.pixel_search(332, 676, 332, 676, TAB_SELECTED, variation=6)
                and any(send_buttons(game, color) for color in (SEND, AWAY, CLAIM))):
            return True
        game.sleep(20)
    return False


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
    for attempt in range(2):
        if attempt:
            event("Shop click retried", target="minions")
        game.click(332, 680)  # minions tab
        if minions_shown(game):
            break
    else:
        if game.pixel_search(332, 676, 332, 676, TAB_SELECTED, variation=6) is None:
            event("Minions tab not shown")
        else:
            event("Minions buttons unknown")
            game.save_frame("minions-buttons-unknown")
        game.click(570, 694)  # exit
        return sent
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

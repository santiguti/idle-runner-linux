"""Check the in-game settings the bot needs, once at start. Not in the original, which only listed them.

The settings are a dialog behind the shop's "⋮" tab (measured 2026-10-28): a list that always opens at its top
and scrolls 50 px per wheel notch. A toggle shows a red cross (F83308) on its left when off and a green tick
(1DD700) on its right when on. Each row is told by its label's white pixels, which also tells that the game is
in English. The bot only reads the list: it ends with "Delete Save" and "Delete Idle Slayer Account" and holds
"Remove Ads" purchases, so the only click inside the dialog is Cancel, and the wheel turns in the empty strip
beside the scrollbar.
"""
import numpy as np

from idle_runner.actions import TAB_SELECTED
from idle_runner.game import Game
from idle_runner.log import event
from idle_runner.shop import Shop

# Each setting the bot needs: its label's right edge (client x) and white pixels, and the state it needs.
SETTINGS: dict[str, tuple[tuple[int, int], bool]] = {
    "Use scientific notation": ((680, 722), False),  # the coin, bonus and SP readers read plain numbers
    "Disable custom cursor": ((680, 713), True),
    "Rounded bulk buy": ((635, 700), True),
    "Hide locked Quest rewards": ((731, 911), True),  # locked event rewards would sit in the Upgrades list
    "Confirm dialogue when activating the Portal": ((846, 1360), False),
}
SETTINGS_LABEL = (89, 558)  # the "Settings" button's label in the "⋮" menu: width and white pixels
OFF, ON = (0xF8, 0x33, 0x08), (0x1D, 0xD7, 0x00)
APPLY_GREEN, CANCEL_RED = 0x00A400, 0xAF0000
SCROLLS = (33, 6)  # notches to the first four settings, then to the portal's (client y 149-484 and 169-432)


def _bands(white: np.ndarray) -> list[tuple[int, int]]:
    """The runs of rows that hold white pixels: (first, end)."""
    rows = white.any(axis=1)
    bands, y = [], 0
    while y < len(rows):
        if rows[y]:
            start = y
            while y < len(rows) and rows[y]:
                y += 1
            bands.append((start, y))
        y += 1
    return bands


def read_toggles(game: Game) -> dict[str, bool]:
    """The settings on screen in the dialog's list, by name: whether each is on."""
    pixels = game.grab(373, 126, 908, 566)  # client x 365-900, y 95-535
    white = (pixels[:, 80:] == 255).all(axis=2)  # the labels, from client x 445
    found: dict[str, bool] = {}
    for start, end in _bands(white):
        band = white[start:end]
        label = (int(np.nonzero(band.any(axis=0))[0].max()) + 445, int(band.sum()))
        for name, (fingerprint, _) in SETTINGS.items():
            if label == fingerprint:
                box = pixels[max(0, start - 8):end + 8, :75]  # the toggle, client x 365-439
                found[name] = int((box == ON).all(axis=2).sum()) > int((box == OFF).all(axis=2).sum())
    return found


def find_settings_button(game: Game) -> tuple[int, int] | None:
    """Where to click the "⋮" menu's Settings button (AutoIt), found by its label; None if it isn't there.
    The menu's left column is searched: an event's card above the buttons comes and goes."""
    white = (game.grab(840, 161, 1024, 656) == 255).all(axis=2)  # client x 832-1016, y 130-625
    for start, end in _bands(white):
        columns = np.nonzero(white[start:end].any(axis=0))[0]
        if (int(columns[-1] - columns[0] + 1), int(white[start:end].sum())) == SETTINGS_LABEL:
            return 840 + int(columns[0] + columns[-1]) // 2, 161 + start - 15
    return None


def _close(game: Game) -> None:
    """Cancel the dialog if it shows (it's modal: the shop's X takes no click under it), then close the shop.
    The dialog fades out after Cancel and an X click then did nothing (live, 2026-10-28): the X is clicked
    again if the shop is still open a second later, never sooner (a click while it closes leaves an empty
    panel that takes every click, see Shop.close_if_open)."""
    if game.pixel_is(791, 631, CANCEL_RED):
        game.click(791, 631)  # Cancel: changes nothing
        deadline = game.now() + 2000
        while game.pixel_is(791, 631, CANCEL_RED) and game.now() < deadline:
            game.sleep(50)
        game.sleep(300)
    for _ in range(2):
        game.click(1244, 712)  # close the shop
        game.sleep(1000)
        if not game.pixel_search(807, 140, 807, 155, 0xFFFFFF):  # the shop's corner, as in Shop.open_shop
            return


def check_game_settings(game: Game, shop: Shop) -> None:
    """Open the settings, read the ones the bot needs, close them with Cancel and log what's wrong."""
    shop.close_if_open()
    if not shop.open_shop():
        event("Game settings not checked", reason="shop not open")
        return
    game.click(1158, 696)  # the "⋮" tab: inside it in both tab bars (see shop.X_TAB_RED)
    button = None
    deadline = game.now() + 2000
    while game.pixel_search(1130, 700, 1130, 700, TAB_SELECTED, variation=6) is None and game.now() < deadline:
        game.sleep(20)  # the selected shade fades in (5A251A-62271C), as in Shop.tab_shown
    if game.pixel_search(1130, 700, 1130, 700, TAB_SELECTED, variation=6):
        game.sleep(200)
        button = find_settings_button(game)
    if button is None:
        event("Game settings not checked", reason="no Settings button")
        game.save_frame("settings-menu-not-shown")
        game.click(1244, 712)  # close the shop
        return
    game.click(*button)
    # The dialog grows from the middle as it opens: Apply reaches (428, 631) last (seen live, 2026-10-28).
    deadline = game.now() + 3000
    while not (game.pixel_is(791, 631, CANCEL_RED) and game.pixel_is(428, 631, APPLY_GREEN)):
        if game.now() > deadline:
            event("Game settings not checked", reason="dialog not shown")
            game.save_frame("settings-dialog-not-shown")
            _close(game)
            return
        game.sleep(50)
    game.sleep(300)
    found: dict[str, bool] = {}
    game.move(916, 331)  # between the list and its scrollbar: no control there
    for notches in SCROLLS:
        game.wheel(up=False, notches=notches)
        game.sleep(1000)
        found |= read_toggles(game)
    if len(found) < len(SETTINGS):
        game.save_frame("settings-not-found")
    _close(game)
    wrong = []
    for name, (_, needed) in SETTINGS.items():
        if name not in found:
            event("Game setting not found", setting=name)
        elif found[name] != needed:
            event("Game setting wrong", setting=name, should_be="on" if needed else "off")
            wrong.append(name)
    event("Game settings checked", wrong=wrong, missing=[name for name in SETTINGS if name not in found])

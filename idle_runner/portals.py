"""CirclePortals from Idle Runner.au3: take the next portal destination whenever the portal is ready."""
from idle_runner.game import STUCK_MS, Game
from idle_runner.log import event
from idle_runner.shop import SCROLLBAR_GRAY, scroll_to_top

PORTAL_COLORS = {
    1: 0x00CBF8,  # hills
    2: 0xBD4348,  # hot desert
    3: 0x009D93,  # jungle
    4: 0x6FF5F8,  # frozen fields
    5: 0xB362C7,  # funky
    6: 0x000173,  # modern city
    7: 0x00F8B5,  # factory
    8: 0xE198BF,  # valley
    9: 0x4F0085,  # castle
}


def portal_ready(game: Game) -> bool:
    """The portal button is visible and shows no countdown."""
    visible = game.pixel_is(1180, 166, 0x830399) or game.pixel_is(1180, 166, 0x290130)
    return visible and game.pixel_search(1154, 144, 1210, 155, 0xFFFFFF, variation=9) is None


def take_portal(game: Game, count: int) -> None:
    color = PORTAL_COLORS[count]
    game.click(1180, 150)  # portal button
    game.sleep(300)
    game.move(867, 300)  # over the destination list's scrollbar
    game.sleep(200)
    scroll_to_top(game, 875, 250, "portals")
    game.sleep(400)
    deadline = game.now() + STUCK_MS
    while True:
        found = game.pixel_search(470, 230, 470, 540, color, variation=10)
        if found is None:
            if not game.pixel_is(875, 536, SCROLLBAR_GRAY):  # bottom of the list: give up
                event("Portal destination not found", count=count)
                game.save_frame("portal-not-found")
                game.click(600, 600)
                break
            game.sleep(100)
            game.move(867, 300)
            game.wheel(up=False, notches=1)
        else:
            game.sleep(300)
            game.wheel(up=False, notches=1)
            game.wheel(up=False, notches=1)
            game.click(found[0] + 300, found[1])  # the destination's travel button
            break
        if game.now() > deadline:
            game.stuck("portals", count=count)
            break
    event("CirclePortals", count=count)
    game.sleep(10_000)

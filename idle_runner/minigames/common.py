"""Shared minigame helpers from Libraries/Common.au3."""
from idle_runner.game import STUCK_MS, Game

# Where the green slider handle can be: (search left, search right, y, drag from x, drag to x).
SLIDER_POSITIONS = (
    (441, 443, 560, 840, 450),  # top left
    (441, 443, 620, 840, 450),  # bottom left
    (847, 850, 560, 450, 840),  # top right
    (847, 850, 620, 450, 840),  # bottom right
)


def slider(game: Game) -> None:
    """Slider(): drag the green handle to start a minigame."""
    for left, right, y, x_from, x_to in SLIDER_POSITIONS:
        if game.pixel_search(left, y, right, y, 0x007E00):
            game.move(x_from, y)
            game.drag(x_from, y, x_to, y)
            return


def slide_until_gone(game: Game, where: str, left: int, top: int, right: int, bottom: int, color: int) -> None:
    """`Do Slider() / Sleep(500) / Until PixelSearch(...) fails`, with a safety net."""
    deadline = game.now() + STUCK_MS
    while True:
        slider(game)
        game.sleep(500)
        if game.pixel_search(left, top, right, bottom, color) is None:
            return
        if game.now() > deadline:
            game.stuck(f"{where}.slider")
            return

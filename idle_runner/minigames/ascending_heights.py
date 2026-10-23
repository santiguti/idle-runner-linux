"""Ascending Heights, ported from Libraries/AscendingHeights.au3."""
from idle_runner.game import Game, Point
from idle_runner.log import event
from idle_runner.minigames.common import slide_until_gone

PLATFORM = 0xC0CBDC
PLATFORM_EDGE = 0x8B9BB4
PLAYER = 0x633E75


def ascending_heights(game: Game) -> None:
    event("Start of Ascending Heights")
    slide_until_gone(game, "ascending_heights", 640, 240, 634, 640, 0xFFCC66)
    game.sleep(3900)
    game.save_frame("ascending-heights-start")
    play(game)
    game.save_frame("ascending-heights-end")


def play(game: Game) -> None:
    last_platform: Point = (0, 0)
    same_count = 0
    same = False
    last_check = start = game.now()
    while True:
        if game.now() - start >= 240_000:
            event("Ascending Heights timed out after 4 minutes")
            game.hold(3000, 0, "a")
            game.sleep(100)
            game.hold(3000, 0, "d")
            return
        if game.now() - last_check >= 5000:
            last_check = game.now()
            if game.pixel_is(190, 125, 0xFFAF36):
                event("Ascending Height Failed")
                return
            if game.pixel_is(540, 560, 0x00A400):  # "second wind": continue
                game.sleep(2000)
                game.click(560, 570)
            if game.pixel_search(700, 385, 730, 385, 0x7A444A):
                game.hold(15_000, 0, "d")
                event("Ascending Height Won")
                return

        player = game.pixel_search(375, 260, 900, 730, PLAYER)
        if player is None:
            continue
        platform = platform_below(game, player[0], player[1], same)
        if platform is None:
            continue
        if platform == last_platform:
            same_count += 1
            if same_count == 5:  # stuck aiming at the same platform: widen the search
                same = True
        else:
            same_count = 0
            same = False
        last_platform = platform

        if platform[0] + 35 > player[0] + 35:
            steer(game, 1100)  # hold on the right half of the screen
        elif platform[0] + 35 < player[0] - 35:
            steer(game, 100)  # hold on the left half


def steer(game: Game, x: int) -> None:
    game.move(x, 600)
    game.mouse_down()
    game.sleep(100)
    game.mouse_up()


def platform_below(game: Game, px: int, py: int, same: bool) -> Point | None:
    """searchAllPlatformBellowPlayer: the highest platform under the player whose edge pixel isn't dark."""
    if not same:
        # Fixed: the original set `$iLeft = 900` when the right bound overflowed.
        left, right = max(px - 130, 375), min(px + 130, 900)
        platform = (game.pixel_search(left, py + 50, right, 752, PLATFORM)
                    or game.pixel_search(375, py + 50, 900, 752, PLATFORM))
    else:
        platform = game.pixel_search(375, py + 50, 900, 752, PLATFORM)
    for _ in range(1000):  # the original's safety counter
        if platform is None:
            return None
        if not game.pixel_is(platform[0] + 6, platform[1], PLATFORM_EDGE):
            return platform
        if platform[1] + 2 > 752:
            return None
        platform = game.pixel_search(375, platform[1] + 1, 900, 752, PLATFORM)
    return None

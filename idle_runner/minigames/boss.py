"""Boss fights, ported from Libraries/BossFightVictor.au3 and BossFightKnight.au3."""
from typing import Protocol

from idle_runner.game import STUCK_MS, Game
from idle_runner.log import event
from idle_runner.minigames.common import slide_until_gone
from idle_runner.repeater import Repeater


class Shooter(Protocol):
    """AdlibRegister("Shoot", 50) / AdlibUnRegister("Shoot")."""

    def resume(self) -> None: ...
    def pause(self) -> None: ...


def boss_fight_knight(game: Game) -> None:
    # The original returns right after this log line: its Knight logic is disabled, so it isn't ported.
    event("Start of BossFight Knight")


def boss_fight_victor(game: Game) -> None:
    event("Start of BossFight Victor")
    slide_until_gone(game, "victor", 653, 222, 653, 222, 0xFFF38F)
    game.save_frame("victor-start")
    shooter = Repeater(game, ("Up",), 50, "victor-shoot")
    try:
        victor_battle(game, shooter)
    finally:
        shooter.stop()
        game.save_frame("victor-end")


def victor_battle(game: Game, shooter: Shooter) -> None:
    shooter.resume()
    game.sleep(5000)
    first_stage = True
    interval = 2000
    last_check = start = game.now()
    while True:
        if not first_stage and game.pixel_search(1072, 150, 1072, 488, 0xFFFFFF):
            flame_attack(game)
        attack = game.pixel_search(919, 292, 919, 452, 0xFFFFFF)
        if attack:
            shooter.pause()
            if attack[1] > 370:
                down_attack(game, shooter, first_stage)
            else:
                upper_attack(game, shooter, first_stage)

        if game.now() - last_check > interval:
            if game.pixel_is(835, 477, 0xFD3169):  # victory screen
                shooter.pause()
                game.sleep(500)
                game.click(615, 563)
                event("Victor Won")
                return
            if first_stage and game.pixel_is(272, 130, 0xAE6C37):  # stage 2 dialog
                first_stage = False
                interval = 10_000
                event("Victor Stage 2")
                shooter.resume()
                deadline = game.now() + STUCK_MS
                while True:
                    game.sleep(50)
                    if not game.pixel_is(272, 130, 0xAE6C37):
                        break
                    if game.now() > deadline:
                        game.stuck("victor.dialog")
                        break
                game.sleep(4000)
                shooter.pause()
            if game.now() - start > 200_000:
                shooter.pause()
                event("Victor Lost")
                return
            last_check = game.now()


def flame_attack(game: Game) -> None:
    game.sleep(350)
    game.key_down("Up")
    game.sleep(100)
    game.key_up("Up")
    for _ in range(18):
        game.sleep(10)
        game.tap("Up")


def down_attack(game: Game, shooter: Shooter, first_stage: bool) -> None:
    game.sleep(200)
    if first_stage:
        shooter.resume()
        return
    game.key_down("Up")
    game.sleep(100)
    game.key_up("Up")
    for _ in range(18):
        game.sleep(10)
        game.tap("Up")


def upper_attack(game: Game, shooter: Shooter, first_stage: bool) -> None:
    game.sleep(730)
    if first_stage:
        shooter.resume()
        return
    for _ in range(15):
        game.sleep(10)
        game.tap("Up")

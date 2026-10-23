"""The main loop, ported from Main() in Idle Runner.au3: fast checks every ~40 ms, slow checks every 5 s."""
import dataclasses
import signal
from collections.abc import Callable

from idle_runner.actions import (BIDIMENSIONAL_STAFF, DIMENSIONAL_STAFF, RAGE_PILL, SOUL_COMPASS,
                                 buy_temp_item, close_all, collect_minions, soul_bonus_active)
from idle_runner.coins import read_coins
from idle_runner.config import Settings
from idle_runner.game import Game
from idle_runner.log import event, log
from idle_runner.minigames.chest_hunt import chest_hunt
from idle_runner.minigames.bonus_stage import bonus_stage
from idle_runner.minigames.boss import boss_fight_knight, boss_fight_victor
from idle_runner.minigames.ascending_heights import ascending_heights
from idle_runner.portals import portal_ready, take_portal
from idle_runner.repeater import Repeater
from idle_runner.shop import Shop
from idle_runner.x11 import GameUnavailable, WindowGone

EXPECTED_SIZE = (1280, 720)
WINDOW_RETRY_MS = 2000  # how often to look for the game window again after it is gone
BOX_RETRY_MS = 15_000  # buy again this soon after a Random Box stopped a buy
SIX_COIN_TIMEOUT_MS = 120_000  # buy anyway if the counter stays unreadable this long after reading < 6
MAX_CONSECUTIVE_CRASHES = 5  # unexpected errors in a row before giving up (e.g. the game window is gone)


def install_stop_signals() -> None:
    """Make `kill` (SIGTERM) and closing the terminal (SIGHUP) stop the bot like Ctrl+C,
    so the shutdown path still releases every held key."""
    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, signal.default_int_handler)


class Runner:
    def __init__(self, game: Game, settings: Settings, jumper: Repeater) -> None:
        self.game = game
        self.s = settings
        self.jumper = jumper
        self.shop = Shop(game)
        now = game.now()
        self.last_slow = now
        self.timer_buy = now
        self.timer_ascend = now
        self.timer_bonus_sample = now
        self.buy_minutes: float = settings.auto_buy_minutes  # $iAutoBuyTempTimer
        self.portal_count = settings.circle_portals_count
        # The original unticks these after one use; with a read-only config they apply once per run.
        self.dimensional_pending = settings.craft_dimensional_staff
        self.bidimensional_pending = settings.craft_bidimensional_staff
        self.paused_reason: str | None = None
        self.unavailable_reason: str | None = None  # last GameUnavailable, until a tick completes
        self.coins_low_since: float | None = None  # when the counter last read under 6 (after an ascension)
        self.retry_buy_at: float | None = None  # set when a Random Box stopped a buy

    def run(self) -> None:
        g = self.game
        event("Bot started", window=f"{g.size[0]}x{g.size[1]}", **dataclasses.asdict(self.s))
        if g.size != EXPECTED_SIZE:
            log.warning("the game window is %dx%d; it must be 1280x720 or no pixel check will match", *g.size)
            event("Window size mismatch", expected="1280x720", actual=f"{g.size[0]}x{g.size[1]}")
        self.jumper.resume()
        crashes = 0
        try:
            while True:
                try:
                    self.tick()
                    crashes = 0
                    if self.unavailable_reason:
                        event("Resumed")
                        self.unavailable_reason = None
                except WindowGone:
                    event("Game window lost")
                    self.wait_for_window()
                except GameUnavailable as exc:
                    if str(exc) != self.unavailable_reason:  # once per state change, not every tick
                        event("Game unavailable", reason=str(exc))
                        self.unavailable_reason = str(exc)
                    g.sleep(500)
                except Exception:
                    crashes += 1
                    log.exception("tick crashed (%d in a row)", crashes)
                    event("tick_crash", in_a_row=crashes)
                    if crashes >= MAX_CONSECUTIVE_CRASHES:
                        event("Bot stopped after repeated errors")
                        raise
                    g.sleep(5000)
        except KeyboardInterrupt:
            event("Bot stopped")
        finally:
            try:
                self.jumper.stop()
            finally:
                g.release_all()  # even if a second Ctrl+C interrupts the jumper shutdown

    def wait_for_window(self) -> None:
        """After the game window is destroyed (game closed or restarted), look it up by name again."""
        while True:
            self.game.sleep(WINDOW_RETRY_MS)
            try:
                self.game.find_window()
            except GameUnavailable:
                continue
            event("Game window found")
            return

    def tick(self) -> None:
        """One iteration of the original Main() loop."""
        g, s = self.game, self.s
        g.sleep(40)
        size = g.refresh_size()
        if size != EXPECTED_SIZE:
            reason = f"window is {size[0]}x{size[1]}, expected 1280x720"
        elif not g.is_active():
            reason = "game not focused"
        else:
            reason = None
        if reason:
            if reason != self.paused_reason:
                event(f"Paused: {reason}")
                if size != EXPECTED_SIZE:
                    log.warning("paused: %s (no pixel check can match at this size)", reason)
                self.paused_reason = reason
            self.unavailable_reason = None  # the pause explains it; its "Resumed" covers both
            g.sleep(500)
            return
        if self.paused_reason:
            event("Resumed")
            self.paused_reason = None

        # --- fast checks ---
        if g.pixel_is(650, 36, 0xCA9700):  # silver box
            event("Silver Box Collected")
            g.click(644, 49)
        if g.pixel_is(385, 280, 0x140C1C):  # megahorde
            self._routine("rage_when_horde", self.rage_when_horde)
        # A quest can be claimed: the shop button pulses 989898 -> CFCF46. The original matches CBCB4C
        # exactly, one ~7 ms frame at 144 FPS; ±16 covers ~160 ms of each pulse (measured 2026-10-22).
        if g.pixel_search(1130, 610, 1130, 610, 0xCBCB4C, variation=16):
            self._routine("claim_quests", self.shop.claim_quests)
        if soul_bonus_active(g):  # rage during soul bonus
            g.tap("r")
        if g.pixel_is(99, 113, 0xFFFF7A):  # minions are back
            self._routine("collect_minions", lambda: collect_minions(g))
        if g.pixel_is(187, 296, 0xFFBB31) and g.pixel_is(187, 303, 0xF68F37):  # chest hunt
            self._routine("chest_hunt", lambda: chest_hunt(
                g, s.no_lockpicking, s.perfect_chest_hunt, s.no_reinforced_crystal_saver))

        if s.auto_buy_upgrades:
            self.buy_at_six_coins()

        # --- slow checks, every 5 s ---
        if g.now() - self.last_slow >= 5000:
            self.last_slow = g.now()
            close_all(g)
            if g.pixel_is(660, 254, 0xFFE737) and g.pixel_is(638, 236, 0xFFBB31):  # bonus stage
                self._routine("bonus_stage", lambda: bonus_stage(g, s.skip_bonus_stage))
            if (g.pixel_is(639, 224, 0xFF878A) and g.pixel_is(634, 224, 0xF263BD)
                    and g.pixel_is(644, 224, 0xFFF38F)):  # boss fight
                if g.pixel_is(30, 690, 0x0B0303):
                    self._routine("boss_knight", lambda: boss_fight_knight(g))
                else:
                    self._routine("boss_victor", lambda: boss_fight_victor(g))
            if g.pixel_is(671, 213, 0xC2F4F9) and g.pixel_search(640, 240, 634, 640, 0xFFCC66):  # ascending heights
                self._routine("ascending_heights", lambda: ascending_heights(g))
            if s.circle_portals and portal_ready(g):
                self._routine("circle_portals", lambda: take_portal(g, self.portal_count))
                self.portal_count = self.portal_count % 9 + 1
            if s.auto_buy_upgrades and g.now() - self.timer_buy > self.buy_minutes * 60_000:
                self.timer_buy = g.now()
                self.buy_minutes = min(self.buy_minutes * 2, s.auto_buy_minutes)
                self.buy()
            elif self.retry_buy_at is not None and g.now() >= self.retry_buy_at:
                self.buy()
            if (s.ascend_bonus_sample_minutes
                    and g.now() - self.timer_bonus_sample > s.ascend_bonus_sample_minutes * 60_000):
                self.timer_bonus_sample = g.now()
                self._routine("ascend_bonus_sample", self.shop.sample_ascend_bonus)
            if s.auto_ascend and g.now() - self.timer_ascend > s.auto_ascend_minutes * 60_000:
                self.timer_ascend = g.now()
                self.shop.loop_amount = 0  # the original left this at its last value
                ascended = self._routine("auto_ascend", self.shop.auto_ascend)
                if ascended and s.post_ascend_first_buy_seconds:
                    self.timer_buy = g.now()
                    self.buy_minutes = s.post_ascend_first_buy_seconds / 60
                    event("Post-ascend buy ramp", first_buy_seconds=s.post_ascend_first_buy_seconds)

    def buy(self) -> None:
        """AutoUpgrade; if a Random Box stopped it, buy again in BOX_RETRY_MS (after the jumper got the
        box and any minigame it started is over: minigames run as routines in between)."""
        self.shop.loop_amount = 0
        completed = self._routine("auto_upgrade", self.shop.auto_upgrade)
        self.retry_buy_at = None if completed else self.game.now() + BOX_RETRY_MS

    def buy_at_six_coins(self) -> None:
        """Not in the original (user's rule, 2026-10-22): after an ascension, by the bot or by hand,
        buy as soon as the counter shows 6 coins, the price of the sword's first level. Then the
        post-ascension ramp takes over."""
        g, s = self.game, self.s
        coins = read_coins(g)
        if coins is not None and coins < 6:
            if self.coins_low_since is None:
                self.coins_low_since = g.now()
            return
        if self.coins_low_since is None:
            return
        if coins is None:
            if g.now() - self.coins_low_since < SIX_COIN_TIMEOUT_MS:
                return
            event("Coins reading timed out")
        else:
            event("Coins reached 6", coins=coins)
        self.coins_low_since = None
        self.buy()
        self.timer_buy = g.now()
        if s.post_ascend_first_buy_seconds:
            self.buy_minutes = s.post_ascend_first_buy_seconds / 60

    def rage_when_horde(self) -> None:
        g, s = self.game, self.s
        soul_bonus = soul_bonus_active(g)
        if soul_bonus:
            event("MegaHorde Rage with SoulBonus")
            if s.craft_rage_pill:
                buy_temp_item(g, RAGE_PILL)
            if s.craft_soul_bonus:
                buy_temp_item(g, SOUL_COMPASS)
        if soul_bonus or not s.disable_rage_without_soul_bonus:
            self.rage()

    def rage(self) -> None:
        g = self.game
        event("MegaHorde Rage")
        if self.dimensional_pending:
            buy_temp_item(g, DIMENSIONAL_STAFF)
            self.dimensional_pending = False
        if self.bidimensional_pending:
            buy_temp_item(g, BIDIMENSIONAL_STAFF)
            self.bidimensional_pending = False
        g.tap("r")

    def _routine[T](self, name: str, fn: Callable[[], T]) -> T:
        """SyncProcess(False) ... SyncProcess(True) around `fn`, with timing logs."""
        with self.jumper.paused(), self.game.routine(name):
            return fn()

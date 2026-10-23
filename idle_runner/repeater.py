"""Background key repeater.

Used for the jump/boost loop and for Victor's `AdlibRegister("Shoot", 50)`. In the original,
`ShootAndBoost` ran as a second process that noticed pauses up to 700 ms late.
"""
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from idle_runner.game import Game
from idle_runner.log import event, log
from idle_runner.x11 import GameUnavailable


class Repeater:
    """Taps `keys` every `interval_ms` on a daemon thread. Starts paused: call resume()."""

    def __init__(self, game: Game, keys: tuple[str, ...], interval_ms: float, name: str) -> None:
        self.game = game
        self.keys = keys
        self.interval_ms = interval_ms
        self.name = name
        self._running = threading.Event()
        self._stop = threading.Event()
        self._tap_lock = threading.Lock()
        self._thread = threading.Thread(target=self._loop, name=name, daemon=True)
        self._thread.start()

    def resume(self) -> None:
        self._running.set()

    def pause(self) -> None:
        """Stop tapping. Returns only once an in-flight tap has finished (SyncProcess(False))."""
        self._running.clear()
        with self._tap_lock:
            pass

    def stop(self) -> None:
        self._stop.set()
        self._running.set()  # wake the thread so it can exit
        self._thread.join(timeout=2)

    @contextmanager
    def paused(self) -> Iterator[None]:
        """Pause for the duration of a routine, then restore the previous state."""
        was_running = self._running.is_set()
        self.pause()
        try:
            yield
        finally:
            if was_running:
                self.resume()

    def _loop(self) -> None:
        while True:
            self._running.wait()
            if self._stop.is_set():
                return
            self.game.sleep(self.interval_ms)
            try:
                with self._tap_lock:
                    if self._stop.is_set() or not self._running.is_set():
                        continue
                    for key in self.keys:
                        self.game.tap(key)
            except GameUnavailable:
                self.game.sleep(500)  # the game isn't focused: stay quiet
            except Exception:
                log.exception("repeater %s failed; retrying in 1 s", self.name)
                event("repeater_error", name=self.name)
                self.game.sleep(1000)

import time

from idle_runner.repeater import Repeater


def test_taps_keys_until_paused_and_pause_is_immediate(fake, game) -> None:
    fake.realtime = True
    repeater = Repeater(game, ("Up", "Right"), interval_ms=10, name="jumper")
    repeater.resume()
    time.sleep(0.2)
    repeater.pause()
    count = len(fake.taps())
    time.sleep(0.1)
    repeater.stop()

    assert count >= 4
    assert fake.taps()[:2] == ["Up", "Right"]
    assert len(fake.taps()) == count  # nothing after pause() returned


def test_paused_context_restores_the_previous_state(fake, game) -> None:
    fake.realtime = True
    repeater = Repeater(game, ("Up",), interval_ms=10, name="jumper")
    repeater.resume()
    with repeater.paused():
        count = len(fake.taps())
        time.sleep(0.05)
        assert len(fake.taps()) == count
    time.sleep(0.05)
    repeater.stop()

    assert len(fake.taps()) > count


def test_does_not_tap_while_the_game_is_unfocused(fake, game) -> None:
    fake.realtime = True
    fake.active = False
    repeater = Repeater(game, ("Up",), interval_ms=10, name="jumper")
    repeater.resume()
    time.sleep(0.1)
    repeater.stop()

    assert fake.taps() == []


def test_repeater_logs_errors_and_keeps_running(fake, game, event_names) -> None:
    fake.realtime = True
    real_key = fake.key
    failures = [RuntimeError("X connection hiccup")]

    def flaky_key(name: str, down: bool) -> None:
        if failures:
            raise failures.pop()
        real_key(name, down)

    fake.key = flaky_key
    repeater = Repeater(game, ("Up",), interval_ms=10, name="jumper")
    repeater.resume()
    deadline = time.monotonic() + 5  # the error, a 1 s back-off, then more taps
    while "Up" not in fake.taps() and time.monotonic() < deadline:
        time.sleep(0.05)
    repeater.stop()

    assert "repeater_error" in event_names()
    assert "Up" in fake.taps()

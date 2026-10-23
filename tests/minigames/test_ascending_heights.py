from idle_runner.minigames.ascending_heights import platform_below, play


def test_platform_below_prefers_the_platform_near_the_player(game, fake) -> None:
    # Near the right edge the original clamped `left` instead of `right` and lost nearby platforms.
    fake.paint(400, 450, 0xC0CBDC)  # far platform, higher on screen
    fake.paint(880, 500, 0xC0CBDC)  # platform right below the player

    assert platform_below(game, 850, 300, same=False) == (880, 500)


def test_play_stops_on_the_failure_screen(game, fake, event_names) -> None:
    fake.paint(190, 125, 0xFFAF36)
    fake.cost_ms = 50
    play(game)

    assert event_names()[-1] == "Ascending Height Failed"


def test_play_times_out_after_4_minutes(game, fake, event_names) -> None:
    fake.cost_ms = 1000  # 4 virtual minutes in ~240 iterations keeps the suite fast
    play(game)

    assert "Ascending Heights timed out after 4 minutes" in event_names()
    assert ("key", "a", True) in fake.actions and ("key", "d", True) in fake.actions

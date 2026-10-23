from idle_runner.minigames.boss import boss_fight_knight, victor_battle


class FakeShooter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def resume(self) -> None:
        self.calls.append("resume")

    def pause(self) -> None:
        self.calls.append("pause")


def test_victor_battle_ends_when_won(game, fake, event_names) -> None:
    fake.paint(835, 477, 0xFD3169)  # the victory screen
    shooter = FakeShooter()
    victor_battle(game, shooter)

    assert "Victor Won" in event_names()
    assert (615, 563) in fake.clicks()
    assert shooter.calls[0] == "resume" and shooter.calls[-1] == "pause"


def test_victor_battle_gives_up_after_200_seconds(game, fake, event_names) -> None:
    fake.cost_ms = 50
    victor_battle(game, FakeShooter())

    assert "Victor Lost" in event_names()


def test_knight_is_logged_but_not_fought(game, fake, event_names) -> None:
    boss_fight_knight(game)

    assert event_names() == ["Start of BossFight Knight"]
    assert fake.actions == []

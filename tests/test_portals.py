from idle_runner.portals import portal_ready, take_portal


def test_not_ready_when_the_portal_button_is_hidden(game) -> None:
    assert not portal_ready(game)


def test_not_ready_while_the_countdown_shows(game, fake) -> None:
    fake.paint(1180, 166, 0x830399)
    fake.paint(1160, 150, 0xFFFFFF)  # countdown text
    assert not portal_ready(game)


def test_ready_when_the_button_shows_without_countdown(game, fake) -> None:
    fake.paint(1180, 166, 0x290130)
    assert portal_ready(game)


def test_take_portal_clicks_the_destination(game, fake, event_names) -> None:
    fake.paint(470, 300, 0x00F8B5)  # factory = destination 7
    take_portal(game, 7)

    assert (770, 300) in fake.clicks()
    assert "CirclePortals" in event_names()


def test_take_portal_gives_up_when_the_destination_is_missing(game, fake, event_names) -> None:
    take_portal(game, 1)

    assert (600, 600) in fake.clicks()
    assert "Portal destination not found" in event_names()

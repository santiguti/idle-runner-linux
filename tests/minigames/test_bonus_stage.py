import pytest

from idle_runner.minigames.bonus_stage import BS2_SECTIONS, bonus_stage, bs2_section, bs3_section1, run_bs2, run_bs3


def test_bs2_stops_and_logs_when_the_stage_fails(game, fake, event_names) -> None:
    fake.paint(716, 600, 0xAF0000)  # the fail screen's close button
    run_bs2(game, sb=False)

    names = event_names()
    assert "BonusStage2" in names and "BonusStage2 Failed" in names
    assert "BonusStage2 Section 1 Complete" not in names
    assert (716, 600) in fake.clicks()


def test_bs3_retries_one_failed_section_once(game) -> None:
    calls = []
    pending_failures = {1: 1}  # section index 1 fails once

    def make(index: int):
        def section(g, sb: bool) -> bool:
            calls.append(index)
            if pending_failures.get(index):
                pending_failures[index] -= 1
                return False
            return True
        return section

    run_bs3(game, False, sections=tuple(make(i) for i in range(4)))

    assert calls == [0, 1, 1, 2, 3]


def test_bs3_gives_up_after_the_second_failure(game) -> None:
    calls = []

    def ok(g, sb: bool) -> bool:
        calls.append("ok")
        return True

    def bad(g, sb: bool) -> bool:
        calls.append("bad")
        return False

    run_bs3(game, False, sections=(ok, bad, ok, ok))

    assert calls == ["ok", "bad", "bad"]


def test_skip_bonus_stage_waits_for_the_fail_screen(game, fake, event_names) -> None:
    fake.paint(716, 600, 0xAF0000)
    bonus_stage(game, skip=True)

    names = event_names()
    assert "Do nothing BonusStage Active" in names and "BonusStage2 Failed" in names


def test_bs3_sync_timeouts_are_logged(game, events) -> None:
    bs3_section1(game, False)

    assert any(r["event"] == "Sync timeout" and r["where"] == "BonusStage3-s1-1" for r in events())


def test_skipped_bonus_stage_saves_the_end_frame(game, fake, events) -> None:
    fake.paint(716, 600, 0xAF0000)
    bonus_stage(game, skip=True)

    labels = [r["label"] for r in events() if r["event"] == "frame"]
    assert labels == ["bonus-stage-start", "bonus-stage-end"]


def test_bs2_takes_second_wind_and_reruns_the_failed_section(game, fake, event_names) -> None:
    fake.paint(716, 600, 0xAF0000)  # fail screen: Close button...
    fake.paint(615, 590, 0x00A400)  # ...and the Second Wind button
    for x, y, color in ((220, 465, 0xCFBCB8), (780, 513, 0xBB26DF), (200, 400, 0x0D2030)):
        fake.paint(x, y, color)  # every section's sync marker, so the test doesn't wait out timeouts

    def second_wind(action: tuple) -> None:
        if action == ("click", 560 - 8, 600 - 31):  # Second Wind: the dialog closes
            fake.paint(716, 600, 0)
            fake.paint(615, 590, 0)

    fake.on_action = second_wind
    run_bs2(game, sb=False)

    names = event_names()
    assert fake.clicks().count((560, 600)) == 1 and (716, 600) not in fake.clicks()
    assert "BonusStage2 Retry" in names and "BonusStage2 Section 4 Complete" in names
    assert "BonusStage2 Failed" not in names


def test_bs2_closes_the_fail_screen_when_the_rerun_fails_too(game, fake, event_names) -> None:
    fake.paint(716, 600, 0xAF0000)
    fake.paint(615, 590, 0x00A400)  # stays up: the rerun fails as well
    run_bs2(game, sb=False)

    assert fake.clicks().count((560, 600)) == 1 and fake.clicks()[-1] == (716, 600)
    assert "BonusStage2 Failed" in event_names()


@pytest.mark.parametrize("edge_x", [163, 179, 205, 220])  # light edges of the resting block, measured in 3 runs
def test_bs2_first_sync_finds_the_block_wherever_it_stops(game, fake, event_names, edge_x: int) -> None:
    fake.paint(edge_x, 465, 0xCFBCB8)
    bs2_section(game, BS2_SECTIONS[0], "BonusStage2-s1")

    assert "Sync timeout" not in event_names()

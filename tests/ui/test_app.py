"""The window, built on a withdrawn root: never shown, so it never takes the game's focus."""
import json
import os
import sys
from pathlib import Path

import pytest

import idle_runner.ui.app as app_module
from idle_runner.ui.app import PAGES, App, BotProcess, GameProbe

pytestmark = pytest.mark.skipif(sys.platform == "linux" and not os.environ.get("DISPLAY"), reason="needs a display")


@pytest.fixture
def window(tmp_path, monkeypatch, root):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(app_module, "latest_tag", lambda: None)  # no network in tests
    monkeypatch.setattr(GameProbe, "status", lambda self, name: ("off", "Idle Slayer isn't running"))

    def build(config_text: str = "") -> App:
        config = tmp_path / "config.toml"
        config.write_text(config_text, encoding="utf-8")
        return App(root, config)

    return build


def test_the_window_builds_every_page(window) -> None:
    app = window()

    assert set(app.pages) == set(PAGES)
    assert app.state_label.cget("text") == "Stopped"


def test_the_window_starts_with_a_bad_config(window) -> None:
    app = window('[tree]\ntree_order = ["Moon Boots"]\n')

    assert "Moon Boots" in app.settings_page.message.cget("text")
    assert app.settings_page.settings.tree_order[0] == "Village Key"  # the defaults
    assert app.nav["Settings"].cget("style") == "Current.Nav.TButton"


def test_the_dashboard_follows_the_events(window, tmp_path) -> None:
    app = window()
    events = tmp_path / "logs" / "events.jsonl"
    events.parent.mkdir(exist_ok=True)
    lines = [{"ts": 1.0, "event": "Bot started"}, {"ts": 2.0, "event": "AutoUpgrade Done", "upgrades": 3,
             "equipment": 0}, {"ts": 3.0, "event": "Sync timeout", "where": "BonusStage2-s1"}]
    events.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    app.poll()

    assert app.stat_values["Upgrades"].cget("text") == "3"
    assert app.stat_values["Problems"].cget("text") == "1"
    assert "Bought 3 upgrades" in app.recent.get("1.0", "end")


def test_saving_a_setting_writes_the_config(window, tmp_path) -> None:
    app = window()
    app.settings_page.vars["auto_buy_minutes"].set("3")

    assert app.settings_page.save()
    assert "auto_buy_minutes = 3.0" in (tmp_path / "config.toml").read_text(encoding="utf-8")


def test_an_invalid_value_is_shown_and_not_saved(window, tmp_path) -> None:
    app = window()
    app.settings_page.vars["jump_interval_ms"].set("999")

    assert not app.settings_page.save()
    assert "“Time between jumps” must be 0-300" in app.settings_page.message.cget("text")
    assert (tmp_path / "config.toml").read_text(encoding="utf-8") == ""


def test_the_bot_stops_when_its_stdin_closes(monkeypatch, tmp_path) -> None:
    started = []

    class FakePopen:
        def __init__(self, args, **kwargs) -> None:
            started.append((args, kwargs))
            self.stdin = open(os.devnull, "w", encoding="utf-8")
            self.stdout = iter(["Bot started\n"])

        def poll(self):
            return None if not self.stdin.closed else 0

    monkeypatch.setattr(app_module.subprocess, "Popen", FakePopen)
    bot = BotProcess()
    bot.start(tmp_path / "config.toml")
    assert bot.running() and started[0][0][-1] == "--stop-on-stdin-eof"
    assert started[0][1]["stdin"] == app_module.subprocess.PIPE

    bot.stop()

    assert not bot.running()


def test_the_game_probe_never_raises(monkeypatch) -> None:
    def broken(name: str):
        raise RuntimeError("no display")

    monkeypatch.setattr(app_module, "open_backend", broken)

    assert GameProbe().status("Idle Slayer") == ("off", "Idle Slayer isn't running")


def test_the_support_button_opens_the_donation_page(window, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "DONATE_URL", "https://ko-fi.com/example")
    opened = []
    monkeypatch.setattr(app_module.webbrowser, "open", opened.append)
    app = window()

    app.support_button.invoke()

    assert opened == ["https://ko-fi.com/example"]


def test_no_support_button_without_a_donation_page(window, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "DONATE_URL", "")

    assert window().support_button is None

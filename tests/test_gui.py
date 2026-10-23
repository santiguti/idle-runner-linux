from pathlib import Path

from idle_runner.gui import hints

EXAMPLE = Path(__file__).resolve().parents[1] / "config.example.toml"


def test_hints_come_from_the_example_config() -> None:
    found = hints(EXAMPLE)

    assert found["auto_buy_minutes"] == "how often to buy, once auto_buy_upgrades is on"
    assert found["blackbox_fps"].startswith("black box:")
    assert "window_name" not in found  # no comment on its line

from pathlib import Path

from idle_runner.gui import hints

EXAMPLE = Path(__file__).resolve().parents[1] / "config.example.toml"


def test_hints_come_from_the_example_config() -> None:
    found = hints(EXAMPLE)

    assert found["auto_buy_minutes"] == "how often to buy, once auto_buy_upgrades is on"
    assert found["blackbox_fps"].startswith("black box:")
    assert "window_name" not in found  # no comment on its line


def test_saving_the_old_window_keeps_a_custom_tree_order(tmp_path) -> None:
    # The window has no field for tree_order (the Tree order page replaces it): saving must not reset it.
    import tkinter as tk

    import pytest

    from idle_runner.gui import App

    config = tmp_path / "config.toml"
    config.write_text('[tree]\ntree_order = ["Portals", "Green Ore"]\n', encoding="utf-8")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    root.withdraw()
    try:
        app = App(root, config)
        assert app.read_form().tree_order == ("Portals", "Green Ore")
    finally:
        root.destroy()

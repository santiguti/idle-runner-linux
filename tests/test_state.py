from pathlib import Path

from idle_runner.state import load_state, state_path, update_state


def test_state_lives_next_to_the_config(tmp_path: Path) -> None:
    assert state_path(tmp_path / "config.toml") == tmp_path / "state.json"


def test_a_missing_or_unreadable_file_is_an_empty_state(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    assert load_state(path) == {}
    for broken in ("{not json", "[1, 2]", ""):
        path.write_text(broken, encoding="utf-8")
        assert load_state(path) == {}, broken


def test_update_keeps_the_other_keys(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    update_state(path, tree_bought=["Village Key"])
    update_state(path, settings_ok_date="2026-10-28")

    assert load_state(path) == {"tree_bought": ["Village Key"], "settings_ok_date": "2026-10-28"}


def test_no_path_means_no_state() -> None:
    update_state(None, tree_bought=["Village Key"])  # nothing to write to: no error

    assert load_state(None) == {}

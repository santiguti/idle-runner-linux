import pytest

import idle_runner.__main__ as main_module
from tests.fakes import FakeBackend


def test_invalid_config_is_reported_cleanly(tmp_path, capsys) -> None:
    config = tmp_path / "config.toml"
    config.write_text("[general]\nbogus = 1\n")

    assert main_module.main(["run", "--config", str(config)]) == 1
    assert "unknown setting 'bogus'" in capsys.readouterr().err


def test_runtime_value_errors_are_not_reported_as_config_errors(tmp_path, monkeypatch) -> None:
    config = tmp_path / "config.toml"
    config.write_text("")
    monkeypatch.chdir(tmp_path)  # logs/ is created relative to the working directory

    def broken_backend(name: str) -> None:
        raise ValueError("cannot reshape array")

    monkeypatch.setattr(main_module, "X11Backend", broken_backend)
    with pytest.raises(ValueError, match="cannot reshape"):
        main_module.main(["run", "--config", str(config)])


def test_run_starts_and_stops_the_black_box(tmp_path, monkeypatch) -> None:
    config = tmp_path / "config.toml"
    config.write_text("")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main_module, "X11Backend", lambda name: FakeBackend())
    monkeypatch.setattr(main_module, "install_stop_signals", lambda: None)
    monkeypatch.setattr(main_module.Runner, "run", lambda self: None)
    started = []

    class FakePopen:
        def __init__(self, args: list[str]) -> None:
            self.args = args
            self.terminated = False
            started.append(self)

        def terminate(self) -> None:
            self.terminated = True

    monkeypatch.setattr(main_module.subprocess, "Popen", FakePopen)

    assert main_module.main(["run", "--config", str(config)]) == 0
    assert started[0].args[1:] == ["-m", "idle_runner", "blackbox", "--config", str(config)]
    assert started[0].terminated


def test_mark_command(tmp_path, capsys) -> None:
    log_dir = tmp_path / "logs"

    assert main_module.main(["mark", "shop stuck", "--log-dir", str(log_dir)]) == 0

    assert "saved to" in capsys.readouterr().out
    assert (next((log_dir / "marks").iterdir()) / "note.txt").read_text() == "shop stuck\n"

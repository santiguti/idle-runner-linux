import os
import sys
import types

import pytest

import idle_runner.__main__ as main_module
from idle_runner import __version__
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

    monkeypatch.setattr(main_module, "open_backend", broken_backend)
    monkeypatch.setattr(main_module, "single_instance", lambda: types.SimpleNamespace(close=lambda: None))
    with pytest.raises(ValueError, match="cannot reshape"):
        main_module.main(["run", "--config", str(config)])


def test_run_starts_and_stops_the_black_box(tmp_path, monkeypatch) -> None:
    config = tmp_path / "config.toml"
    config.write_text("")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main_module, "open_backend", lambda name: FakeBackend())
    monkeypatch.setattr(main_module, "install_stop_signals", lambda: None)
    monkeypatch.setattr(main_module.Runner, "run", lambda self: None)
    monkeypatch.setattr(main_module, "single_instance", lambda: types.SimpleNamespace(close=lambda: None))
    started = []

    class FakePopen:
        def __init__(self, args: list[str], stdin: int | None = None) -> None:
            self.args, self.stdin_arg = args, stdin
            self.stdin = types.SimpleNamespace(closed=False)
            self.stdin.close = lambda: setattr(self.stdin, "closed", True)
            self.waited = self.terminated = False
            started.append(self)

        def wait(self, timeout: float) -> int:
            self.waited = True
            return 0

        def terminate(self) -> None:
            self.terminated = True

    monkeypatch.setattr(main_module.subprocess, "Popen", FakePopen)

    assert main_module.main(["run", "--config", str(config)]) == 0
    box = started[0]
    # It stops when its stdin closes, so it also stops if this bot is killed outright.
    assert box.args[1:] == ["-m", "idle_runner", "blackbox", "--config", str(config), "--stop-on-stdin-eof"]
    assert box.stdin_arg == main_module.subprocess.PIPE
    assert box.stdin.closed and box.waited and not box.terminated


def test_run_refuses_a_second_bot(tmp_path, monkeypatch, capsys) -> None:
    config = tmp_path / "config.toml"
    config.write_text("")
    monkeypatch.setattr(main_module, "single_instance", lambda: None)
    monkeypatch.setattr(main_module, "open_backend", lambda name: pytest.fail("no backend for a second bot"))

    assert main_module.main(["run", "--config", str(config)]) == 1
    assert "another Idle Runner bot is already running" in capsys.readouterr().err


def test_mark_command(tmp_path, capsys) -> None:
    log_dir = tmp_path / "logs"

    assert main_module.main(["mark", "shop stuck", "--log-dir", str(log_dir)]) == 0

    assert "saved to" in capsys.readouterr().out
    assert (next((log_dir / "marks").iterdir()) / "note.txt").read_text() == "shop stuck\n"


def test_no_command_opens_the_window(monkeypatch) -> None:
    opened = []
    fake_gui = types.ModuleType("idle_runner.ui.app")
    fake_gui.main = lambda config: opened.append(config) or 0
    monkeypatch.setitem(sys.modules, "idle_runner.ui.app", fake_gui)

    assert main_module.main([]) == 0
    assert len(opened) == 1


def test_version_flag(capsys) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main_module.main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"Idle Runner {__version__}"


def test_frozen_main_runs_from_the_exe_folder(monkeypatch, tmp_path) -> None:
    folder = tmp_path / "Idle Runner é"
    folder.mkdir()
    monkeypatch.chdir(tmp_path)  # restored by pytest afterwards
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(folder / "IdleRunner.exe"))
    monkeypatch.setattr(sys, "stdout", None)  # windowed builds have no console
    monkeypatch.setattr(sys, "stderr", None)

    with pytest.raises(SystemExit):
        main_module.main(["--version"])

    assert os.getcwd() == str(folder)
    assert sys.stdout is not None and sys.stderr is not None

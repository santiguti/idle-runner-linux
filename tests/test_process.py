import sys

from idle_runner.process import self_command


def test_self_command_from_source() -> None:
    assert self_command("run") == [sys.executable, "-m", "idle_runner", "run"]


def test_self_command_frozen(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Juegos\Idle Runner é\IdleRunner.exe")

    assert self_command("run", "--config", "config.toml") == [
        r"C:\Juegos\Idle Runner é\IdleRunner.exe", "run", "--config", "config.toml"]

import os
import sys
import threading

from idle_runner.process import self_command, single_instance, stop_on_stdin_eof


def test_self_command_from_source() -> None:
    assert self_command("run") == [sys.executable, "-m", "idle_runner", "run"]


def test_self_command_frozen(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Juegos\Idle Runner é\IdleRunner.exe")

    assert self_command("run", "--config", "config.toml") == [
        r"C:\Juegos\Idle Runner é\IdleRunner.exe", "run", "--config", "config.toml"]


def test_stdin_eof_stops() -> None:
    read_fd, write_fd = os.pipe()
    stopped = threading.Event()
    stop_on_stdin_eof(os.fdopen(read_fd, encoding="utf-8"), stopped.set)
    assert not stopped.wait(0.1)

    os.close(write_fd)  # the window closed the pipe (Stop), or died

    assert stopped.wait(1)


def test_second_instance_is_refused() -> None:
    first = single_instance(port=0)  # any free port
    assert first is not None
    port = first.getsockname()[1]
    assert single_instance(port=port) is None

    first.close()  # that bot stopped
    assert single_instance(port=port) is not None


def test_a_command_line_on_stdin_runs_its_action_and_eof_still_stops() -> None:
    read_fd, write_fd = os.pipe()
    stopped, asked = threading.Event(), threading.Event()
    stop_on_stdin_eof(os.fdopen(read_fd, encoding="utf-8"), stopped.set, {"check-settings": asked.set})
    writer = os.fdopen(write_fd, "w", encoding="utf-8")

    writer.write("something else\ncheck-settings\n")
    writer.flush()  # the pipe stays open: the line must arrive without EOF

    assert asked.wait(1) and not stopped.is_set()
    writer.close()
    assert stopped.wait(1)

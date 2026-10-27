"""Process plumbing: starting Idle Runner's own sub-commands (the bot, the black box) as child processes,
stopping them without POSIX signals (Windows has no SIGINT for a child), and one bot at a time."""
import _thread
import socket
import sys
import threading
from collections.abc import Callable
from typing import IO

INSTANCE_PORT = 52671  # held on 127.0.0.1 by the running bot


def self_command(*args: str) -> list[str]:
    """argv that runs `idle_runner <args>`: the exe itself when frozen (PyInstaller), else `python -m`."""
    if getattr(sys, "frozen", False):
        return [sys.executable, *args]
    return [sys.executable, "-m", "idle_runner", *args]


def stop_on_stdin_eof(stream: IO[str], stop: Callable[[], None] = _thread.interrupt_main) -> threading.Thread:
    """Call `stop` once `stream` ends: the parent closed the pipe, or died. The default raises
    KeyboardInterrupt in the main thread, the same path as Ctrl+C, which releases every held key."""
    def watch() -> None:
        while stream.read(4096):
            pass
        stop()

    thread = threading.Thread(target=watch, name="stdin-watch", daemon=True)
    thread.start()
    return thread


def single_instance(port: int = INSTANCE_PORT) -> socket.socket | None:
    """Hold a local port for as long as the returned socket is open; None if another bot holds it. Two bots
    would fight over the same keys and clicks. The OS frees the port when the process ends, however."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
    except OSError:
        sock.close()
        return None
    return sock

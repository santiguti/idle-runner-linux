"""Starting Idle Runner's own sub-commands (the bot, the black box) as child processes."""
import sys


def self_command(*args: str) -> list[str]:
    """argv that runs `idle_runner <args>`: the exe itself when frozen (PyInstaller), else `python -m`."""
    if getattr(sys, "frozen", False):
        return [sys.executable, *args]
    return [sys.executable, "-m", "idle_runner", *args]

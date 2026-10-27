"""The platform backend against a real window with real input: a Tk window stands in for the game.

Opt-in (`pytest -m desktop`): it moves the mouse and presses keys on this desktop. CI runs it on Windows,
the only place the Win32 backend can run; on Linux run it only when nothing else needs the keyboard.
"""
import time
import tkinter as tk

import pytest

from idle_runner.game import open_backend

pytestmark = pytest.mark.desktop
TITLE = "Idle Runner backend test"  # never the game's title: no input can reach the game


def pump(root: tk.Tk, until, seconds: float = 2) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        root.update()
        if until():
            return True
        time.sleep(0.02)
    return False


def test_the_backend_finds_reads_and_drives_a_window() -> None:
    root = tk.Tk()
    root.title(TITLE)
    root.geometry("400x300+100+100")  # CI screens are 1024x768
    canvas = tk.Canvas(root, width=400, height=300, highlightthickness=0, bd=0)
    canvas.create_rectangle(0, 0, 200, 300, fill="#830399", width=0)
    canvas.create_rectangle(200, 0, 400, 300, fill="#11A622", width=0)
    canvas.pack()
    seen: list[str] = []
    canvas.bind("<ButtonPress-1>", lambda e: seen.append("click"))
    root.bind("<KeyPress-Up>", lambda e: seen.append("Up"))
    canvas.bind("<MouseWheel>", lambda e: seen.append("wheel"))  # Windows
    canvas.bind("<Button-4>", lambda e: seen.append("wheel"))  # X11
    try:
        root.attributes("-topmost", True)
        root.focus_force()
        pump(root, lambda: root.winfo_viewable(), 2)
        backend = open_backend(TITLE)

        assert backend.size() == (400, 300)
        assert pump(root, backend.is_active), "the test window never became the foreground window"
        # Foreground isn't on screen yet (Windows fades new windows in), and grab reads the screen.
        def pixel(x: int, y: int) -> list[int]:
            return backend.grab(x, y, 1, 1)[0, 0].tolist()

        assert pump(root, lambda: pixel(10, 10) == [0x83, 0x03, 0x99]), pixel(10, 10)
        assert pixel(300, 10) == [0x11, 0xA6, 0x22]

        backend.move(50, 50)
        backend.button(1, True)
        backend.button(1, False)
        backend.key("Up", True)
        backend.key("Up", False)
        backend.button(4, True)
        backend.button(4, False)

        assert pump(root, lambda: {"click", "Up", "wheel"} <= set(seen)), seen
    finally:
        root.destroy()

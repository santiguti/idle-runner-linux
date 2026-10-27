"""The Windows backend's pure parts and the exact input it sends, checked on any OS with fake DLLs. The real
calls are covered by tests/test_backend_desktop.py on the Windows CI runner and by trying it with the game."""
import ctypes

import pytest

import idle_runner.win32 as win32
from idle_runner.game import HELD_KEYS, GameUnavailable, WindowGone
from idle_runner.win32 import INPUT, VK, Win32Backend, bgra_to_rgb, wheel_delta

HWND = 0x1234


class FakeDll:
    """Records every call as (name, args); `returns` gives a function's return value (default 1)."""

    def __init__(self, calls: list[tuple], returns: dict[str, object]) -> None:
        self._calls, self._returns = calls, returns

    def __getattr__(self, name: str):
        def call(*args):
            self._calls.append((name, args))
            return self._returns.get(name, 1)
        return call


@pytest.fixture
def calls(monkeypatch) -> list[tuple]:
    recorded: list[tuple] = []
    returns = {"FindWindowW": HWND, "GetForegroundWindow": HWND, "IsIconic": 0, "MapVirtualKeyW": 0x48}
    monkeypatch.setattr(win32, "_load_dlls", lambda: (FakeDll(recorded, returns), FakeDll(recorded, returns)))
    return recorded


def sent_inputs(calls: list[tuple]) -> list[INPUT]:
    return [args[1].contents for name, args in calls if name == "SendInput"]


def test_every_bot_key_has_a_virtual_key() -> None:
    assert set(HELD_KEYS) <= set(VK)


def test_input_struct_matches_the_win64_abi() -> None:
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        assert ctypes.sizeof(INPUT) == 40


def test_bgra_to_rgb() -> None:
    assert bgra_to_rgb(bytes([0x99, 0x03, 0x83, 0xFF]), 1, 1)[0, 0].tolist() == [0x83, 0x03, 0x99]


def test_wheel_notches() -> None:
    assert (wheel_delta(4), wheel_delta(5), wheel_delta(1)) == (120, -120, 0)


def test_dpi_awareness_is_set_before_any_window_call(calls) -> None:
    Win32Backend("Idle Slayer")

    names = [name for name, _ in calls]
    assert names[0] == "SetProcessDpiAwarenessContext" and "FindWindowW" in names


def test_a_missing_window_is_game_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(win32, "_load_dlls", lambda: (FakeDll([], {"FindWindowW": None}), FakeDll([], {})))

    with pytest.raises(GameUnavailable, match="no window named 'Idle Slayer'"):
        Win32Backend("Idle Slayer")


def test_a_closed_window_is_window_gone(calls) -> None:
    backend = Win32Backend("Idle Slayer")
    backend.user32._returns["IsWindow"] = 0

    with pytest.raises(WindowGone):
        backend.is_active()


def test_arrow_keys_are_sent_as_extended_keys(calls) -> None:
    backend = Win32Backend("Idle Slayer")
    backend.key("Up", True)
    backend.key("Up", False)
    backend.key("r", True)

    down, up, r = sent_inputs(calls)
    assert (down.type, down.ki.wVk, down.ki.wScan, down.ki.dwFlags) == (1, 0x26, 0x48, 0x0001)
    assert (up.ki.wVk, up.ki.dwFlags) == (0x26, 0x0001 | 0x0002)
    assert (r.ki.wVk, r.ki.dwFlags) == (0x52, 0)


def test_unknown_key(calls) -> None:
    with pytest.raises(ValueError, match="unknown key"):
        Win32Backend("Idle Slayer").key("F13", True)


def test_mouse_buttons_and_wheel(calls) -> None:
    backend = Win32Backend("Idle Slayer")
    for button, down in ((1, True), (1, False), (5, True), (5, False)):
        backend.button(button, down)

    left_down, left_up, wheel = sent_inputs(calls)  # a wheel "release" sends nothing
    assert (left_down.type, left_down.mi.dwFlags) == (0, 0x0002)
    assert left_up.mi.dwFlags == 0x0004
    assert (wheel.mi.dwFlags, wheel.mi.mouseData) == (0x0800, (-120) & 0xFFFFFFFF)


def test_the_window_under_the_pointer(calls) -> None:
    backend = Win32Backend("Idle Slayer")
    backend.user32._returns["GetAncestor"] = HWND
    assert backend.pointer_over_game()

    backend.user32._returns["GetAncestor"] = 0x9999  # e.g. a notification over the game
    assert not backend.pointer_over_game()

"""Windows backend: finds the Idle Slayer window, captures its pixels and sends input with SendInput.

The same surface as x11.X11Backend, in client-area coordinates (0, 0 = top-left pixel of the 1280x720 game),
so `Game`'s AutoIt offset (8, 31) holds here too. Only stdlib ctypes; importable on any OS (the DLLs load in
`Win32Backend.__init__`), so the structures and the input it builds are tested on Linux as well.

Pixels come from the *screen* (BitBlt from GetDC(NULL)), like AutoIt's PixelGetColor: a Unity/DirectX
window's own DC can come back black. Whatever is on top of the game is captured too, which is fine: the bot
only acts while the game is the foreground window.
"""
import ctypes
import threading
import time
from typing import Any

import numpy as np

from idle_runner.game import GameUnavailable, WindowGone

# Explicit sizes (not ctypes.wintypes): DWORD is 32-bit on Windows but c_ulong is 64-bit on Linux.
DWORD, LONG, WORD, ULONG_PTR = ctypes.c_uint32, ctypes.c_int32, ctypes.c_uint16, ctypes.c_size_t
HANDLE = ctypes.c_void_p  # HWND, HDC, HBITMAP: pointer-sized; the default int restype would truncate them

INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP, MOUSEEVENTF_WHEEL = 0x0002, 0x0004, 0x0800
KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP = 0x0001, 0x0002
WHEEL_DELTA = 120
SRCCOPY = 0x00CC0020
# Every key the bot presses (game.HELD_KEYS): virtual-key code, and whether it is an extended key (arrows).
VK: dict[str, tuple[int, bool]] = {"Up": (0x26, True), "Right": (0x27, True), "a": (0x41, False),
                                   "d": (0x44, False), "r": (0x52, False)}


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", LONG), ("dy", LONG), ("mouseData", DWORD), ("dwFlags", DWORD), ("time", DWORD),
                ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", WORD), ("wScan", WORD), ("dwFlags", DWORD), ("time", DWORD), ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", DWORD), ("wParamL", WORD), ("wParamH", WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", DWORD), ("u", _INPUTUNION)]


class RECT(ctypes.Structure):
    _fields_ = [("left", LONG), ("top", LONG), ("right", LONG), ("bottom", LONG)]


class POINT(ctypes.Structure):
    _fields_ = [("x", LONG), ("y", LONG)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", DWORD), ("biWidth", LONG), ("biHeight", LONG), ("biPlanes", WORD),
                ("biBitCount", WORD), ("biCompression", DWORD), ("biSizeImage", DWORD),
                ("biXPelsPerMeter", LONG), ("biYPelsPerMeter", LONG), ("biClrUsed", DWORD),
                ("biClrImportant", DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", DWORD * 3)]


def _load_dlls() -> tuple[Any, Any]:
    """user32 and gdi32 with the signatures this module uses (replaced by fakes in tests)."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    signatures = {
        user32: {
            "SetProcessDpiAwarenessContext": ([HANDLE], ctypes.c_int),
            "FindWindowW": ([ctypes.c_wchar_p, ctypes.c_wchar_p], HANDLE),
            "IsWindow": ([HANDLE], ctypes.c_int),
            "IsIconic": ([HANDLE], ctypes.c_int),
            "GetClientRect": ([HANDLE, ctypes.POINTER(RECT)], ctypes.c_int),
            "ClientToScreen": ([HANDLE, ctypes.POINTER(POINT)], ctypes.c_int),
            "GetForegroundWindow": ([], HANDLE),
            "GetDC": ([HANDLE], HANDLE),
            "ReleaseDC": ([HANDLE, HANDLE], ctypes.c_int),
            "SetCursorPos": ([ctypes.c_int, ctypes.c_int], ctypes.c_int),
            "GetCursorPos": ([ctypes.POINTER(POINT)], ctypes.c_int),
            "WindowFromPoint": ([POINT], HANDLE),
            "GetAncestor": ([HANDLE, ctypes.c_uint], HANDLE),
            "SendInput": ([ctypes.c_uint, ctypes.POINTER(INPUT), ctypes.c_int], ctypes.c_uint),
            "MapVirtualKeyW": ([ctypes.c_uint, ctypes.c_uint], ctypes.c_uint),
        },
        gdi32: {
            "CreateCompatibleDC": ([HANDLE], HANDLE),
            "CreateCompatibleBitmap": ([HANDLE, ctypes.c_int, ctypes.c_int], HANDLE),
            "SelectObject": ([HANDLE, HANDLE], HANDLE),
            "BitBlt": ([HANDLE] + [ctypes.c_int] * 4 + [HANDLE, ctypes.c_int, ctypes.c_int, DWORD], ctypes.c_int),
            "GetDIBits": ([HANDLE, HANDLE, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p,
                           ctypes.POINTER(BITMAPINFO), ctypes.c_uint], ctypes.c_int),
            "DeleteObject": ([HANDLE], ctypes.c_int),
            "DeleteDC": ([HANDLE], ctypes.c_int),
        },
    }
    for dll, functions in signatures.items():
        for name, (argtypes, restype) in functions.items():
            try:
                function = getattr(dll, name)
            except AttributeError:  # SetProcessDpiAwarenessContext: Windows 10 1703 and later
                continue
            function.argtypes, function.restype = argtypes, restype
    return user32, gdi32


def enable_dpi_awareness(user32: Any = None) -> None:
    """Per-monitor DPI awareness for this process, before any window or coordinate call: then sizes, pixels
    and clicks are physical pixels at any display scaling (the original needed 100 %). An error means it was
    set already, which is fine."""
    user32 = user32 or _load_dlls()[0]
    try:
        user32.SetProcessDpiAwarenessContext(HANDLE(-4))  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
    except (AttributeError, OSError):
        try:
            ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)  # Windows 8.1: PROCESS_PER_MONITOR_DPI_AWARE
        except (AttributeError, OSError):
            pass


def bgra_to_rgb(data: bytes, w: int, h: int) -> np.ndarray:
    """RGB pixels (h, w, 3) from a top-down 32-bit BGRA DIB."""
    return np.frombuffer(data, dtype=np.uint8).reshape(h, w, 4)[:, :, 2::-1]


def wheel_delta(button: int) -> int:
    """X11-style wheel buttons: 4 = one notch up, 5 = one notch down."""
    return {4: WHEEL_DELTA, 5: -WHEEL_DELTA}.get(button, 0)


class Win32Backend:
    def __init__(self, window_name: str) -> None:
        # The jumper thread and the main loop both send input: one call at a time, as in X11Backend.
        self._lock = threading.RLock()
        self.user32, self.gdi32 = _load_dlls()
        enable_dpi_awareness(self.user32)
        self._name = window_name
        self._hwnd = self._find_window()

    @property
    def window_id(self) -> int:
        return self._hwnd

    def find_window(self) -> None:
        """Look the window up by its title again (after the game was restarted)."""
        with self._lock:
            self._hwnd = self._find_window()

    def _find_window(self) -> int:
        hwnd = self.user32.FindWindowW(None, self._name)
        if not hwnd:
            raise GameUnavailable(f"no window named {self._name!r}; is the game running?")
        return hwnd

    def _check(self) -> None:
        if not self.user32.IsWindow(self._hwnd):
            raise WindowGone("the game window is gone")
        if self.user32.IsIconic(self._hwnd):
            raise GameUnavailable("the game window is minimized")

    def size(self) -> tuple[int, int]:
        with self._lock:
            self._check()
            rect = RECT()
            self.user32.GetClientRect(self._hwnd, ctypes.byref(rect))
            return rect.right - rect.left, rect.bottom - rect.top

    def origin(self) -> tuple[int, int]:
        """Top-left of the client area in screen coordinates."""
        with self._lock:
            self._check()
            point = POINT(0, 0)
            self.user32.ClientToScreen(self._hwnd, ctypes.byref(point))
            return point.x, point.y

    def is_active(self) -> bool:
        with self._lock:
            self._check()
            return self.user32.GetForegroundWindow() == self._hwnd

    def grab(self, x: int, y: int, w: int, h: int) -> np.ndarray:
        """RGB pixels (h, w, 3) of a client-area rectangle."""
        origin_x, origin_y = self.origin()
        with self._lock:
            user32, gdi32 = self.user32, self.gdi32
            screen = user32.GetDC(None)
            memory = gdi32.CreateCompatibleDC(screen)
            bitmap = gdi32.CreateCompatibleBitmap(screen, w, h)
            try:
                previous = gdi32.SelectObject(memory, bitmap)
                gdi32.BitBlt(memory, 0, 0, w, h, screen, origin_x + x, origin_y + y, SRCCOPY)
                gdi32.SelectObject(memory, previous)  # GetDIBits needs the bitmap out of any DC
                info = BITMAPINFO()
                info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
                info.bmiHeader.biWidth, info.bmiHeader.biHeight = w, -h  # negative: top-down rows
                info.bmiHeader.biPlanes, info.bmiHeader.biBitCount = 1, 32  # biCompression 0 = BI_RGB
                data = ctypes.create_string_buffer(w * h * 4)
                if gdi32.GetDIBits(memory, bitmap, 0, h, data, ctypes.byref(info), 0) != h:  # DIB_RGB_COLORS
                    raise GameUnavailable("cannot capture the game window (GetDIBits failed)")
            finally:
                gdi32.DeleteObject(bitmap)
                gdi32.DeleteDC(memory)
                user32.ReleaseDC(None, screen)
        return bgra_to_rgb(data.raw, w, h)

    def move(self, x: int, y: int) -> None:
        origin_x, origin_y = self.origin()
        with self._lock:
            self.user32.SetCursorPos(origin_x + x, origin_y + y)

    def pointer_over_game(self) -> bool:
        """The game is the top-level window under the cursor (GA_ROOT of the window at that point)."""
        with self._lock:
            point = POINT()
            self.user32.GetCursorPos(ctypes.byref(point))
            return self.user32.GetAncestor(self.user32.WindowFromPoint(point), 2) == self._hwnd

    def button(self, button: int, down: bool) -> None:
        if button == 1:
            self._send(INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(
                dwFlags=MOUSEEVENTF_LEFTDOWN if down else MOUSEEVENTF_LEFTUP)))
        elif wheel_delta(button) and down:  # a wheel notch is one event; its "release" sends nothing
            self._send(INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(
                mouseData=wheel_delta(button) & 0xFFFFFFFF, dwFlags=MOUSEEVENTF_WHEEL)))

    def key(self, name: str, down: bool) -> None:
        if name not in VK:
            raise ValueError(f"unknown key {name!r}")
        vk, extended = VK[name]
        flags = (KEYEVENTF_EXTENDEDKEY if extended else 0) | (0 if down else KEYEVENTF_KEYUP)
        with self._lock:
            scan = self.user32.MapVirtualKeyW(vk, 0)  # MAPVK_VK_TO_VSC: games often read the scan code
        self._send(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags)))

    def _send(self, event: INPUT) -> None:
        with self._lock:
            self.user32.SendInput(1, ctypes.pointer(event), ctypes.sizeof(INPUT))

    def now_ms(self) -> float:
        return time.monotonic() * 1000

    def sleep_ms(self, ms: float) -> None:
        if ms > 0:
            time.sleep(ms / 1000)

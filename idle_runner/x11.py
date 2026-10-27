"""X11 backend: finds the Idle Slayer window, captures its pixels and injects input via XTEST.

Coordinates here are client-area coordinates of the game window (0, 0 = top-left pixel of the
1280x720 game). The AutoIt window-frame offset is handled one level up, in game.py.
"""
import threading
import time

import numpy as np
from Xlib import X, XK, display, error
from Xlib.ext import xtest
from Xlib.xobject.drawable import Window

from idle_runner.game import GameUnavailable, WindowGone


class X11Backend:
    def __init__(self, window_name: str) -> None:
        # python-xlib connections must not be used from two threads at once (the jumper
        # thread and the main loop both send input), so every request holds this lock.
        self._lock = threading.RLock()
        self._display = display.Display()
        if self._display.query_extension("XTEST") is None:
            raise RuntimeError("the X server has no XTEST extension; input injection is impossible")
        self._root = self._display.screen().root
        self._active_atom = self._display.intern_atom("_NET_ACTIVE_WINDOW")
        self._name = window_name
        self._window = self._find_window(window_name)

    @property
    def window_id(self) -> int:
        return self._window.id

    def find_window(self) -> None:
        """Look the window up by name again (AutoIt finds "Idle Slayer" by title on every call)."""
        with self._lock:
            self._window = self._find_window(self._name)

    def _find_window(self, name: str) -> Window:
        clients = self._root.get_full_property(self._display.intern_atom("_NET_CLIENT_LIST"), X.AnyPropertyType)
        for window_id in clients.value if clients else []:
            window = self._display.create_resource_object("window", window_id)
            try:
                window_name = self._window_name(window)
            except error.BadWindow:
                continue  # closed while we were listing (likely while the game restarts)
            if window_name == name:
                return window
        raise GameUnavailable(f"no X11 window named {name!r}; is the game running?")

    def _window_name(self, window: Window) -> str:
        utf8_name = window.get_full_property(
            self._display.intern_atom("_NET_WM_NAME"), self._display.intern_atom("UTF8_STRING"))
        if utf8_name:
            return utf8_name.value.decode("utf-8", "replace")
        name = window.get_wm_name()
        return name.decode("latin-1") if isinstance(name, bytes) else (name or "")

    def size(self) -> tuple[int, int]:
        with self._lock:
            try:
                geometry = self._window.get_geometry()
            except (error.BadWindow, error.BadDrawable) as exc:
                raise WindowGone(f"the game window is gone ({type(exc).__name__})") from exc
            return geometry.width, geometry.height

    def origin(self) -> tuple[int, int]:
        """Top-left of the client area in root (screen) coordinates."""
        with self._lock:
            try:
                reply = self._root.translate_coords(self._window, 0, 0)
            except (error.BadWindow, error.BadDrawable) as exc:
                raise WindowGone(f"the game window is gone ({type(exc).__name__})") from exc
            return reply.x, reply.y

    def is_active(self) -> bool:
        with self._lock:
            prop = self._root.get_full_property(self._active_atom, X.AnyPropertyType)
            return bool(prop) and len(prop.value) > 0 and prop.value[0] == self._window.id

    def grab(self, x: int, y: int, w: int, h: int) -> np.ndarray:
        """RGB pixels (h, w, 3) of a client-area rectangle."""
        with self._lock:
            try:
                image = self._window.get_image(x, y, w, h, X.ZPixmap, 0xFFFFFFFF)
            except (error.BadWindow, error.BadDrawable) as exc:
                raise WindowGone(f"the game window is gone ({type(exc).__name__})") from exc
            except error.BadMatch as exc:  # e.g. unmapped (minimized)
                raise GameUnavailable(f"cannot capture the game window ({type(exc).__name__})") from exc
        bgrx = np.frombuffer(image.data, dtype=np.uint8).reshape(h, w, 4)
        return bgrx[:, :, 2::-1]

    def move(self, x: int, y: int) -> None:
        origin_x, origin_y = self.origin()
        with self._lock:
            xtest.fake_input(self._display, X.MotionNotify, x=origin_x + x, y=origin_y + y)
            self._display.sync()

    def button(self, button: int, down: bool) -> None:
        with self._lock:
            xtest.fake_input(self._display, X.ButtonPress if down else X.ButtonRelease, button)
            self._display.sync()

    def key(self, name: str, down: bool) -> None:
        with self._lock:
            keycode = self._display.keysym_to_keycode(XK.string_to_keysym(name))
            if not keycode:
                raise ValueError(f"unknown key {name!r}")
            xtest.fake_input(self._display, X.KeyPress if down else X.KeyRelease, keycode)
            self._display.sync()

    def now_ms(self) -> float:
        return time.monotonic() * 1000

    def sleep_ms(self, ms: float) -> None:
        if ms > 0:
            time.sleep(ms / 1000)

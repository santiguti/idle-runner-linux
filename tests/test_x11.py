import os

import pytest
from Xlib import X, display

from idle_runner.x11 import WindowGone, X11Backend

pytestmark = pytest.mark.skipif(not os.environ.get("DISPLAY"), reason="needs an X server")


def test_a_destroyed_window_raises_window_gone(monkeypatch) -> None:
    other = display.Display()
    window = other.screen().root.create_window(0, 0, 10, 10, 0, X.CopyFromParent)  # never mapped: invisible
    other.sync()
    monkeypatch.setattr(X11Backend, "_find_window",
                        lambda self, name: self._display.create_resource_object("window", window.id))
    backend = X11Backend("test window")
    assert backend.size() == (10, 10)

    window.destroy()
    other.sync()
    for call in (backend.size, backend.origin, lambda: backend.grab(0, 0, 1, 1)):
        with pytest.raises(WindowGone):
            call()

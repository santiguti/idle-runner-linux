import time
import tkinter as tk
from collections.abc import Iterator

import pytest


@pytest.fixture
def root() -> Iterator[tk.Tk]:
    """A withdrawn Tk root: never mapped, so it can't take the game's focus."""
    for attempt in range(3):
        try:
            window = tk.Tk()
            break
        except tk.TclError as exc:
            if "display" in str(exc):  # Linux without an X server
                pytest.skip("no display")
            # GitHub's Windows runners now and then fail to read Tcl's own init.tcl ("couldn't read file
            # ... init.tcl: No error"); the next try reads it.
            if attempt == 2:
                raise
            time.sleep(0.5)
    window.withdraw()
    yield window
    window.destroy()

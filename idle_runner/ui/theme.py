"""The window's look, taken from Idle Slayer's own UI: dark plum panels in copper frames with square studs at
the corners (the game's dialogs), Slayer Points purple, coin gold, and the game's green Buy and red Close
for Start and Stop. Plain ttk on the "clam" theme, so it looks the same on Linux and Windows.

The icon and logo in assets/ are drawn by packaging/make_icons.py.
"""
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from tkinter import font as tkfont
from tkinter import ttk

ASSETS = Path(__file__).parent / "assets"
FAMILIES = ("Segoe UI", "Noto Sans", "Cantarell", "DejaVu Sans")  # the first one installed


@dataclass(frozen=True)
class Palette:
    bg: str = "#17121C"  # night: the window and the sidebar
    surface: str = "#231A29"  # panels
    raised: str = "#33263B"  # fields, the selected page, buttons
    frame: str = "#B9805A"  # copper, the game's dialog frames
    stud: str = "#E2B48C"  # the frame's corner studs
    text: str = "#F3EDF7"
    muted: str = "#B9AEC4"
    accent: str = "#A87CFF"  # Slayer Points
    gold: str = "#F2C14E"  # coins
    on_gold: str = "#2A1A05"  # text on a gold button
    ok: str = "#0C7A27"  # the game's green buttons, dark enough for white text
    danger: str = "#AF0000"  # the game's red Close
    danger_text: str = "#FF7A7A"  # errors written on a panel
    warning: str = "#F0A030"


PALETTE = Palette()


def contrast(fg: str, bg: str) -> float:
    """WCAG contrast ratio of two #RRGGBB colours (4.5 and up reads well)."""
    def luminance(colour: str) -> float:
        channels = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        r, g, b = (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    light, dark = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def apply_theme(root: tk.Tk) -> None:
    p = PALETTE
    family = next((f for f in FAMILIES if f in tkfont.families(root)), "TkDefaultFont")
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(name, root).configure(family=family, size=10)
    # Named fonts die with their Python object: keep them on the root.
    root.fonts = [tkfont.Font(root, name="Title", family=family, size=17, weight="bold"),  # type: ignore[attr-defined]
                  tkfont.Font(root, name="Big", family=family, size=20, weight="bold"),
                  tkfont.Font(root, name="Strong", family=family, size=10, weight="bold")]
    root.configure(bg=p.bg)
    root.option_add("*Text.font", "TkDefaultFont")
    root.option_add("*Text.background", p.surface)
    root.option_add("*Text.foreground", p.text)
    root.option_add("*Text.insertBackground", p.text)
    root.option_add("*Text.selectBackground", p.raised)
    root.option_add("*Text.relief", "flat")

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=p.bg, foreground=p.text, fieldbackground=p.raised, bordercolor=p.raised,
                    lightcolor=p.raised, darkcolor=p.raised, troughcolor=p.bg, focuscolor=p.frame,
                    selectbackground=p.accent, selectforeground="#FFFFFF", insertcolor=p.text, arrowcolor=p.text)
    style.configure("Panel.TFrame", background=p.surface)
    for name, bg in (("", p.bg), ("Panel.", p.surface)):
        style.configure(f"{name}TLabel", background=bg, foreground=p.text)
        style.configure(f"Muted.{name}TLabel", background=bg, foreground=p.muted)
        style.configure(f"Strong.{name}TLabel", background=bg, foreground=p.text, font="Strong")
        style.configure(f"{name}TCheckbutton", background=bg, foreground=p.text)
        style.configure(f"{name}TRadiobutton", background=bg, foreground=p.text)
        style.map(f"{name}TCheckbutton", background=[("active", bg)], indicatorcolor=[("selected", p.accent)])
        style.map(f"{name}TRadiobutton", background=[("active", bg)], indicatorcolor=[("selected", p.accent)])
    style.configure("Title.TLabel", font="Title")
    style.configure("Stat.Panel.TLabel", background=p.surface, foreground=p.gold, font="Big")
    style.configure("Error.Panel.TLabel", background=p.surface, foreground=p.danger_text)
    style.configure("Error.TLabel", background=p.bg, foreground=p.danger_text)
    style.configure("Warning.TLabel", background=p.bg, foreground=p.warning)
    style.configure("Warning.Panel.TLabel", background=p.surface, foreground=p.warning)

    style.configure("TButton", background=p.raised, foreground=p.text, borderwidth=1, focusthickness=1,
                    padding=(12, 5), relief="flat")
    style.map("TButton", background=[("pressed", p.bg), ("active", "#3F3048")], bordercolor=[("focus", p.frame)])
    for name, colour, active in (("Start", p.ok, "#0E8E2E"), ("Stop", p.danger, "#C41010")):
        style.configure(f"{name}.TButton", background=colour, foreground="#FFFFFF", font="Big", padding=(28, 10))
        style.map(f"{name}.TButton", background=[("pressed", colour), ("active", active)])
    style.configure("Support.TButton", background=p.gold, foreground=p.on_gold, font="Strong", padding=(12, 7))
    style.map("Support.TButton", background=[("pressed", p.gold), ("active", "#F7D27A")])
    style.configure("Nav.TButton", background=p.bg, foreground=p.muted, anchor="w", padding=(18, 9), borderwidth=0)
    style.map("Nav.TButton", background=[("active", p.surface)], foreground=[("active", p.text)])
    style.configure("Current.Nav.TButton", background=p.raised, foreground=p.text, font="Strong")
    style.map("Current.Nav.TButton", background=[("active", p.raised)])
    style.configure("Link.Panel.TLabel", background=p.surface, foreground=p.accent)
    style.configure("Link.TLabel", background=p.bg, foreground=p.accent)

    style.configure("TEntry", padding=4)
    style.configure("TSpinbox", padding=4, arrowsize=12)
    style.configure("TCombobox", padding=4)
    style.map("TCombobox", fieldbackground=[("readonly", p.raised)], foreground=[("readonly", p.text)])
    root.option_add("*TCombobox*Listbox.background", p.raised)
    root.option_add("*TCombobox*Listbox.foreground", p.text)
    style.configure("Horizontal.TScale", troughcolor=p.raised, background=p.frame, bordercolor=p.raised,
                    lightcolor=p.frame, darkcolor=p.frame)
    style.configure("Treeview", background=p.surface, fieldbackground=p.surface, foreground=p.text, rowheight=24,
                    borderwidth=0)
    style.map("Treeview", background=[("selected", p.raised)], foreground=[("selected", p.text)])
    style.configure("Treeview.Heading", background=p.raised, foreground=p.muted, relief="flat", font="Strong")
    style.map("Treeview.Heading", background=[("active", p.raised)])
    for orient in ("Vertical", "Horizontal"):
        style.configure(f"{orient}.TScrollbar", background=p.raised, troughcolor=p.bg, bordercolor=p.bg,
                        lightcolor=p.raised, darkcolor=p.raised, arrowcolor=p.muted, gripcount=0)
        style.map(f"{orient}.TScrollbar", background=[("active", "#3F3048")])


def panel(parent: tk.Misc, title: str = "", subtitle: str = "") -> ttk.Frame:
    """A copper-framed panel with studs at its corners, like the game's dialogs. Returns its body frame."""
    p = PALETTE
    outer = tk.Frame(parent, bg=p.surface, highlightthickness=2, highlightbackground=p.frame,
                     highlightcolor=p.frame)
    body = ttk.Frame(outer, style="Panel.TFrame", padding=(16, 12))
    for x, y in ((0, 0), (1, 0), (0, 1), (1, 1)):  # over the frame's corners, above the body
        stud = tk.Frame(outer, bg=p.stud, width=7, height=7)
        stud.place(relx=x, rely=y, x=-7 if x else 0, y=-7 if y else 0)
        stud.lift(body)
    if title:
        ttk.Label(body, text=title, style="Strong.Panel.TLabel").pack(anchor="w")
    if subtitle:
        ttk.Label(body, text=subtitle, style="Muted.Panel.TLabel", wraplength=640, justify="left").pack(
            anchor="w", pady=(2, 8))
    body.pack(fill="both", expand=True)
    body.outer = outer  # type: ignore[attr-defined]  # what the caller packs or grids
    return body


class Toggle(tk.Canvas):
    """An on/off switch bound to a BooleanVar (click or Space)."""

    def __init__(self, parent: tk.Misc, variable: tk.BooleanVar, command: Callable[[], None] | None = None,
                 bg: str = PALETTE.surface) -> None:
        super().__init__(parent, width=44, height=24, bg=bg, highlightthickness=1, highlightbackground=bg,
                         highlightcolor=PALETTE.frame, takefocus=True, cursor="hand2")
        self.variable, self.command = variable, command
        self.bind("<Button-1>", lambda e: self.toggle())
        self.bind("<space>", lambda e: self.toggle())
        variable.trace_add("write", lambda *_: self.draw())
        self.draw()

    def toggle(self) -> None:
        if str(self.cget("state")) == "disabled":
            return
        self.variable.set(not self.variable.get())
        if self.command:
            self.command()

    def draw(self) -> None:
        on = self.variable.get()
        disabled = str(self.cget("state")) == "disabled"
        self.delete("all")
        track = PALETTE.ok if on else PALETTE.raised
        self.create_rectangle(3, 4, 41, 20, fill="#3A3040" if disabled else track, outline=PALETTE.frame)
        knob = 25 if on else 5
        self.create_rectangle(knob, 6, knob + 14, 18, fill=PALETTE.muted if disabled else PALETTE.text, width=0)

    def set_enabled(self, enabled: bool) -> None:
        self.configure(state="normal" if enabled else "disabled", cursor="hand2" if enabled else "arrow")
        self.draw()

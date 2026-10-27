"""The Settings page: one copper panel per group (ui/fields.py), saved to config.toml a moment after each
valid change. Problems show at the top, named by their labels; nothing pops up."""
import tkinter as tk
from collections.abc import Callable
from dataclasses import fields
from pathlib import Path
from tkinter import messagebox, ttk

from idle_runner.config import Settings, check_ranges, dump_settings, load_settings
from idle_runner.ui.fields import CARDS, FIELDS, Field, friendly
from idle_runner.ui.theme import Toggle, panel

TYPES = {f.name: f.type for f in fields(Settings)}
SAVE_DELAY_MS = 600


def mtime(path: Path) -> float | None:
    return path.stat().st_mtime if path.exists() else None


class ScrollFrame(ttk.Frame):
    """A vertically scrolling area; put children in `.inner`. The wheel scrolls it while the pointer is over it."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=ttk.Style().lookup("TFrame", "background"))
        bar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = ttk.Frame(canvas)
        window = canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        canvas.configure(yscrollcommand=bar.set)
        canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")

        def wheel(event: tk.Event) -> None:
            steps = -1 if getattr(event, "num", 0) == 4 or getattr(event, "delta", 0) > 0 else 1
            canvas.yview_scroll(steps * 3, "units")

        def bind(_: tk.Event) -> None:
            for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                self.bind_all(sequence, wheel)

        def unbind(_: tk.Event) -> None:
            for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                self.unbind_all(sequence)

        self.bind("<Enter>", bind)
        self.bind("<Leave>", unbind)


class SettingsPage(ttk.Frame):
    def __init__(self, parent: tk.Misc, config_path: Path, on_saved: Callable[[Settings], None]) -> None:
        super().__init__(parent)
        self.config_path, self.on_saved = config_path, on_saved
        self.settings = Settings()
        self.load_error = ""
        try:
            if config_path.exists():
                self.settings = load_settings(config_path)
        except ValueError as exc:  # also covers a TOML syntax error
            self.load_error = (f"{friendly(str(exc))}. These are the defaults; changing a setting saves them "
                               f"over {config_path.name}.")
        self.saved_mtime = mtime(config_path)
        self.tree_order = self.settings.tree_order
        self.vars: dict[str, tk.Variable] = {}
        self.inputs: dict[str, list[tk.Widget]] = {}
        self.pending: str | None = None

        self.message = ttk.Label(self, wraplength=700, justify="left")
        self.message.pack(anchor="w", fill="x")
        scroll = ScrollFrame(self)
        scroll.pack(fill="both", expand=True)
        for card in CARDS:
            body = panel(scroll.inner, card)
            body.outer.pack(fill="x", pady=(0, 14), padx=(2, 14))
            body.columnconfigure(1, weight=1)
            for key, field in FIELDS.items():
                if field.card == card:
                    self.add_field(body, key, field)
        self.show_message(self.load_error, "Error")
        self.update_dependents()

    def add_field(self, body: ttk.Frame, key: str, field: Field) -> None:
        value = getattr(self.settings, key)
        row = ttk.Frame(body, style="Panel.TFrame")
        row.pack(fill="x", pady=5)
        row.columnconfigure(2, weight=1)  # a long help text widens this column, not the label's
        if field.kind == "toggle":
            var: tk.Variable = tk.BooleanVar(value=value)
            widget: tk.Widget = Toggle(row, var, command=self.changed)
            widget.grid(row=0, column=0, rowspan=3, sticky="nw", padx=(0, 12))
            ttk.Label(row, text=field.label, style="Strong.Panel.TLabel").grid(row=0, column=1, sticky="w")
        else:
            ttk.Label(row, text=field.label, style="Strong.Panel.TLabel").grid(row=0, column=0, sticky="w")
            row.columnconfigure(0, minsize=250)
            var = tk.StringVar(value=self.shown(field, value))
            widget = self.value_widget(row, field, var)
            widget.grid(row=0, column=1, sticky="w")
            var.trace_add("write", lambda *_: self.changed())
        if field.help:
            ttk.Label(row, text=field.help, style="Muted.Panel.TLabel", wraplength=560, justify="left").grid(
                row=1, column=1 if field.kind == "toggle" else 0, columnspan=3, sticky="w")
        if field.warning:
            ttk.Label(row, text=field.warning, style="Warning.Panel.TLabel", wraplength=560, justify="left").grid(
                row=2, column=1 if field.kind == "toggle" else 0, columnspan=3, sticky="w")
        self.vars[key] = var
        self.inputs[key] = [widget]

    def value_widget(self, row: ttk.Frame, field: Field, var: tk.StringVar) -> tk.Widget:
        box = ttk.Frame(row, style="Panel.TFrame")
        if field.kind == "slider":
            scale = ttk.Scale(box, from_=field.minimum, to=field.maximum, length=220,
                              command=lambda v: var.set(str(int(round(float(v) / field.step) * field.step))))
            scale.set(float(var.get()))
            scale.pack(side="left")
            ttk.Label(box, textvariable=var, style="Panel.TLabel", width=4, anchor="e").pack(side="left", padx=(8, 0))
        elif field.kind == "choice":
            ttk.Combobox(box, textvariable=var, values=field.choices, state="readonly", width=16).pack(side="left")
        elif field.kind == "text":
            ttk.Entry(box, textvariable=var, width=24).pack(side="left")
        else:
            ttk.Spinbox(box, textvariable=var, width=8, increment=field.step,
                        from_=field.minimum if field.minimum is not None else -10_000,
                        to=field.maximum if field.maximum is not None else 10_000).pack(side="left")
        if field.unit:
            ttk.Label(box, text=field.unit, style="Muted.Panel.TLabel").pack(side="left", padx=(6, 0))
        return box

    @staticmethod
    def shown(field: Field, value: object) -> str:
        if field.kind == "choice" and isinstance(value, int):
            return field.choices[value - 1]
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    def read(self) -> Settings:
        values: dict[str, object] = {}
        for key, var in self.vars.items():
            field, kind = FIELDS[key], TYPES[key]
            raw = var.get()
            if kind is bool or kind is str and field.kind != "choice":
                values[key] = raw.strip() if isinstance(raw, str) else raw
            elif field.kind == "choice":
                values[key] = field.choices.index(raw) + 1 if kind is int else raw
            else:
                try:
                    number = float(str(raw).replace(",", "."))
                except ValueError:
                    raise ValueError(f"x: “{field.label}” must be a number, not {raw!r}") from None
                values[key] = int(number) if kind is int else number
        return Settings(**values, tree_order=self.tree_order)

    def set_tree_order(self, order: tuple[str, ...]) -> None:
        self.tree_order = order
        self.changed()

    def changed(self) -> None:
        self.update_dependents()
        if self.pending:
            self.after_cancel(self.pending)
        self.pending = self.after(SAVE_DELAY_MS, self.save)

    def save(self) -> bool:
        """Write config.toml if the form is valid and differs from the file. False if it wasn't saved."""
        self.pending = None
        try:
            settings = self.read()
            check_ranges(self.config_path, settings)
        except ValueError as exc:
            self.show_message(friendly(str(exc)), "Error")
            return False
        if settings == self.settings and self.config_path.exists() and not self.load_error:
            self.show_message("")
            return True
        if mtime(self.config_path) != self.saved_mtime and not messagebox.askyesno(
                "Idle Runner", f"{self.config_path.name} changed outside this window. Replace those changes with "
                               "the settings shown here?\n\n(No: close the window and open it again to see them.)"):
            return False
        self.config_path.write_text(dump_settings(settings), encoding="utf-8")
        self.saved_mtime, self.settings, self.load_error = mtime(self.config_path), settings, ""
        self.show_message("")
        self.on_saved(settings)
        return True

    def update_dependents(self) -> None:
        for key, field in FIELDS.items():
            if field.depends_on:
                on = bool(self.vars[field.depends_on].get())
                for box in self.inputs[key]:
                    for widget in box.winfo_children():
                        if isinstance(widget, ttk.Widget):
                            widget.state(["!disabled"] if on else ["disabled"])

    def show_message(self, text: str, kind: str = "Muted") -> None:
        self.message.configure(text=text, style=f"{kind}.TLabel" if text else "TLabel")
        if text:
            self.message.pack_configure(pady=(0, 10))

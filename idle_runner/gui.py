"""The Idle Runner window (`python -m idle_runner gui`): start and stop the bot, edit config.toml, follow
the log and mark problems.

The original had an AutoIt GUI in the same process. This one runs the bot as a child process
(`python -m idle_runner run`), so the window stays responsive and a bot crash can't take it down.
"""
import queue
import re
import signal
import subprocess
import sys
import threading
import tkinter as tk
from dataclasses import fields
from pathlib import Path
from tkinter import messagebox, ttk

from idle_runner.blackbox import mark
from idle_runner.config import SECTIONS, Settings, check_ranges, dump_settings, load_settings
from idle_runner.log import setup_logging
from idle_runner.process import self_command
from idle_runner.stats import summarize

EXAMPLE = Path(__file__).resolve().parents[1] / "config.example.toml"
MAX_LOG_LINES = 2000
TYPES = {field.name: field.type for field in fields(Settings)}


def hints(example: Path) -> dict[str, str]:
    """The comment after each key in config.example.toml (with its continuation lines), shown next to
    the key's field."""
    found: dict[str, str] = {}
    key = None
    for line in example.read_text(encoding="utf-8").splitlines():
        if m := re.match(r"(\w+)\s*=[^#]*#\s*(.+)", line):
            key = m[1]
            found[key] = m[2]
        elif key and (m := re.match(r"\s+#\s*(.+)", line)):
            found[key] += " " + m[1]
        else:
            key = None
    return found


class App:
    def __init__(self, root: tk.Tk, config_path: Path) -> None:
        self.root = root
        self.config_path = config_path
        self.bot: subprocess.Popen[str] | None = None
        self.lines: queue.Queue[str] = queue.Queue()  # the bot's output, filled by a reader thread
        self.vars: dict[str, tk.Variable] = {}
        self.loaded_mtime = config_path.stat().st_mtime if config_path.exists() else None
        settings = Settings()
        try:
            if config_path.exists():
                settings = load_settings(config_path)
        except ValueError as exc:
            messagebox.showerror("Idle Runner", f"{exc}\n\nShowing the defaults instead.")
        self.tree_order = settings.tree_order  # not editable here: kept as loaded when the form is saved

        root.title("Idle Runner")
        root.geometry("1000x640")
        bar = ttk.Frame(root, padding=6)
        bar.pack(fill="x")
        ttk.Button(bar, text="Start", command=self.start).pack(side="left")
        ttk.Button(bar, text="Stop", command=self.stop).pack(side="left", padx=4)
        ttk.Button(bar, text="Save settings", command=self.save).pack(side="left")
        ttk.Button(bar, text="Stats", command=self.show_stats).pack(side="left", padx=4)
        self.status = ttk.Label(bar, text="Stopped")
        self.status.pack(side="left", padx=12)

        tabs = ttk.Notebook(root)
        tabs.pack(fill="both", expand=True, padx=6)
        log_tab = ttk.Frame(tabs)
        tabs.add(log_tab, text="Log")
        self.log = tk.Text(log_tab, wrap="none", height=20)
        scroll = ttk.Scrollbar(log_tab, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)
        help_text = hints(EXAMPLE)
        for section in ("general", "minigames", "crafting", "debug", "game"):  # the most used first
            keys = SECTIONS[section]
            tab = ttk.Frame(tabs, padding=8)
            tabs.add(tab, text=section.capitalize())
            for row, key in enumerate(keys):
                value = getattr(settings, key)
                ttk.Label(tab, text=key.replace("_", " ").capitalize()).grid(row=row, column=0, sticky="w", pady=2)
                if TYPES[key] is bool:
                    var: tk.Variable = tk.BooleanVar(value=value)
                    ttk.Checkbutton(tab, variable=var).grid(row=row, column=1, sticky="w", padx=8)
                else:
                    var = tk.StringVar(value=str(value))
                    ttk.Entry(tab, textvariable=var, width=14).grid(row=row, column=1, sticky="w", padx=8)
                ttk.Label(tab, text=help_text.get(key, ""), foreground="gray", wraplength=560).grid(
                    row=row, column=2, sticky="w")
                self.vars[key] = var

        note_bar = ttk.Frame(root, padding=6)
        note_bar.pack(fill="x")
        ttk.Label(note_bar, text="Something went wrong?").pack(side="left")
        self.note = ttk.Entry(note_bar)
        self.note.pack(side="left", fill="x", expand=True, padx=6)
        self.note.bind("<Return>", lambda _: self.mark_problem())
        ttk.Button(note_bar, text="Mark problem", command=self.mark_problem).pack(side="left")

        root.protocol("WM_DELETE_WINDOW", self.close)
        self.show("Start the bot, then click the game window: it only plays while the game is focused.")
        root.after(200, self.poll)

    def read_form(self) -> Settings:
        values: dict[str, object] = {}
        for key, var in self.vars.items():
            kind = TYPES[key]
            try:
                values[key] = var.get() if kind is bool else kind(var.get().strip())
            except ValueError:
                raise ValueError(f"'{key}' must be a {kind.__name__}, got {var.get()!r}") from None
        return Settings(**values, tree_order=self.tree_order)

    def save(self) -> bool:
        try:
            settings = self.read_form()
            check_ranges(self.config_path, settings)
        except ValueError as exc:
            messagebox.showerror("Idle Runner", str(exc))
            return False
        mtime = self.config_path.stat().st_mtime if self.config_path.exists() else None
        if mtime != self.loaded_mtime and not messagebox.askyesno(
                "Idle Runner", f"{self.config_path} changed outside this window since it opened. Overwrite those "
                               "changes with the settings shown here?\n\n(No: close and reopen the window to see them.)"):
            return False
        self.config_path.write_text(dump_settings(settings), encoding="utf-8")
        self.loaded_mtime = self.config_path.stat().st_mtime
        if self.running():
            self.show("Settings saved; restart the bot to use them.")
        return True

    def running(self) -> bool:
        return self.bot is not None and self.bot.poll() is None

    def start(self) -> None:
        if self.running() or not self.save():
            return
        self.bot = subprocess.Popen(self_command("run", "--config", str(self.config_path)),
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=self.read_output, args=(self.bot,), daemon=True).start()

    def read_output(self, bot: subprocess.Popen[str]) -> None:
        assert bot.stdout is not None
        for line in bot.stdout:
            self.lines.put(line.rstrip("\n"))

    def stop(self) -> None:
        if self.running():
            assert self.bot is not None
            self.bot.send_signal(signal.SIGINT)  # like Ctrl+C: releases every held key

    def log_dir(self) -> Path:
        return Path(self.vars["log_dir"].get())

    def show_stats(self) -> None:
        self.show("\n".join(summarize(self.log_dir() / "events.jsonl")))

    def mark_problem(self) -> None:
        text = self.note.get().strip() or "(no description)"
        setup_logging(self.log_dir())
        folder = mark(self.log_dir(), text)
        self.note.delete(0, "end")
        self.show(f"Marked: {text} -> {folder}")

    def show(self, text: str) -> None:
        self.log.insert("end", text + "\n")
        excess = int(self.log.index("end-1c").split(".")[0]) - MAX_LOG_LINES
        if excess > 0:
            self.log.delete("1.0", f"{excess + 1}.0")
        self.log.see("end")

    def poll(self) -> None:
        while not self.lines.empty():
            self.show(self.lines.get())
        if self.running():
            self.status.configure(text="Running (pauses while the game isn't focused)")
        elif self.bot is not None:
            self.status.configure(text=f"Stopped (exit code {self.bot.returncode})")
        self.root.after(200, self.poll)

    def close(self) -> None:
        if self.running():
            assert self.bot is not None
            self.bot.send_signal(signal.SIGINT)
            try:
                self.bot.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.bot.kill()
        self.root.destroy()


def main(config_path: Path) -> int:
    root = tk.Tk()
    ttk.Style(root).theme_use("clam")
    App(root, config_path)
    root.mainloop()
    return 0

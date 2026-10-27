"""The Tree order page: which Ascension Tree nodes the bot buys, and in what order (`Settings.tree_order`)."""
import tkinter as tk
from collections.abc import Callable, Collection, Sequence
from tkinter import ttk

from idle_runner.tree_nodes import NODES, RECOMMENDED_ORDER


def move(order: tuple[str, ...], name: str, to: int) -> tuple[str, ...]:
    """`name` at index `to` (clamped to the list) with the others in their order."""
    if name not in order:
        return order
    rest = [n for n in order if n != name]
    rest.insert(max(0, min(to, len(rest))), name)
    return tuple(rest)


def include(order: tuple[str, ...], name: str) -> tuple[str, ...]:
    return order if name in order else (*order, name)


def exclude(order: tuple[str, ...], name: str) -> tuple[str, ...]:
    return tuple(n for n in order if n != name)


class TreePage(ttk.Frame):
    """Two lists: the nodes the bot buys, top to bottom (drag a row or use the arrows), and the rest.
    `on_change` gets the new order after every change the user makes."""

    def __init__(self, parent: tk.Misc, order: Sequence[str], on_change: Callable[[tuple[str, ...]], None]) -> None:
        super().__init__(parent)
        self.order = tuple(order)
        self.on_change = on_change
        self.bought: Collection[str] = ()
        self.search = tk.StringVar()
        self.search.trace_add("write", lambda *_: self.refresh())
        self._dragged = ""

        bar = ttk.Frame(self)
        ttk.Label(bar, text="Search").pack(side="left")
        ttk.Entry(bar, textvariable=self.search).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(bar, text="Reset to recommended", command=self.reset).pack(side="right")
        bar.pack(fill="x", pady=(0, 8))

        ttk.Label(self, text="Bought by the bot, in this order").pack(anchor="w")
        self.order_view = self._table(("#", "Node", "Cost (SP)", "Status"), 10)
        self.order_view.bind("<ButtonPress-1>", lambda e: setattr(self, "_dragged", self.order_view.identify_row(e.y)))
        self.order_view.bind("<ButtonRelease-1>", self._release)
        buttons = ttk.Frame(self)
        ttk.Button(buttons, text="↑", width=3, command=lambda: self.nudge(-1)).pack(side="left")
        ttk.Button(buttons, text="↓", width=3, command=lambda: self.nudge(+1)).pack(side="left", padx=4)
        ttk.Button(buttons, text="Remove", command=self.remove).pack(side="left")
        buttons.pack(anchor="w", pady=8)

        ttk.Label(self, text="Not bought by the bot").pack(anchor="w")
        self.rest_view = self._table(("Node", "Cost (SP)"), 5)
        self.rest_view.bind("<Double-1>", lambda e: self.add())
        ttk.Button(self, text="Add", command=self.add).pack(anchor="w", pady=8)
        self.refresh()

    def _table(self, columns: tuple[str, ...], height: int) -> ttk.Treeview:
        frame = ttk.Frame(self)
        view = ttk.Treeview(frame, columns=columns, show="headings", height=height, selectmode="browse")
        for column in columns:
            view.heading(column, text=column)
            view.column(column, width=60 if column == "#" else 150, anchor="e" if column in ("#", "Cost (SP)") else "w")
        scroll = ttk.Scrollbar(frame, command=view.yview)
        view.configure(yscrollcommand=scroll.set)
        view.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        frame.pack(fill="both", expand=True)
        return view

    def refresh(self) -> None:
        """Redraw both lists for the current order, bought set and search text."""
        wanted = self.search.get().strip().lower()
        selected = self.order_view.selection() + self.rest_view.selection()
        self.order_view.delete(*self.order_view.get_children())
        self.rest_view.delete(*self.rest_view.get_children())
        for place, name in enumerate(self.order, 1):
            if wanted in name.lower():
                status = "bought this run" if name in self.bought else ""
                self.order_view.insert("", "end", iid=name, values=(place, name, f"{NODES[name].cost:,}", status))
        for name, node in NODES.items():
            if name not in self.order and wanted in name.lower():
                self.rest_view.insert("", "end", iid=name, values=(name, f"{node.cost:,}"))
        for name in selected:
            for view in (self.order_view, self.rest_view):
                if view.exists(name):
                    view.selection_set(name)

    def set_order(self, order: Sequence[str]) -> None:
        """Show a new order (e.g. a reloaded config) without reporting it as a change."""
        self.order = tuple(order)
        self.refresh()

    def set_bought(self, names: Collection[str]) -> None:
        self.bought = names
        self.refresh()

    def _change(self, order: tuple[str, ...]) -> None:
        if order != self.order:
            self.order = order
            self.refresh()
            self.on_change(order)

    def drop(self, name: str, onto: str) -> None:
        """Dragging `name` onto the row `onto` puts it at that row's place."""
        if onto in self.order:
            self._change(move(self.order, name, self.order.index(onto)))

    def _release(self, event: tk.Event) -> None:
        target = self.order_view.identify_row(event.y)
        if self._dragged and target and target != self._dragged:
            self.drop(self._dragged, target)
        self._dragged = ""

    def nudge(self, step: int) -> None:
        """Move the selected node past the visible row above (-1) or below (+1) it."""
        selection = self.order_view.selection()
        if not selection:
            return
        rows = self.order_view.get_children()
        i = rows.index(selection[0]) + step
        if 0 <= i < len(rows):
            self.drop(selection[0], rows[i])

    def add(self) -> None:
        for name in self.rest_view.selection():
            self._change(include(self.order, name))

    def remove(self) -> None:
        for name in self.order_view.selection():
            self._change(exclude(self.order, name))

    def reset(self) -> None:
        self._change(RECOMMENDED_ORDER)

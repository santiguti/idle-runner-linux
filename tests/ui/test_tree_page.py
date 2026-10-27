

from idle_runner.tree_nodes import NODES, RECOMMENDED_ORDER
from idle_runner.ui.tree_page import TreePage, exclude, include, move


def test_move_puts_the_node_at_the_given_place() -> None:
    assert move(("a", "b", "c"), "c", 0) == ("c", "a", "b")
    assert move(("a", "b", "c"), "a", 1) == ("b", "a", "c")
    assert move(("a", "b", "c"), "b", 1) == ("a", "b", "c")


def test_move_clamps_an_index_out_of_range() -> None:
    assert move(("a", "b", "c"), "b", 99) == ("a", "c", "b")
    assert move(("a", "b", "c"), "b", -5) == ("b", "a", "c")


def test_move_ignores_a_node_that_is_not_listed() -> None:
    assert move(("a", "b"), "z", 0) == ("a", "b")


def test_exclude_then_include_puts_the_node_last() -> None:
    order = exclude(("a", "b", "c"), "a")
    assert order == ("b", "c")
    assert include(order, "a") == ("b", "c", "a")


def test_include_and_exclude_are_idempotent() -> None:
    assert include(("a", "b"), "a") == ("a", "b")
    assert exclude(("a", "b"), "z") == ("a", "b")



def rows(tree) -> list[str]:
    return list(tree.get_children())


def make_page(root, order=("Portals", "Green Ore", "Pink Ore")):
    changes: list[tuple[str, ...]] = []
    page = TreePage(root, order, changes.append)
    return page, changes


def test_the_page_lists_the_order_with_costs_and_the_rest_below(root) -> None:
    page, _ = make_page(root)

    assert rows(page.order_view) == ["Portals", "Green Ore", "Pink Ore"]
    assert page.order_view.item("Green Ore", "values") == ("2", "Green Ore", "35", "")
    assert rows(page.rest_view) == [n for n in NODES if n not in ("Portals", "Green Ore", "Pink Ore")]


def test_nodes_bought_this_run_are_marked(root) -> None:
    page, _ = make_page(root)
    page.set_bought({"Green Ore"})

    assert page.order_view.item("Green Ore", "values")[3] == "bought this run"
    assert page.order_view.item("Portals", "values")[3] == ""


def test_dropping_a_row_reorders_and_reports(root) -> None:
    page, changes = make_page(root)
    page.drop("Pink Ore", "Portals")

    assert rows(page.order_view) == ["Pink Ore", "Portals", "Green Ore"]
    assert changes == [("Pink Ore", "Portals", "Green Ore")]


def test_the_arrow_buttons_move_the_selection(root) -> None:
    page, changes = make_page(root)
    page.order_view.selection_set("Portals")
    page.nudge(+1)
    assert changes[-1] == ("Green Ore", "Portals", "Pink Ore")
    page.nudge(-1)
    page.nudge(-1)  # already first: nothing changes
    assert changes[-1] == ("Portals", "Green Ore", "Pink Ore") and len(changes) == 2
    assert page.order_view.selection() == ("Portals",)


def test_add_and_remove_move_nodes_between_the_lists(root) -> None:
    page, changes = make_page(root)
    page.rest_view.selection_set("Soul Gem")
    page.add()
    assert changes[-1] == ("Portals", "Green Ore", "Pink Ore", "Soul Gem")
    assert "Soul Gem" not in rows(page.rest_view)

    page.order_view.selection_set("Green Ore")
    page.remove()
    assert changes[-1] == ("Portals", "Pink Ore", "Soul Gem")
    assert "Green Ore" in rows(page.rest_view)


def test_search_filters_both_lists_and_keeps_the_real_position(root) -> None:
    page, _ = make_page(root)
    page.search.set("ore")

    assert rows(page.order_view) == ["Green Ore", "Pink Ore"]
    assert page.order_view.item("Pink Ore", "values")[0] == "3"
    assert all("ore" in n.lower() for n in rows(page.rest_view)) and rows(page.rest_view)


def test_moving_while_filtered_swaps_with_the_visible_neighbour(root) -> None:
    page, changes = make_page(root, ("Portals", "Green Ore", "Soul Gem", "Pink Ore"))
    page.search.set("ore")
    page.order_view.selection_set("Green Ore")
    page.nudge(+1)  # the next visible row is Pink Ore, past Soul Gem

    assert changes[-1] == ("Portals", "Soul Gem", "Pink Ore", "Green Ore")


def test_reset_restores_the_recommended_order(root) -> None:
    page, changes = make_page(root)
    page.reset()

    assert changes[-1] == RECOMMENDED_ORDER and rows(page.order_view) == list(RECOMMENDED_ORDER)
    # Only the nodes surveyed outside the wiki's order (2026-10-26) are left out.
    assert set(rows(page.rest_view)) == set(NODES) - set(RECOMMENDED_ORDER) != set()


def test_set_order_refreshes_without_reporting(root) -> None:
    page, changes = make_page(root)
    page.set_order(("Soul Gem",))

    assert rows(page.order_view) == ["Soul Gem"] and changes == []

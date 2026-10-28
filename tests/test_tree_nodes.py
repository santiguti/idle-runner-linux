from idle_runner.tree_nodes import NODES, RECOMMENDED_ORDER


def test_recommended_order_names_known_nodes_once() -> None:
    assert set(RECOMMENDED_ORDER) <= set(NODES)
    assert len(set(RECOMMENDED_ORDER)) == len(RECOMMENDED_ORDER)


def test_the_user_order_of_98d31ce_comes_first() -> None:
    assert RECOMMENDED_ORDER[:11] == (
        "Village Key", "Idle Earrings I", "Idle Earrings II", "Blessing of Cronus", "Portals",
        "Green Ore", "Pink Ore", "Soul Gem", "Ancient Quests", "Hot Desert", "Portal Traveler")
    assert RECOMMENDED_ORDER[-1] == "Ultra Ascension"  # the node the bot never uses comes last


def test_node_points_and_costs() -> None:
    assert NODES["Village Key"].point == (118, 213) and NODES["Village Key"].cost == 3
    assert NODES["Master Chest Souls"].cost == 150_000_000  # "150 M"
    assert NODES["Bonus Stage 2"].cost == 5_000
    # Map: the green ring at client (69, 141) in the bot's "top" layout (black box 2026-10-28 00:45:11), the
    # icon of Santi's screenshot; the wiki's tier list puts it between Dark Wizard and Ethereal Wand.
    assert NODES["Map"] == ((77, 172), 150, "top")
    assert RECOMMENDED_ORDER.index("Map") == RECOMMENDED_ORDER.index("Dark Wizard") + 1
    assert len({node.point for node in NODES.values()}) == len(NODES)  # two nodes never share a click point

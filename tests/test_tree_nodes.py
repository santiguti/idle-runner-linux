from idle_runner.tree_nodes import NODES, RECOMMENDED_ORDER


def test_recommended_order_names_known_nodes_once() -> None:
    assert set(RECOMMENDED_ORDER) <= set(NODES)
    assert len(set(RECOMMENDED_ORDER)) == len(RECOMMENDED_ORDER)


def test_the_user_order_of_98d31ce_comes_first() -> None:
    assert RECOMMENDED_ORDER[:9] == (
        "Village Key", "Idle Earrings I", "Idle Earrings II", "Blessing of Cronus", "Portals",
        "Green Ore", "Pink Ore", "Soul Gem", "Portal Traveler")
    assert RECOMMENDED_ORDER[-1] == "Ultra Ascension"  # the node the bot never uses comes last


def test_node_points_and_costs() -> None:
    assert NODES["Village Key"].point == (118, 213) and NODES["Village Key"].cost == 3
    assert NODES["Master Chest Souls"].cost == 150_000_000  # "150 M"
    assert NODES["Bonus Stage 2"].cost == 5_000
    assert len({node.point for node in NODES.values()}) == len(NODES)  # two nodes never share a click point

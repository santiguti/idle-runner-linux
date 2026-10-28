import ast
import re
import string
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from idle_runner.blackbox import ANOMALIES
from idle_runner.config import Settings, check_ranges
from idle_runner.game_settings import SETTINGS
from idle_runner.ui import app, i18n, tree_page
from idle_runner.ui.activity import DOING, MINIGAMES
from idle_runner.ui.fields import CARDS, FIELDS
from idle_runner.ui.i18n import SPANISH, set_language, system_language, t

UI = Path(i18n.__file__).parent


@pytest.fixture
def spanish():
    set_language("es")
    yield
    set_language("en")


@pytest.mark.skipif(sys.platform == "win32", reason="Windows asks the system, not the environment")
@pytest.mark.parametrize(("environment", "language"), [
    ({"LANG": "es_AR.UTF-8"}, "es"), ({"LANG": "en_US.UTF-8"}, "en"), ({"LANG": "C"}, "en"), ({}, "en"),
    ({"LANGUAGE": "es_ES:en", "LANG": "en_US.UTF-8"}, "es"), ({"LC_ALL": "en_GB.UTF-8", "LANG": "es_MX.UTF-8"}, "en"),
])
def test_the_system_language_comes_from_the_environment(monkeypatch, environment: dict, language: str) -> None:
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(name, raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)

    assert system_language() == language


def test_english_is_the_text_itself_and_spanish_falls_back_to_it(spanish) -> None:
    assert t("Start") == "Iniciar"
    assert t("Version {version}", version="2.2.0") == "Versión 2.2.0"
    assert t("Something new") == "Something new"
    set_language("en")
    assert t("Start") == "Start"
    assert t("Version {version}", version="2.2.0") == "Version 2.2.0"


def shown_texts() -> set[str]:
    """Every English text the window can show: the literal t("...") calls in idle_runner/ui and the texts the
    window passes to t from tables."""
    texts = set()
    for path in UI.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "t"
                    and node.args and isinstance(node.args[0], ast.Constant)):
                texts.add(node.args[0].value)
    for field in FIELDS.values():
        texts |= {field.label, field.help, field.warning, field.card}
    texts |= {unit for field in FIELDS.values() for unit in [field.unit] if unit.isalpha() and unit != "ms"}
    texts |= set(CARDS) | set(app.PAGES) | set(app.FILTERS) | set(app.STATS) | {app.SETUP, app.SAFETY}
    texts |= set(DOING.values()) | set(MINIGAMES.values()) | set(ANOMALIES) | set(SETTINGS)
    texts |= set(tree_page.ORDER_COLUMNS + tree_page.REST_COLUMNS) - {"#"}
    try:  # every range rule broken at once: each message on its own
        check_ranges(Path("config.toml"), replace(Settings(), jump_interval_ms=-1, circle_portals_count=0,
                     auto_buy_minutes=0, ascend_bonus_sample_minutes=-1, auto_ascend_percent=-1,
                     post_ascend_first_buy_seconds=-1, color_tolerance=-1, log_level="x", blackbox_fps=-1,
                     blackbox_minutes=0, language="fr"))
    except ValueError as exc:
        texts |= set(str(exc).split(": ", 1)[1].split("; "))
    return texts - {""}


def test_every_text_the_window_shows_has_a_spanish_version() -> None:
    assert sorted(shown_texts() - set(SPANISH)) == []


def test_spanish_texts_keep_their_fields() -> None:
    def fields(text: str) -> set[str]:
        return {name for _, name, _, _ in string.Formatter().parse(text) if name}

    assert [english for english, spanish in SPANISH.items() if fields(english) != fields(spanish)] == []


def test_the_window_names_the_game_settings_with_the_game_s_spanish_words(spanish) -> None:
    # Measured in the game in Spanish, 2026-10-28 (game_settings.SETTINGS).
    assert t("Rounded bulk buy") == "Compra masiva redondeada"
    assert re.search(r"Compra masiva redondeada", t(app.SETUP))


def test_every_tree_node_has_the_game_s_spanish_name(spanish) -> None:
    # Read from each node's modal with the game in Spanish (2026-10-28).
    from idle_runner.tree_nodes import NODES
    from idle_runner.ui.i18n import NODES_ES, node_name

    assert sorted(set(NODES) - set(NODES_ES)) == []
    assert node_name("Minions") == "Súbditos"
    set_language("en")
    assert node_name("Minions") == "Minions"


def test_the_tree_page_and_the_feed_use_the_spanish_node_names(spanish, root) -> None:
    from idle_runner.ui.activity import describe
    from idle_runner.ui.tree_page import TreePage

    page = TreePage(root, ("Village Key", "Portals"), lambda order: None)
    assert page.order_view.item("Village Key", "values")[1] == "Llave de la Aldea"
    page.search.set("aldea")
    assert page.order_view.get_children() == ("Village Key",)
    assert describe({"event": "Tree node bought", "node": "Portals"}) == ("tree", "Árbol: compró Portales")

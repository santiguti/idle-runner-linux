import pytest

from idle_runner.ui.theme import PALETTE, contrast


@pytest.mark.parametrize(("fg", "bg"), [
    (PALETTE.text, PALETTE.bg), (PALETTE.text, PALETTE.surface), (PALETTE.text, PALETTE.raised),
    (PALETTE.muted, PALETTE.bg), (PALETTE.muted, PALETTE.surface), (PALETTE.accent, PALETTE.surface),
    (PALETTE.gold, PALETTE.surface), ("#FFFFFF", PALETTE.ok), ("#FFFFFF", PALETTE.danger),
    (PALETTE.warning, PALETTE.surface), (PALETTE.danger_text, PALETTE.surface), (PALETTE.on_gold, PALETTE.gold),
])
def test_text_colours_are_readable(fg: str, bg: str) -> None:
    assert contrast(fg, bg) >= 4.5


def test_contrast_of_black_on_white_is_21() -> None:
    assert round(contrast("#000000", "#FFFFFF"), 1) == 21.0

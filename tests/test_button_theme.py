"""No Qt dependency: ensure all tactile button states have CSS selectors."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.ui.button_theme import BUTTON_STYLE


def test_button_states_defined():
    for selector in ("QPushButton {", "QPushButton:hover", "QPushButton:pressed",
                     "QPushButton:focus", "QPushButton:disabled",
                     "QPushButton#primary", "QPushButton#primary:pressed",
                     "QPushButton#primary:disabled", "QPushButton#danger",
                     "QPushButton#danger:pressed", "QPushButton#danger:disabled"):
        assert selector in BUTTON_STYLE


def test_tactile_depth_and_no_expensive_effects():
    assert "border-bottom: 3px solid" in BUTTON_STYLE
    assert "border-bottom: 1px solid" in BUTTON_STYLE
    assert "border-top: 3px solid" in BUTTON_STYLE
    assert "padding-top: 9px" in BUTTON_STYLE
    assert "padding-bottom: 5px" in BUTTON_STYLE
    assert "linear-gradient" not in BUTTON_STYLE
    assert "animation" not in BUTTON_STYLE

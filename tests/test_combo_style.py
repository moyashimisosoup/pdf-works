"""Lightweight, Qt-free checks for common dropdown design tokens."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "src" / "pdf_works" / "ui"


def test_both_selectors_use_soft_combo():
    text = (ROOT / "main_window.py").read_text(encoding="utf-8")
    assert "self.zoom_combo=SoftComboBox()" in text
    assert "self.font_combo = SoftComboBox()" in text


def test_dropdown_states_and_no_remote_resources():
    from importlib.util import module_from_spec, spec_from_file_location
    path = ROOT / "theme.py"
    spec = spec_from_file_location("ui_theme_tokens", path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    css = module.COMBO_STYLE
    for selector in ("QComboBox#softCombo {", ":hover", ":on", ":focus",
                     ":disabled", "::drop-down", "::down-arrow", "QAbstractItemView"):
        assert selector in css
    assert "http://" not in css and "https://" not in css


def test_popup_delegate_and_keyboard_preserved():
    text = (ROOT / "widgets" / "combo_box.py").read_text(encoding="utf-8")
    assert "class SoftComboBox(QComboBox)" in text
    assert "class SoftItemDelegate(QStyledItemDelegate)" in text
    assert "super().showPopup()" in text
    assert "setMaxVisibleItems(8)" in text
    assert "setFocusPolicy" in text
    assert "QPolygonF" in text

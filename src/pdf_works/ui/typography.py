"""Compact, predictable Qt typography for the Soft Outline UI.

Font files are installed once with scripts/install_fonts.py, then loaded locally.
No startup network traffic and no Windows-wide font installation are required.
"""
from __future__ import annotations

from pathlib import Path
from PySide6.QtGui import QFont, QFontDatabase

PRESETS = {
    "gentle": "やわらか 400",
    "standard": "標準 500",
    "clear": "くっきり 700",
}
WEIGHTS = {
    "gentle": QFont.Weight.Normal,
    "standard": QFont.Weight.Medium,
    "clear": QFont.Weight.Bold,
}
LOCAL_FONTS = (
    "ZenMaruGothic-Regular.ttf",
    "ZenMaruGothic-Medium.ttf",
    "ZenMaruGothic-Bold.ttf",
)
FONT_DIR = Path(__file__).resolve().parents[1] / "resources" / "fonts"
_loaded_family: str | None = None
_loaded_files: set[str] = set()


def load_local_fonts(preset: str = "standard") -> bool:
    """Register only the selected weight; other weights load on first use."""
    global _loaded_family
    filenames = dict(zip(PRESETS, LOCAL_FONTS))
    name = filenames.get(preset, filenames["standard"])
    # PRESETS ordering: gentle=Regular, standard=Medium, clear=Bold.
    if name in _loaded_files:
        return True
    path = FONT_DIR / name
    if not path.is_file():
        return False
    font_id = QFontDatabase.addApplicationFont(str(path))
    if font_id == -1:
        return False
    families = QFontDatabase.applicationFontFamilies(font_id)
    if not families:
        return False
    _loaded_family = families[0]
    _loaded_files.add(name)
    return True


def font_status() -> dict[str, object]:
    return {
        "embedded": _loaded_family is not None,
        "complete": all((FONT_DIR / name).is_file() for name in LOCAL_FONTS),
        "family": _loaded_family or "",
        "loaded_weights": len(_loaded_files),
    }


def _fallback_font_family() -> str:
    installed = set(QFontDatabase.families())
    # Readability takes priority over forcing a not-present aesthetic font.
    for family in ("BIZ UDPGothic", "Yu Gothic UI", "Meiryo", "Noto Sans CJK JP"):
        if family in installed:
            return family
    return QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()


def font_for_preset(preset: str) -> QFont:
    if preset not in WEIGHTS:
        preset = "standard"
    load_local_fonts(preset)
    family = _loaded_family or _fallback_font_family()
    font = QFont(family)
    font.setPointSize(11)
    font.setWeight(WEIGHTS[preset])
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font

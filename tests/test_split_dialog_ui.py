"""Qt group splitting dialog: preview, invalid cuts, confirmed parameters."""
import os
import sys
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QDialogButtonBox
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdf_works.ui.split_dialog import SplitGroupsDialog


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_group_by_five_for_forty_pages(app):
    dialog = SplitGroupsDialog([(i,0) for i in range(40)])
    assert dialog.size.value() == 5
    assert "8ファイル" in dialog.info.text()
    assert dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    dialog._accept_config()
    assert dialog.configuration == {"mode":"fixed", "size":5, "boundaries":None}


def test_explicit_boundaries_live_preview(app):
    dialog = SplitGroupsDialog([(i,0) for i in range(10)])
    dialog.mode.setCurrentIndex(1)
    dialog.boundaries.setText("3、7")
    assert "3ファイル" in dialog.info.text()
    assert "3 / 4 / 3" in dialog.info.text()
    dialog._accept_config()
    assert dialog.configuration == {
        "mode":"boundaries", "size":None, "boundaries":[3,7]
    }


@pytest.mark.parametrize("bad", ["", "0", "10", "4, 4", "8, 3", "a, b", "1,,2"])
def test_reject_invalid_boundaries(app, bad):
    dialog = SplitGroupsDialog([(i, 0) for i in range(10)])
    dialog.mode.setCurrentIndex(1)
    dialog.boundaries.setText(bad)
    assert not dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()


def test_one_page_disables_group_splitting(app):
    dialog = SplitGroupsDialog([(0, 0)])
    assert not dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()

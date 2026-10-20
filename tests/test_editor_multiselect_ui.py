"""Standard Windows-style Qt multi-page selection and batch controls."""
from __future__ import annotations

import os
from pathlib import Path
import sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt, QItemSelectionModel
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdf_works.core.page_edit import EditSession
from pdf_works.ui.editor_window import EditWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def editor(app, monkeypatch):
    monkeypatch.setattr(EditWindow, "_start_worker", lambda self: None)
    window = EditWindow()
    window.resize(1150, 790)
    window._session = EditSession(8)
    window._source_sizes = [(595.,842.)] * 8
    window._saved_snapshot = window._session.snapshot()
    window._refresh_pages(0)
    window.show()
    app.processEvents()
    yield window
    window.close()
    app.processEvents()


def row_position(window, row):
    item = window.page_list.item(row)
    window.page_list.scrollToItem(item)
    QApplication.processEvents()
    rect = window.page_list.visualItemRect(item)
    assert rect.isValid(), row
    return rect.center()


def test_ctrl_click_shift_range_and_one_undo(editor):
    page_list = editor.page_list
    assert editor._selected_rows() == [0]
    page_list.setFocus()
    QTest.mouseClick(
        page_list.viewport(), Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ControlModifier, pos=row_position(editor, 2),
    )
    QApplication.processEvents()
    assert editor._selected_rows() == [0, 2]
    assert editor._current_page == 2
    QTest.mouseClick(
        page_list.viewport(), Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ShiftModifier, pos=row_position(editor, 3),
    )
    QApplication.processEvents()
    assert editor._selected_rows() == [2, 3]
    editor._edit(("rotate", 90))
    assert editor._session.pages[2].rotation_delta == 90
    assert editor._session.pages[3].rotation_delta == 90
    assert editor._selected_rows() == [2, 3]
    assert editor._session.can_undo
    editor._edit(("undo",))
    assert not editor._session.can_undo
    assert all(page.rotation_delta == 0 for page in editor._session.pages)


def test_ctrl_a_disable_all_page_delete_and_safe_batch_delete(editor, monkeypatch):
    page_list = editor.page_list
    page_list.setFocus()
    QTest.keyClick(page_list, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    QApplication.processEvents()
    assert len(editor._selected_rows()) == 8
    assert not editor._edit_buttons["delete"].isEnabled()
    # Recreate a noncontiguous selection without depending on scroll geometry.
    page_list.clearSelection()
    for index in (1, 4, 6):
        page_list.item(index).setSelected(True)
    assert editor._selected_rows() == [1, 4, 6]
    monkeypatch.setattr(
        QMessageBox, "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    editor._edit(("delete",))
    assert [p.source_index for p in editor._session.pages] == [0, 2, 3, 5, 7]
    editor._edit(("undo",))
    assert [p.source_index for p in editor._session.pages] == list(range(8))


def test_navigation_buttons_replace_selection(editor):
    editor.page_list.item(2).setSelected(True)
    editor._select_page(4)
    assert editor._selected_rows() == [4]
    assert editor._current_page == 4

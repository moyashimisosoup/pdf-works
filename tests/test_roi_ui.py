"""Qt ROI mouse interaction and page-relative persistence.

Offscreen Qt test on Windows CI. No worker, real PDFs or network requests.
"""
import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdf_works.ui.viewer import PdfViewer


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_drag_roi_normalized_and_cleared(app):
    view = PdfViewer()
    view.resize(600, 550)
    view.set_page(300, 400)
    view.show()
    app.processEvents()
    assert view.roi is None
    view.enable_roi_selection(True)
    start = view.mapFromScene(QPointF(30, 40))
    end = view.mapFromScene(QPointF(150, 180))
    assert view.viewport().rect().contains(start)
    assert view.viewport().rect().contains(end)
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(view.viewport(), pos=end)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=end)
    app.processEvents()
    assert view.roi is not None
    left, top, right, bottom = view.roi
    assert abs(left - .1) < .02
    assert abs(top - .1) < .02
    assert abs(right - .5) < .02
    assert abs(bottom - .45) < .02

    view.set_zoom(1.5)
    view.set_page(500, 400)
    assert view.roi == (left, top, right, bottom)
    assert view._roi_item is not None
    assert abs(view._roi_item.rect().width() - (right - left) * 500) < 1
    view.enable_roi_selection(False)
    view.clear_roi()
    assert view.roi is None
    assert view._roi_item is None
    view.close()


def test_no_drag_mode_does_not_create_roi(app):
    view = PdfViewer()
    view.resize(600, 550)
    view.set_page(300, 400)
    view.show()
    app.processEvents()
    assert view.dragMode() == view.DragMode.ScrollHandDrag
    view.enable_roi_selection(True)
    assert view.dragMode() == view.DragMode.NoDrag
    view.enable_roi_selection(False)
    assert view.dragMode() == view.DragMode.ScrollHandDrag
    view.reset_document()
    assert view.roi is None
    view.close()

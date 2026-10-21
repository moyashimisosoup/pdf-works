"""Qt gallery with 40 artificial PNGs, offscreen and no PDF IO."""
from __future__ import annotations

import os
from pathlib import Path
import sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.ui.roi_gallery import CropGallery, MAX_PENDING, THUMB_LIMIT


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def gallery_files(tmp_path):
    files = []
    for i in range(40):
        path = tmp_path / f"sample_{i:02d}.png"
        picture = QImage(240, 160, QImage.Format.Format_RGB32)
        picture.fill(QColor("#ECE8F3") if i % 2 else QColor("#E8F2F3"))
        assert picture.save(str(path))
        files.append(path)
    return files


def wait_for(app, pred, ms=3000):
    for _ in range(ms // 50):
        app.processEvents()
        if pred():
            return
        QTest.qWait(50)
    assert pred(), "Qt gallery image loading timed out"


def test_gallery_40_pages_visible_only_and_preview(app, gallery_files):
    gallery = CropGallery(gallery_files, list(range(40)))
    gallery.resize(940, 660)
    gallery.show()
    wait_for(app, lambda: bool(gallery._loaded) and not gallery._preview_image.isNull())
    assert gallery.items.count() == 40
    assert len(gallery._loaded) <= THUMB_LIMIT
    assert len(gallery._loaded) < 40  # no eager full-page image collection
    assert len(gallery._pending) <= MAX_PENDING
    assert not gallery.preview.pixmap().isNull()
    gallery.size_combo.setCurrentIndex(0)
    assert gallery.items.iconSize().width() == 96
    gallery.size_combo.setCurrentIndex(2)
    assert gallery.items.iconSize().width() == 184
    gallery.close()
    app.processEvents()


def test_gallery_source_signal_uses_original_source_id(app, gallery_files):
    sources = [39 - i for i in range(40)]
    gallery = CropGallery(gallery_files, sources)
    gallery.show()
    app.processEvents()
    spy = QSignalSpy(gallery.source_requested)
    gallery.items.setCurrentRow(2)
    app.processEvents()
    item = gallery.items.item(2)
    gallery.items.itemDoubleClicked.emit(item)
    assert spy.count() == 1
    assert spy.at(0)[0] == 37
    gallery.close()
    app.processEvents()


def test_gallery_rejects_bad_lengths(app, gallery_files):
    with pytest.raises(ValueError):
        CropGallery([], [])
    with pytest.raises(ValueError):
        CropGallery(gallery_files, [0])


def test_gallery_pdf_button_requests_save(app, gallery_files):
    gallery = CropGallery(gallery_files[:2], [7, 3])
    gallery.show()
    app.processEvents()
    spy = QSignalSpy(gallery.pdf_requested)
    gallery.pdf_button.click()
    app.processEvents()
    assert spy.count() == 1
    gallery.close()
    app.processEvents()


def test_gallery_order_exclusion_and_restore_are_reversible(app, gallery_files):
    gallery = CropGallery(gallery_files[:4], [10, 11, 12, 13])
    spy = QSignalSpy(gallery.layout_changed)
    gallery.show()
    app.processEvents()
    gallery.items.setCurrentRow(1)
    gallery.up_button.click()
    files, sources = gallery.export_entries()
    assert sources == [11, 10, 12, 13]
    assert files[0] == str(gallery_files[1])
    assert gallery.items.item(0).data(Qt.ItemDataRole.UserRole) == 1
    gallery.exclude_button.click()
    files, sources = gallery.export_entries()
    assert sources == [10, 12, 13]
    assert "除外" in gallery.items.item(0).text()
    assert spy.count() == 2
    assert spy.at(1)[0] == [1, 0, 2, 3]
    assert spy.at(1)[1] == [1]
    gallery.items.setCurrentRow(1)
    gallery.down_button.click()
    assert gallery.export_entries()[1] == [12, 10, 13]
    gallery.restore_button.click()
    assert gallery.export_entries()[1] == [11, 12, 10, 13]
    assert gallery.pdf_button.isEnabled()
    gallery.close()
    app.processEvents()


def test_all_excluded_disables_pdf_but_can_restore(app, gallery_files):
    gallery = CropGallery(gallery_files[:2], [3, 9])
    gallery.show()
    app.processEvents()
    gallery.items.setCurrentRow(0)
    gallery.exclude_button.click()
    gallery.items.setCurrentRow(1)
    gallery.exclude_button.click()
    assert gallery.export_entries() == ([], [])
    assert not gallery.pdf_button.isEnabled()
    gallery.restore_button.click()
    assert gallery.export_entries()[1] == [3, 9]
    assert gallery.pdf_button.isEnabled()
    gallery.close()
    app.processEvents()


def test_reopened_gallery_recovers_order_and_exclusions(app, gallery_files):
    gallery = CropGallery(
        gallery_files[:3], [7, 4, 8],
        order=[2, 0, 1], excluded=[0],
    )
    gallery.show()
    app.processEvents()
    assert gallery.export_entries()[1] == [8, 4]
    assert "除外" in gallery.items.item(1).text()
    gallery.items.setCurrentRow(0)
    spy = QSignalSpy(gallery.source_requested)
    gallery.items.itemDoubleClicked.emit(gallery.items.item(0))
    assert spy.count() == 1 and spy.at(0)[0] == 8
    gallery.close()
    app.processEvents()

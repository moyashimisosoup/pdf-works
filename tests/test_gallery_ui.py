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

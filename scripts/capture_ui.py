"""Capture real Qt widget pixels on Windows CI, with synthetic PDF content.

This is a *CI-hosted preview*, NOT a screenshot of the user's own desktop.
The PDF worker is intentionally disabled so this checks only UI rendering.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import fitz
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from pdf_works.core.page_edit import EditSession
from pdf_works.ui.editor_window import EditWindow
from pdf_works.ui.main_window import rgb_to_pixmap


def capture(output: Path, pdf_path: Path) -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")  # Match pdf_works.__main__ on Windows.
    # Keep the screenshot deterministic and prevent spawned render worker I/O.
    EditWindow._start_worker = lambda self: None

    window = EditWindow()
    window.resize(1180, 790)
    with fitz.open(pdf_path) as pdf:
        sizes = [(float(page.rect.width), float(page.rect.height)) for page in pdf]
        source_page = pdf[0]
        pix = source_page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
        page_image = {
            "width": pix.width,
            "height": pix.height,
            "stride": pix.stride,
            "samples": bytes(pix.samples),
        }

    window._pdf_path = str(pdf_path)
    window._source_sizes = sizes
    window._session = EditSession(len(sizes))
    window._saved_snapshot = window._session.snapshot()
    window.filename.setText("sample_40.pdf")
    window._refresh_pages(0)
    window.viewer.show_image(rgb_to_pixmap(page_image), 0, 0, 1)
    window.statusBar().showMessage("40ページの人工PDFを表示中 · Qt / Windows CIプレビュー")
    window.show()
    app.processEvents()

    output.mkdir(parents=True, exist_ok=True)
    regular = output / "pdf-works-qt-normal.png"
    if not window.grab().save(str(regular)):
        raise RuntimeError("Failed to save normal-state Qt screenshot")

    # Depressed state without clicking or triggering actual file dialogs.
    window.open_button.setDown(True)
    window.save_button.setDown(True)
    window._edit_buttons["right"].setDown(True)
    app.processEvents()
    pressed = output / "pdf-works-qt-pressed.png"
    if not window.grab().save(str(pressed)):
        raise RuntimeError("Failed to save pressed-state Qt screenshot")

    if regular.read_bytes() == pressed.read_bytes():
        raise RuntimeError("Qt pressed state produced no visible screenshot change")

    window.open_button.setDown(False)
    window.save_button.setDown(False)
    window._edit_buttons["right"].setDown(False)
    app.processEvents()

    # Draw the normalized rectangle using an actual Qt viewport mouse drag.
    # This is the same widget interaction used in the Windows version.
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtTest import QTest
    window.roi_toggle.setChecked(True)
    start = window.viewer.mapFromScene(QPointF(65, 80))
    end = window.viewer.mapFromScene(QPointF(260, 245))
    QTest.mousePress(window.viewer.viewport(), Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(window.viewer.viewport(), pos=end)
    QTest.mouseRelease(window.viewer.viewport(), Qt.MouseButton.LeftButton, pos=end)
    app.processEvents()
    if window.viewer.roi is None or not window.roi_export.isEnabled():
        raise RuntimeError("ROI drag failed or PNG export button remains disabled")
    roi_screenshot = output / "pdf-works-qt-roi-selected.png"
    if not window.grab().save(str(roi_screenshot)):
        raise RuntimeError("Failed to save selected ROI screenshot")
    if roi_screenshot.read_bytes() == regular.read_bytes():
        raise RuntimeError("ROI selection was not visible")
    window.roi_toggle.setChecked(False)

    # Multi-page Qt list selection: keep current page and selected set distinct.
    from PySide6.QtCore import QItemSelectionModel
    window.page_list.setCurrentRow(
        0, QItemSelectionModel.SelectionFlag.ClearAndSelect
    )
    window.page_list.item(2).setSelected(True)
    app.processEvents()
    if window._selected_rows() != [0, 2]:
        raise RuntimeError("Extended selection does not preserve two pages")
    selected_capture = output / "pdf-works-qt-multi-selection.png"
    if not window.grab().save(str(selected_capture)):
        raise RuntimeError("Failed to capture multi-page selection")
    window.page_list.setCurrentRow(
        0, QItemSelectionModel.SelectionFlag.ClearAndSelect
    )
    app.processEvents()

    # The combobox popup is a separate top-level Qt window. Grab that window,
    # otherwise the main-window capture would not include the expanded choices.
    dropdown_path = output / "pdf-works-qt-dropdown-open.png"
    combo = window.font_combo
    start_selection = combo.currentIndex()
    combo.showPopup()
    app.processEvents()
    popup = combo.view().window()
    if not combo.view().isVisible() or popup.width() < 120 or popup.height() < 40:
        raise RuntimeError("Soft Outline dropdown popup failed to open")
    if not popup.grab().save(str(dropdown_path)):
        raise RuntimeError("Failed to save expanded dropdown screenshot")
    combo.hidePopup()
    app.processEvents()
    if combo.currentIndex() != start_selection:
        raise RuntimeError("Simply opening a dropdown changed its selection")

    # The separate gallery shows 40 artificial snippets. No worker needed.
    thumbnails = output / "artificial-gallery-pngs"
    thumbnails.mkdir(exist_ok=True)
    files = []
    for idx in range(40):
        path = thumbnails / f"item_{idx:02d}.png"
        qimg = QImage(250, 160, QImage.Format.Format_RGB32)
        qimg.fill(QColor("#E8F2F3") if idx % 2 == 0 else QColor("#F0ECF4"))
        painter = QPainter(qimg)
        painter.setPen(QColor("#351F39"))
        painter.drawText(qimg.rect(), Qt.AlignmentFlag.AlignCenter,
                         f"Sample {idx+1} / 40")
        painter.end()
        if not qimg.save(str(path)):
            raise RuntimeError("Failed to create artificial gallery file")
        files.append(path)
    window._gallery_files = [str(p) for p in files]
    window._gallery_sources = list(range(40))
    window._show_roi_gallery()
    from PySide6.QtTest import QTest
    gallery = window._gallery
    app.processEvents()
    gallery._request_visible()
    for _ in range(65):
        app.processEvents()
        if gallery._loaded:
            break
        QTest.qWait(100)
    if gallery.items.count() != 40 or not gallery._loaded:
        raise RuntimeError(
            "Lazy gallery did not load thumbnails: "
            f"count={gallery.items.count()}, visible={gallery.isVisible()}, "
            f"viewport={gallery.items.viewport().rect()}, "
            f"pending={list(gallery._pending)}, "
            f"preview_index={gallery._preview_index}"
        )
    gallery_capture = output / "pdf-works-qt-crop-gallery.png"
    if not gallery.grab().save(str(gallery_capture)):
        raise RuntimeError("Failed to capture ROI gallery screenshot")
    gallery.close()
    app.processEvents()

    print(f"Qt application client area and dropdown captured on {sys.platform}:")
    for f in (regular, pressed, roi_screenshot, selected_capture,
              dropdown_path, gallery_capture):
        print(f"  {f} ({f.stat().st_size} bytes)")
    window.close()


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/ui-screenshots")
    sample = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("tests/sample_40.pdf")
    capture(out, sample)

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
from PySide6.QtGui import QPixmap
from pdf_works.core.page_edit import EditSession
from pdf_works.ui.editor_window import EditWindow
from pdf_works.ui.main_window import rgb_to_pixmap


def capture(output: Path, pdf_path: Path) -> None:
    app = QApplication.instance() or QApplication(sys.argv)
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
    print(f"Qt application client area captured on {sys.platform}:")
    for f in (regular, pressed):
        print(f"  {f} ({f.stat().st_size} bytes)")
    window.close()


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/ui-screenshots")
    sample = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("tests/sample_40.pdf")
    capture(out, sample)

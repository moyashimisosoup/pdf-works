"""Offscreen Qt smoke: side-by-side/overlay, A-only transforms, export request."""
from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.ui.alignment_dialog import AlignmentDialog
from pdf_works.workers.bridge import PdfBridge


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_one_pair_dialog_controls_and_worker_payload(app, tmp_path, monkeypatch):
    monkeypatch.setattr(PdfBridge, "start", lambda self: None)
    dialog = AlignmentDialog()
    dialog.show()
    app.processEvents()
    try:
        assert not dialog.save_button.isEnabled()
        dialog._source = tmp_path / "answer.pdf"
        dialog._reference = tmp_path / "reference.pdf"
        dialog._preview_request = 11
        a = bytes([225, 70, 60] * 12)
        b = bytes([240, 240, 245] * 20)
        dialog._receive({
            "id": 11, "op": "align_preview", "status": "ok",
            "source_pages": 2, "reference_pages": 1,
            "source_size": (300, 400), "reference_size": (310, 430),
            "images": {
                "a": {"width": 3, "height": 4, "stride": 9, "samples": a},
                "b": {"width": 4, "height": 5, "stride": 12, "samples": b},
            },
        })
        assert dialog.save_button.isEnabled()
        assert "全2ページ" in dialog.page_info.text()
        dialog.mode.setCurrentIndex(1)
        dialog.opacity.setValue(65)
        dialog.scale.setValue(102.5)
        dialog.x_offset.setValue(1.5)
        dialog.y_offset.setValue(-2.0)
        dialog._redraw()
        assert dialog.display.currentIndex() == 1
        assert not dialog.overlay_preview.pixmap().isNull()
        target = tmp_path / "output.pdf"
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            lambda *args: (str(target), "PDF (*.pdf)"),
        )
        requests = []
        monkeypatch.setattr(
            dialog._bridge, "send",
            lambda op, **kw: requests.append((op, kw)) or 31,
        )
        dialog._save()
        assert requests[0][0] == "align_export"
        assert requests[0][1]["source"] == str(dialog._source)
        assert requests[0][1]["reference"] == str(dialog._reference)
        assert requests[0][1]["percent"] == 102.5
        assert requests[0][1]["x_mm"] == 1.5
        assert requests[0][1]["y_mm"] == -2.0
        assert dialog._exporting
        monkeypatch.setattr(
            QMessageBox, "information", lambda *args: QMessageBox.StandardButton.Ok,
        )
        dialog._receive({
            "id": 31, "op": "align_export", "status": "ok",
            "destination": str(target), "pages": 2,
        })
        assert not dialog._exporting
        assert dialog.save_button.isEnabled()
    finally:
        dialog._exporting = False
        dialog.close()
        app.processEvents()


def test_form_preview_requires_explicit_visual_only_consent(app, monkeypatch, tmp_path):
    monkeypatch.setattr(PdfBridge, "start", lambda self: None)
    dialog = AlignmentDialog()
    dialog.show()
    app.processEvents()
    try:
        dialog._source = tmp_path / "form.pdf"
        dialog._reference = tmp_path / "reference.pdf"
        a = bytes([225, 70, 60] * 12)
        b = bytes([240, 240, 245] * 20)
        response = {
            "op": "align_preview", "status": "ok",
            "source_pages": 1, "reference_pages": 1,
            "source_size": (300, 400), "reference_size": (310, 430),
            "images": {
                "a": {"width": 3, "height": 4, "stride": 9, "samples": a},
                "b": {"width": 4, "height": 5, "stride": 12, "samples": b},
            },
        }
        dialog._preview_request = 9
        dialog._receive({**response, "id": 9, "source_issues": ["widgets"]})
        assert dialog.visual_warning.isVisible()
        assert dialog.visual_consent.isVisible()
        assert not dialog.save_button.isEnabled()
        dialog.visual_consent.setChecked(True)
        assert dialog.save_button.isEnabled()
        target = tmp_path / "visual_only.pdf"
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            lambda *args: (str(target), "PDF (*.pdf)"),
        )
        requests = []
        monkeypatch.setattr(
            dialog._bridge, "send",
            lambda op, **kw: requests.append((op, kw)) or 23,
        )
        dialog._save()
        assert requests[0][1]["allow_visual_only"] is True
        dialog._exporting = False

        dialog._preview_request = 10
        dialog._receive({**response, "id": 10, "source_issues": ["signature"]})
        assert dialog.visual_warning.isVisible()
        assert not dialog.save_button.isEnabled()
        assert not dialog.visual_consent.isVisible()
    finally:
        dialog._exporting = False
        dialog.close()
        app.processEvents()

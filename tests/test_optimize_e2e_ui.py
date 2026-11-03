"""Offscreen real-Qt + spawned-worker optimization acceptance on synthetic PDF.

No user documents, mocked worker responses, or network are involved.
This does not replace hands-on Windows GUI testing.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest

pytest.importorskip("PySide6")
import fitz
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.ui.editor_window import EditWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def wait_for(app, predicate, *, timeout=35):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("Qt/worker operation timed out")


def test_40page_gui_button_to_real_worker_and_output(app, tmp_path, monkeypatch):
    source = tmp_path / "source_40.pdf"
    output = tmp_path / "source_40_optimized.pdf"
    with fitz.open() as doc:
        for i in range(40):
            page = doc.new_page(width=300, height=420)
            page.insert_text((25, 54), f"SYNTHETIC_PAGE_{i+1}")
        doc.set_toc([[1, "First", 1], [1, "Last", 40]])
        doc.save(source)

    old_hash = hashlib.sha256(source.read_bytes()).digest()
    warnings = []
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        lambda *a, **kw: (str(output), "PDF (*.pdf)"),
    )
    monkeypatch.setattr(
        QMessageBox, "warning",
        lambda *a, **kw: warnings.append(("warning", a[1:])),
    )
    monkeypatch.setattr(
        QMessageBox, "critical",
        lambda *a, **kw: warnings.append(("critical", a[1:])),
    )
    view = EditWindow()
    try:
        view.show()
        wait_for(app, lambda: (
            view._bridge._process is not None
            and view._bridge._process.is_alive()
        ))
        view.open_pdf(str(source))
        wait_for(app, lambda: (
            view._session is not None
            and len(view._session.pages) == 40
            and len(view._sizes) == 40
            and view.optimize_button.isEnabled()
        ))
        assert view.size_label.text()
        assert not view._dirty()
        view.optimize_button.click()
        assert view._optimizing
        assert not view.optimize_button.isEnabled()
        wait_for(app, lambda: (not view._optimizing) or bool(warnings))
        assert not warnings, warnings
        assert output.exists()
        assert "保存済み：" in view.statusBar().currentMessage()
        assert hashlib.sha256(source.read_bytes()).digest() == old_hash
        assert not view._dirty()
        assert view.optimize_button.isEnabled()
        with fitz.open(source) as original, fitz.open(output) as optimized:
            assert len(original) == len(optimized) == 40
            assert original.get_toc() == optimized.get_toc()
            assert original[0].get_text() == optimized[0].get_text()
            assert original[39].get_text() == optimized[39].get_text()
    finally:
        # Permit deterministic cleanup even if the assertion failed mid-worker.
        view._optimizing = False
        view.close()

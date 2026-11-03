"""Qt quality-preserving optimize button uses the worker, never the GUI thread."""
from __future__ import annotations
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.core.page_edit import EditSession
from pdf_works.ui.editor_window import EditWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def editor(app, monkeypatch, tmp_path):
    monkeypatch.setattr(EditWindow, "_start_worker", lambda self: None)
    # Closing a dirty editor requires user consent; automate only this test path.
    monkeypatch.setattr(
        QMessageBox, "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    view=EditWindow()
    src=tmp_path/"synthetic.pdf"
    src.write_bytes(b"NO REAL DOCUMENT NEEDED FOR UI")
    view._pdf_path=str(src)
    view._generation=30
    view._session=EditSession(6)
    view._source_sizes=[(595,842)]*6
    view._saved_snapshot=view._session.snapshot()
    view._refresh_pages(0)
    view.show()
    app.processEvents()
    yield view
    view.close()
    app.processEvents()


def test_optimize_worker_and_status_reports_no_false_savings(editor, tmp_path, monkeypatch):
    calls=[]
    monkeypatch.setattr(editor._bridge,"send",lambda op,**kw:
                        calls.append((op,kw)) or 71)
    monkeypatch.setattr(
        QFileDialog,"getSaveFileName",
        lambda *a,**kw:(str(tmp_path/"optimized.pdf"),"PDF (*.pdf)"),
    )
    original=editor._session.snapshot()
    assert editor.optimize_button.isEnabled()
    editor.optimize_button.click()
    assert calls[-1][0] == "optimize_lossless"
    assert calls[-1][1]["generation"] == 30
    assert calls[-1][1]["destination"] == str(tmp_path/"optimized.pdf")
    assert editor._optimizing
    assert not editor.extract_button.isEnabled()
    editor._on_worker_reply({
        "id":71,"op":"optimize_lossless","generation":30,
        "status":"ok", "before_bytes":1024, "after_bytes":1536, "pages":6,
    })
    assert not editor._optimizing
    assert "容量増加" in editor.statusBar().currentMessage()
    assert editor._session.snapshot() == original


def test_unsaved_edits_prohibit_optimization(editor, monkeypatch, tmp_path):
    editor._session.rotate(0,90)
    editor._refresh_pages(0)
    assert editor._dirty()
    assert not editor.optimize_button.isEnabled()
    called=[]
    monkeypatch.setattr(editor._bridge,"send",
                        lambda *a, **kw: called.append(a))
    monkeypatch.setattr(QMessageBox,"information",lambda *a, **kw: None)
    editor._optimize_source()  # extra guard when invoked by shortcuts/program
    assert not called


def test_existing_filename_not_overwritten(editor, tmp_path, monkeypatch):
    output=tmp_path/"existing.pdf"
    output.write_bytes(b"STAY")
    monkeypatch.setattr(
        QFileDialog,"getSaveFileName",lambda *a,**kw:(str(output),"PDF (*.pdf)")
    )
    monkeypatch.setattr(QMessageBox,"warning",lambda *a,**kw:None)
    called=[]
    monkeypatch.setattr(editor._bridge,"send",
                        lambda *a, **kw:called.append(a))
    editor._optimize_source()
    assert not called
    assert output.read_bytes() == b"STAY"

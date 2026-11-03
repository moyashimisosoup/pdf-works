"""Qt split group toolbar and dialog request; no disk IO on GUI thread."""
from __future__ import annotations
import os
import sys
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QFileDialog, QDialog, QMessageBox

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.core.page_edit import EditSession
from pdf_works.ui.editor_window import EditWindow
from pdf_works.ui.split_dialog import SplitGroupsDialog


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, monkeypatch, tmp_path):
    monkeypatch.setattr(EditWindow, "_start_worker", lambda self: None)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw:
                        QMessageBox.StandardButton.Yes)
    view=EditWindow()
    src=tmp_path/"lesson.pdf"
    src.write_bytes(b"TEST SOURCE PLACEHOLDER")
    view._pdf_path=str(src)
    view._generation=42
    view._session=EditSession(10)
    view._source_sizes=[(595,842)]*10
    view._saved_snapshot=view._session.snapshot()
    view._refresh_pages(0)
    view.show()
    app.processEvents()
    yield view
    view.close()
    app.processEvents()


def test_group_split_sends_edited_order_and_protects_busy(window, tmp_path, monkeypatch):
    calls=[]
    monkeypatch.setattr(window._bridge,"send",lambda op,**kw:
                        calls.append((op,kw)) or 66)
    monkeypatch.setattr(QFileDialog,"getExistingDirectory",lambda *a,**kw:
                        str(tmp_path))
    def confirm(dialog):
        dialog.mode.setCurrentIndex(1)
        dialog.boundaries.setText("3, 7")
        dialog._accept_config()
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(SplitGroupsDialog,"exec",confirm)
    window._session.move(9,0)
    window._session.rotate(0,90)
    window._refresh_pages(0)
    snapshot=window._session.snapshot()
    window.groups_button.click()
    assert calls[-1][0]=="split_groups"
    req=calls[-1][1]
    assert req["pages"]==snapshot
    assert req["boundaries"] == [3,7]
    assert req["prefix"]=="lesson"
    assert req["generation"]==42
    assert window._page_exporting
    assert not window.groups_button.isEnabled()
    assert not window.extract_button.isEnabled()
    window._on_worker_reply({
        "id":66, "op":"split_groups","generation":42,
        "status":"ok","count":3,
    })
    assert not window._page_exporting
    assert window._session.snapshot()==snapshot


def test_cancel_never_calls_worker(window, monkeypatch):
    calls=[]
    monkeypatch.setattr(window._bridge,"send",
                        lambda op, **kw: calls.append(op) or 99)
    monkeypatch.setattr(SplitGroupsDialog,"exec",
                        lambda self: QDialog.DialogCode.Rejected)
    window.groups_button.click()
    assert calls == []

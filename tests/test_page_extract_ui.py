"""Qt extraction and splitting dialog/IPC guard tests with an inert PDF worker."""
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
    monkeypatch.setattr(QMessageBox,"question",
                        lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    window = EditWindow()
    source = tmp_path / "synthetic.pdf"
    source.write_bytes(b"INERT SYNTHETIC PLACEHOLDER")
    window._pdf_path = str(source)
    window._generation = 3
    window._session = EditSession(6)
    window._source_sizes = [(595.,842.)] * 6
    window._saved_snapshot = window._session.snapshot()
    window._refresh_pages(0)
    window.show()
    app.processEvents()
    yield window
    window.close()
    app.processEvents()


def test_extract_selected_in_display_order_no_edit_mutation(editor, monkeypatch, tmp_path):
    requests = []
    monkeypatch.setattr(editor._bridge, "send", lambda operation, **kwargs:
                        requests.append((operation,kwargs)) or 72)
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        lambda *args, **kwargs: (str(tmp_path / "chosen.pdf"), "PDF (*.pdf)"),
    )
    editor._session.move(5, 0)
    editor._session.rotate(0, 90)
    editor._refresh_pages(0)
    editor.page_list.item(2).setSelected(True)
    editor.page_list.item(4).setSelected(True)
    snapshot = editor._session.snapshot()
    editor.extract_button.click()
    assert requests[-1][0] == "extract_selected"
    assert requests[-1][1]["pages"] == [snapshot[0],snapshot[2],snapshot[4]]
    assert editor._page_exporting
    assert not editor.split_button.isEnabled()
    assert editor._session.snapshot() == snapshot
    editor._on_worker_reply({"id":72, "op":"extract_selected",
                             "status":"ok", "generation":3, "count":3})
    assert not editor._page_exporting
    assert editor._session.snapshot() == snapshot


def test_split_selected_confirmation_and_prevents_existing(editor, monkeypatch, tmp_path):
    calls=[]
    monkeypatch.setattr(editor._bridge,"send",lambda operation,**kwargs:
                        calls.append((operation,kwargs)) or 73)
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory",
        lambda *args, **kwargs: str(tmp_path),
    )
    monkeypatch.setattr(
        QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    editor.page_list.item(3).setSelected(True)
    snapshot=editor._session.snapshot()
    editor.split_button.click()
    assert calls[-1][0] == "split_selected"
    assert calls[-1][1]["pages"] == [snapshot[0], snapshot[3]]
    assert calls[-1][1]["destination_dir"] == str(tmp_path)
    assert not editor.extract_button.isEnabled()
    editor._on_worker_reply({"id":73,"op":"split_selected",
                             "generation":3,"status":"ok","count":2})
    assert not editor._page_exporting
    assert editor._session.snapshot() == snapshot


def test_extract_does_not_overwrite_existing_or_source(editor, monkeypatch, tmp_path):
    calls=[]
    monkeypatch.setattr(editor._bridge,"send",lambda operation,**kwargs:
                        calls.append(operation) or 74)
    existing=tmp_path/"existing.pdf"
    existing.write_bytes(b"KEEP")
    monkeypatch.setattr(QFileDialog,"getSaveFileName",
                        lambda *args, **kwargs:(str(existing),"PDF (*.pdf)"))
    monkeypatch.setattr(QMessageBox,"warning",lambda *args, **kwargs:None)
    editor.extract_button.click()
    assert not calls
    assert existing.read_bytes()==b"KEEP"

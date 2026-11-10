"""Qt offscreen checks for the angle input, arrows and undo state."""
from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QFileDialog

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.core.page_edit import EditSession
from pdf_works.ui.editor_window import EditWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_angle_controls_preview_undo_and_save_payload(app, tmp_path, monkeypatch):
    monkeypatch.setattr(EditWindow, "_start_worker", lambda self: None)
    view = EditWindow()
    try:
        view._session = EditSession(3)
        view._source_sizes = [(300.0, 420.0)] * 3
        view._saved_snapshot = view._session.snapshot()
        view._saved_fine = view._session.fine_snapshot()
        view._refresh_pages(0)
        view.show()
        app.processEvents()
        assert view.fine_spin.value() == 0.0
        view.fine_right.click()
        assert view.fine_spin.value() == 0.1
        assert view._session.fine_snapshot() == [1, 0, 0]
        assert view._dirty()
        assert view.viewer._fine_degrees == 0.1
        view.fine_spin.setValue(-1.5)
        assert view._session.fine_snapshot() == [-15, 0, 0]
        assert view.viewer._fine_degrees == -1.5
        view._edit(("undo",))
        assert view._session.fine_snapshot() == [1, 0, 0]
        assert view.fine_spin.value() == 0.1
        assert not view.extract_button.isEnabled()
        assert not view.roi_export.isEnabled()

        source = tmp_path / "synthetic.pdf"
        source.write_bytes(b"not opened: export mock only")
        destination = tmp_path / "edited.pdf"
        view._pdf_path = str(source)
        payloads = []
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            lambda *args: (str(destination), "PDF (*.pdf)"),
        )
        monkeypatch.setattr(
            view._bridge, "send",
            lambda op, **payload: payloads.append((op, payload)) or 42,
        )
        view._save_as()
        assert payloads[0][0] == "export"
        assert payloads[0][1]["fine_angles"] == [1, 0, 0]
        assert view._saving
        # Clear fake busy flag so the close does not request waiting.
        view._saving = False
        view._save_request = None
        view._session.set_fine_many([0], 0)
        view._saved_fine = view._session.fine_snapshot()
    finally:
        view._session = None
        view._saving = False
        view.close()

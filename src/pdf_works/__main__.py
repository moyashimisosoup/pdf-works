"""Run alpha viewer via python -m pdf_works."""
from __future__ import annotations
import multiprocessing
import sys

def main()->int:
    multiprocessing.freeze_support()
    from PySide6.QtWidgets import QApplication
    from .ui.editor_window import EditWindow as MainWindow
    app=QApplication(sys.argv)
    # Fusion gives Qt controls a stable platform-independent baseline.
    # Native Windows file dialogs and the window frame remain untouched.
    app.setStyle("Fusion")
    from .ui.typography import load_local_fonts, font_for_preset
    from PySide6.QtCore import QSettings
    chosen = str(QSettings("pdf-works", "desktop").value("text_weight", "standard"))
    load_local_fonts(chosen)
    app.setFont(font_for_preset(chosen))
    window=MainWindow()
    window.show()
    return app.exec()

if __name__=="__main__":
    raise SystemExit(main())

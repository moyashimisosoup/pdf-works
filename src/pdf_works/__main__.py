"""Run alpha viewer via python -m pdf_works."""
from __future__ import annotations
import multiprocessing
import sys

def main()->int:
    multiprocessing.freeze_support()
    from PySide6.QtWidgets import QApplication
    from .ui.editor_window import EditWindow as MainWindow
    app=QApplication(sys.argv)
    from .ui.typography import load_local_fonts, font_for_preset
    from PySide6.QtCore import QSettings
    load_local_fonts()
    chosen = str(QSettings("pdf-works", "desktop").value("text_weight", "standard"))
    app.setFont(font_for_preset(chosen))
    window=MainWindow()
    window.show()
    return app.exec()

if __name__=="__main__":
    raise SystemExit(main())

"""Run alpha viewer via python -m pdf_works."""
from __future__ import annotations
import multiprocessing
import sys

def main()->int:
    multiprocessing.freeze_support()
    from PySide6.QtWidgets import QApplication
    from .ui.main_window import MainWindow
    app=QApplication(sys.argv)
    window=MainWindow()
    window.show()
    return app.exec()

if __name__=="__main__":
    raise SystemExit(main())

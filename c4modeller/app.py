from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .gui import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("C4 Modeller")
    window = MainWindow()
    window.resize(1200, 800)
    window.show()
    return app.exec()


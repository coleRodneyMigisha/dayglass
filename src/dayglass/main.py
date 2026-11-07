"""Application entry point for Dayglass."""

import sys

from PySide6.QtWidgets import QApplication

from dayglass.ui.main_window import MainWindow
from dayglass.ui.styles import APP_STYLESHEET


def main() -> int:
    """Initialize the application and start the Qt event loop."""

    app = QApplication(sys.argv)
    app.setApplicationName("Dayglass")
    app.setStyleSheet(APP_STYLESHEET)

    window = MainWindow()
    window.show()

    # Qt processes clicks, redraws, and window events in this loop.
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

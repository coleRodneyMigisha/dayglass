
"""Visual theme for the Dayglass interface."""

from PySide6.QtGui import QColor

from dayglass.services.wallpaper import DEFAULT_ACCENT


def build_stylesheet(wallpaper_color: str = DEFAULT_ACCENT) -> str:
    """Build the interface stylesheet using a wallpaper-derived accent."""

    color = QColor(wallpaper_color)

    if not color.isValid():
        color = QColor(DEFAULT_ACCENT)

    # Dark accents need a lighter shade to remain visible on dark surfaces.
    if color.lightness() < 145:
        color = color.lighter(220)

    accent = color.name()
    accent_soft = (
        f"rgba({color.red()}, {color.green()}, "
        f"{color.blue()}, 0.16)"
    )
    accent_border = (
        f"rgba({color.red()}, {color.green()}, "
        f"{color.blue()}, 0.45)"
    )

    template = """
    QWidget {
        color: #E8EDF4;
        font-family: "Noto Sans", "Ubuntu", sans-serif;
        font-size: 13px;
    }

    QWidget#root {
        background-color: rgba(24, 29, 39, 238);
        border: 1px solid rgba(255, 255, 255, 35);
        border-radius: 20px;
    }

    QFrame#header {
        background: transparent;
        border: none;
    }

    QLabel#app_title {
        color: #F5F7FB;
        font-size: 19px;
        font-weight: 600;
    }

    QLabel#muted {
        color: #A7B0C0;
    }

    QFrame#task_card {
        background-color: rgba(255, 255, 255, 12);
        border: 1px solid rgba(255, 255, 255, 18);
        border-radius: 12px;
    }

    QCheckBox {
        spacing: 10px;
        color: #E8EDF4;
        padding: 7px;
    }

    QCheckBox::indicator {
        width: 17px;
        height: 17px;
        border-radius: 5px;
        border: 1px solid #78869B;
        background-color: rgba(255, 255, 255, 8);
    }

    QCheckBox::indicator:checked {
        background-color: @ACCENT@;
        border: 1px solid @ACCENT@;
    }

    QPushButton {
        background-color: rgba(255, 255, 255, 18);
        border: 1px solid rgba(255, 255, 255, 28);
        border-radius: 8px;
        padding: 6px 10px;
        color: #F5F7FB;
    }

    QPushButton:hover {
        background-color: rgba(255, 255, 255, 32);
    }

    QPushButton#close_button:hover {
        background-color: #A94452;
    }

    QProgressBar {
        background-color: rgba(255, 255, 255, 18);
        border: none;
        border-radius: 4px;
        min-height: 7px;
        max-height: 7px;
        text-align: center;
    }

    QProgressBar::chunk {
        background-color: @ACCENT@;
        border-radius: 4px;
    }

    QLineEdit,
    QPlainTextEdit {
        background-color: @ACCENT_SOFT@;
        border: 1px solid @ACCENT_BORDER@;
        border-radius: 10px;
        padding: 8px 10px;
        color: #f2f5f3;
        selection-background-color: @ACCENT@;
    }

    QPlainTextEdit {
        padding: 10px;
    }

    QLineEdit:hover,
    QPlainTextEdit:hover {
        border-color: @ACCENT@;
    }

    QLineEdit:focus,
    QPlainTextEdit:focus {
        background-color: @ACCENT_SOFT@;
        border: 1px solid @ACCENT@;
    }

    """

    return (
        template
        .replace("@ACCENT@", accent)
        .replace("@ACCENT_SOFT@", accent_soft)
        .replace("@ACCENT_BORDER@", accent_border)
    )


# Preserve the existing import used by main.py.
APP_STYLESHEET = build_stylesheet()

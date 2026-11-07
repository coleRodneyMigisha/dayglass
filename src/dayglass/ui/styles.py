
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
        background-color: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(32, 36, 46, 220),
            stop: 0.48 rgba(20, 24, 34, 210),
            stop: 1 rgba(15, 18, 26, 225)
        );
        border: 1px solid rgba(255, 255, 255, 60);
        border-radius: 22px;
    }

    QFrame#header {
        background: transparent;
        border: none;
    }

    QLabel#app_title {
        color: #F5F7FB;
        font-size: 16px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }

    QLabel#section_header {
        color: rgba(235, 240, 250, 0.45);
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        margin-top: 4px;
        margin-bottom: 1px;
    }

    QLabel#date_display {
        color: #F8FAFD;
        font-size: 13.5px;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 8px;
    }

    QLabel#date_display:hover {
        background-color: rgba(255, 255, 255, 0.08);
    }

    QLabel#muted {
        color: #8E99AB;
        font-size: 12px;
    }

    QLabel#muted_caption {
        color: rgba(220, 228, 240, 0.48);
        font-size: 11px;
        font-weight: 500;
    }

    QFrame#task_card {
        background: rgba(255, 255, 255, 0.035);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 14px;
    }

    QWidget#task_row,
    QWidget#weekly_goal_card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 10px;
    }

    QWidget#task_row:hover,
    QWidget#weekly_goal_card:hover {
        background: rgba(255, 255, 255, 0.065);
        border-color: rgba(255, 255, 255, 0.11);
    }

    QPushButton#action_btn {
        background: transparent;
        border: none;
        border-radius: 6px;
        color: rgba(230, 238, 250, 0.45);
        font-size: 13px;
        font-weight: 500;
        padding: 0;
    }

    QPushButton#action_btn:hover {
        background: rgba(255, 255, 255, 0.12);
        color: #FFFFFF;
    }

    QPushButton#action_btn:pressed,
    QPushButton#action_btn[active="true"] {
        background: @ACCENT_SOFT@;
        color: @ACCENT@;
    }

    QPushButton#action_btn[has_content="true"] {
        color: @ACCENT@;
    }

    QPushButton#delete_action_btn {
        background: transparent;
        border: none;
        border-radius: 6px;
        color: rgba(230, 238, 250, 0.35);
        font-size: 14px;
        font-weight: 400;
        padding: 0;
    }

    QPushButton#delete_action_btn:hover {
        background: rgba(255, 95, 87, 0.18);
        color: #FF6B6B;
    }

    QPushButton#delete_action_btn:pressed {
        background: rgba(255, 95, 87, 0.30);
        color: #FF4D4D;
    }

    QPushButton#nav_btn {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        color: #E2E8F0;
        font-size: 12.5px;
        font-weight: 500;
        padding: 3px 9px;
    }

    QPushButton#nav_btn:hover {
        background: rgba(255, 255, 255, 0.13);
        border-color: rgba(255, 255, 255, 0.16);
        color: #FFFFFF;
    }

    QPushButton#nav_btn:pressed {
        background: @ACCENT_SOFT@;
        border-color: @ACCENT_BORDER@;
    }

    QPushButton#pill_btn {
        background: @ACCENT_SOFT@;
        border: 1px solid @ACCENT_BORDER@;
        border-radius: 10px;
        color: #FFFFFF;
        font-size: 15px;
        font-weight: 600;
    }

    QPushButton#pill_btn:hover {
        background: @ACCENT@;
        border-color: @ACCENT@;
    }

    QFrame#glass_nav {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 0, y2: 1,
            stop: 0 rgba(255, 255, 255, 49),
            stop: 0.45 rgba(238, 244, 255, 27),
            stop: 1 rgba(190, 205, 228, 18)
        );
        border: 1px solid rgba(255, 255, 255, 82);
        border-radius: 30px;
    }

    QPushButton#glass_nav_button,
    QPushButton#glass_nav_button:hover,
    QPushButton#glass_nav_button:checked {
        background: transparent;
        border: none;
        color: #F7FAFF;
        font-weight: 600;
        padding: 6px 12px;
    }

    QLabel#focus_timer {
        color: #F8FAFF;
        font-size: 58px;
        font-weight: 300;
        letter-spacing: 2px;
    }

    QProgressBar#focus_progress {
        background-color: rgba(255, 255, 255, 32);
        border: 1px solid rgba(255, 255, 255, 48);
        border-radius: 5px;
        min-height: 8px;
        max-height: 8px;
    }

    QProgressBar#focus_progress::chunk {
        background-color: @ACCENT@;
        border-radius: 4px;
    }

    QPushButton#focus_primary {
        background-color: @ACCENT_SOFT@;
        border: 1px solid @ACCENT_BORDER@;
        border-radius: 16px;
        padding: 10px 24px;
        font-weight: 600;
    }

    QCheckBox {
        spacing: 9px;
        color: #EDF2F7;
        padding: 5px 4px;
        font-size: 13.5px;
    }

    QCheckBox::indicator {
        width: 17px;
        height: 17px;
        border-radius: 8.5px;
        border: 1.5px solid rgba(255, 255, 255, 0.35);
        background-color: rgba(255, 255, 255, 0.04);
    }

    QCheckBox::indicator:hover {
        border-color: @ACCENT@;
        background-color: rgba(255, 255, 255, 0.08);
    }

    QCheckBox::indicator:checked {
        background-color: @ACCENT@;
        border: 1.5px solid @ACCENT@;
    }

    QPushButton {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 5px 10px;
        color: #F5F7FB;
    }

    QPushButton:hover {
        background: rgba(255, 255, 255, 0.12);
        border-color: rgba(255, 255, 255, 0.15);
    }

    QPushButton:pressed,
    QPushButton[expanded="true"] {
        background-color: @ACCENT_SOFT@;
        border-color: @ACCENT_BORDER@;
    }

    QPushButton#close_button:hover {
        background-color: #A94452;
        border-color: #C04E5D;
    }

    QProgressBar {
        background: rgba(255, 255, 255, 0.08);
        border: none;
        border-radius: 2px;
        min-height: 4px;
        max-height: 4px;
        text-align: center;
    }

    QProgressBar::chunk {
        background-color: @ACCENT@;
        border-radius: 2px;
    }

    QLineEdit,
    QPlainTextEdit {
        background: rgba(255, 255, 255, 0.045);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 8px 12px;
        color: #F0F4F8;
        selection-background-color: @ACCENT@;
    }

    QPlainTextEdit {
        padding: 10px 12px;
    }

    QLineEdit:hover,
    QPlainTextEdit:hover {
        background: rgba(255, 255, 255, 0.065);
        border-color: rgba(255, 255, 255, 0.14);
    }

    QLineEdit:focus,
    QPlainTextEdit:focus {
        background-color: rgba(255, 255, 255, 0.08);
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

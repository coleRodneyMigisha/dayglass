
"""Main floating window for Dayglass."""

from datetime import date, datetime, timedelta
import time
from zoneinfo import ZoneInfo

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPoint,
    QDate,
    QPropertyAnimation,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QCheckBox,
    QInputDialog,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from dayglass.config import (
    APP_NAME,
    MAX_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from dayglass.database.task_repository import TaskRepository
from dayglass.database.notes_repository import NotesRepository
from dayglass.database.weekly_goal_repository import WeeklyGoalRepository
from dayglass.services.notion_sync import NotionSyncService
from dayglass.services.wallpaper_watcher import WallpaperWatcher
from dayglass.services.wallpaper import DEFAULT_ACCENT
from dayglass.ui.styles import build_stylesheet


class DragHandle(QFrame):
    """A title bar that asks the desktop to move its parent window."""

    def __init__(self, window: QWidget) -> None:
        super().__init__()
        self._window = window

    def mousePressEvent(self, event) -> None:
        """Request a native window move when the title bar is grabbed."""
        if event.button() == Qt.MouseButton.LeftButton:
            window_handle = self._window.windowHandle()

            if window_handle is not None:
                window_handle.startSystemMove()

            event.accept()
            return

        super().mousePressEvent(event)


class LiquidGlassPill(QWidget):
    """A softly highlighted, animated glass tab indicator."""

    def __init__(self, parent: QWidget, accent: str) -> None:
        super().__init__(parent)
        self._fill_level = 0.0
        self._accent = QColor(accent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def get_fill_level(self) -> float:
        return self._fill_level

    def set_fill_level(self, value: float) -> None:
        self._fill_level = max(0.0, min(1.0, value))
        self.update()

    fillLevel = Property(float, get_fill_level, set_fill_level)

    def set_accent(self, accent: str) -> None:
        self._accent = QColor(accent)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds = self.rect().adjusted(1, 1, -1, -1)
        radius = bounds.height() / 2

        painter.setPen(QColor(255, 255, 255, 90))
        painter.setBrush(QColor(255, 255, 255, 24))
        painter.drawRoundedRect(bounds, radius, radius)

        accent = QColor(self._accent)
        accent.setAlpha(round(28 + 88 * self._fill_level))
        liquid = QLinearGradient(bounds.topLeft(), bounds.bottomRight())
        liquid.setColorAt(0.0, QColor(255, 255, 255, 90))
        liquid.setColorAt(0.32, accent.lighter(125))
        liquid.setColorAt(1.0, accent.darker(115))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(liquid)
        painter.drawRoundedRect(bounds.adjusted(2, 2, -2, -2), radius - 2, radius - 2)

        sheen = QLinearGradient(0, bounds.top(), 0, bounds.center().y())
        sheen.setColorAt(0.0, QColor(255, 255, 255, 95))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(sheen)
        painter.drawRoundedRect(bounds.adjusted(3, 2, -3, -bounds.height() // 2), radius - 3, radius - 3)


class GlassNavigation(QFrame):
    """Centered floating navigation with a liquid-glass active tab."""

    page_selected = Signal(int)

    def __init__(self, accent: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("glass_nav")
        self.setFixedSize(210, 60)
        self._buttons: list[QPushButton] = []
        self._active_index = 0
        self._pill = LiquidGlassPill(self, accent)
        self._position_animation = QPropertyAnimation(
            self._pill, b"geometry", self
        )
        self._position_animation.setDuration(430)
        self._position_animation.setEasingCurve(QEasingCurve.Type.OutBack)
        self._fill_animation: QPropertyAnimation | None = None

        row = QHBoxLayout(self)
        row.setContentsMargins(7, 7, 7, 7)
        row.setSpacing(4)
        for index, label in enumerate(("Plan", "Focus")):
            button = QPushButton(label, self)
            button.setObjectName("glass_nav_button")
            button.setCheckable(True)
            button.setFixedSize(96, 46)
            button.clicked.connect(
                lambda _checked=False, page=index: self.page_selected.emit(page)
            )
            row.addWidget(button)
            self._buttons.append(button)
        self._buttons[0].setChecked(True)
        self._pill.setGeometry(self._buttons[0].geometry())
        self._pill.lower()

    def set_active(self, index: int, animate: bool = True) -> None:
        if not 0 <= index < len(self._buttons):
            return
        self._active_index = index
        for button_index, button in enumerate(self._buttons):
            button.setChecked(button_index == index)

        destination = self._buttons[index].geometry()
        self._position_animation.stop()
        if animate:
            self._position_animation.setStartValue(self._pill.geometry())
            self._position_animation.setEndValue(destination)
            self._position_animation.start()
            if self._fill_animation is not None:
                self._fill_animation.stop()
            self._fill_animation = QPropertyAnimation(self._pill, b"fillLevel", self)
            self._fill_animation.setDuration(260)
            self._fill_animation.setStartValue(0.0)
            self._fill_animation.setEndValue(1.0)
            self._fill_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._fill_animation.finished.connect(lambda: self._pill.set_fill_level(1.0))
            self._fill_animation.start()
        else:
            self._pill.setGeometry(destination)
            self._pill.set_fill_level(1.0)

    def set_accent(self, accent: str) -> None:
        self._pill.set_accent(accent)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._buttons:
            self._pill.setGeometry(self._buttons[self._active_index].geometry())


class MainWindow(QWidget):
    """A compact, draggable daily-planner window."""

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        watch_wallpaper: bool = True,
        notion_sync: NotionSyncService | None = None,
    ) -> None:
        super().__init__()

        self._task_repository = task_repository or TaskRepository()
        self._today = datetime.now(ZoneInfo("Africa/Kampala")).date().isoformat()
        self._notion_sync = notion_sync or NotionSyncService()

        self._notes_repository = NotesRepository(self._task_repository.database_path)
        self._weekly_repository = WeeklyGoalRepository(self._task_repository.database_path)
        self._notes_save_timer = QTimer(self)
        self._notes_save_timer.setSingleShot(True)
        self._notes_save_timer.setInterval(800)
        self._notes_save_timer.timeout.connect(self._save_notes)
        self._focus_duration = 25 * 60
        self._focus_session_total = 25 * 60
        self._focus_deadline: float | None = None
        self._focus_timer = QTimer(self)
        self._focus_timer.setInterval(250)
        self._focus_timer.timeout.connect(self._update_focus_timer)

        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(30_000)
        self._sync_timer.timeout.connect(self._sync_from_notion)
        self._sync_timer.start()

        if self._notion_sync.is_configured:
            self._notion_sync.start_network_monitor(
                task_repo=self._task_repository,
                get_current_date=lambda: self._today,
                on_change=lambda: QTimer.singleShot(
                    0, lambda: self._load_tasks_if_same_date(self._today)
                ),
            )

        self._task_checkboxes: list[QCheckBox] = []
        self._task_ids: list[int] = []

        self._subtask_containers: dict[int, QWidget] = {}
        self._subtask_layouts: dict[int, QVBoxLayout] = {}
        self._subtask_inputs: dict[int, QLineEdit] = {}
        self._subtask_buttons: dict[int, QPushButton] = {}

        self._task_note_inputs: dict[int, QPlainTextEdit] = {}
        self._subtask_note_inputs: dict[int, QPlainTextEdit] = {}
        self._task_notes_panels: dict[int, QFrame] = {}
        self._task_notes_buttons: dict[int, QPushButton] = {}

        self._item_notes_timers: dict[str, QTimer] = {}

        self._wallpaper_watcher: WallpaperWatcher | None = None

        self.setWindowTitle(APP_NAME)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.setMaximumWidth(MAX_WINDOW_WIDTH)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )

        self._build_ui()
        self._load_notes()
        self._load_tasks()

        if watch_wallpaper:
            self._wallpaper_watcher = WallpaperWatcher(self)
            self._wallpaper_watcher.accent_changed.connect(
                self._apply_accent
            )
            self._wallpaper_watcher.start()
        QTimer.singleShot(0, self._adjust_window_height)

    def _build_ui(self) -> None:
        """Construct the interface and connect user interactions."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        root = QWidget()
        root.setObjectName("root")
        outer_layout.addWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(13)

        header = DragHandle(self)
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("dayglass")
        title.setObjectName("app_title")
        title.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        minimize_button = QPushButton("−")
        minimize_button.setFixedSize(30, 28)
        minimize_button.setToolTip("Minimize window")
        minimize_button.clicked.connect(self.showMinimized)

        close_button = QPushButton("×")
        close_button.setObjectName("close_button")
        close_button.setFixedSize(30, 28)
        close_button.setToolTip("Close Dayglass")
        close_button.clicked.connect(self.close)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(minimize_button)
        header_layout.addWidget(close_button)
        layout.addWidget(header)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setAutoFillBackground(False)
        scroll_area.viewport().setAutoFillBackground(False)
        scroll_area.viewport().setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        content = QWidget()
        content.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(13)
        scroll_area.setWidget(content)
        self._screen_stack = QStackedWidget(root)
        self._screen_stack.addWidget(scroll_area)
        self._screen_stack.addWidget(self._build_focus_page())
        layout.addWidget(self._screen_stack, 1)
        layout = content_layout

        date_navigation = QHBoxLayout()
        date_navigation.setSpacing(6)
        date_navigation.setContentsMargins(0, 2, 0, 4)

        self._previous_day_button = QPushButton("‹")
        self._previous_day_button.setObjectName("nav_btn")
        self._previous_day_button.setFixedSize(30, 28)
        self._previous_day_button.setToolTip("Previous day")
        self._previous_day_button.clicked.connect(
            self._go_to_previous_day
        )

        self._date_label = QLabel()
        self._date_label.setObjectName("date_display")
        self._date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._date_label.setCursor(Qt.PointingHandCursor)
        self._date_label.mousePressEvent = lambda _event: self._open_date_picker()

        self._calendar_button = QPushButton("▦")
        self._calendar_button.setObjectName("nav_btn")
        self._calendar_button.setFixedSize(30, 28)
        self._calendar_button.setToolTip("Choose a date")
        self._calendar_button.clicked.connect(
            self._open_date_picker
        )

        self._today_button = QPushButton("Today")
        self._today_button.setObjectName("nav_btn")
        self._today_button.setFixedHeight(28)
        self._today_button.clicked.connect(self._go_to_today)

        self._next_day_button = QPushButton("›")
        self._next_day_button.setObjectName("nav_btn")
        self._next_day_button.setFixedSize(30, 28)
        self._next_day_button.setToolTip("Next day")
        self._next_day_button.clicked.connect(
            self._go_to_next_day
        )

        date_navigation.addWidget(self._previous_day_button)
        date_navigation.addWidget(self._date_label, 1)
        date_navigation.addWidget(self._calendar_button)
        date_navigation.addWidget(self._today_button)
        date_navigation.addWidget(self._next_day_button)

        layout.addLayout(date_navigation)
        self._update_date_label()

        section_title = QLabel("TODAY'S FOCUS")
        section_title.setObjectName("section_header")
        layout.addWidget(section_title)

        progress_row = QHBoxLayout()
        progress_row.setContentsMargins(0, 0, 0, 0)
        self.progress_label = QLabel()
        self.progress_label.setObjectName("muted_caption")
        self.subtask_progress_label = QLabel()
        self.subtask_progress_label.setObjectName("muted_caption")
        progress_row.addWidget(self.progress_label)
        progress_row.addStretch()
        progress_row.addWidget(self.subtask_progress_label)
        layout.addLayout(progress_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("task_progress_bar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        layout.addWidget(self.progress_bar)

        weekly_title = QLabel("THIS WEEK'S OBJECTIVES")
        weekly_title.setObjectName("section_header")
        layout.addWidget(weekly_title)

        self._weekly_layout = QVBoxLayout()
        self._weekly_layout.setSpacing(3)
        layout.addLayout(self._weekly_layout)

        weekly_input_row = QHBoxLayout()
        weekly_input_row.setSpacing(6)
        self._weekly_input = QLineEdit()
        self._weekly_input.setPlaceholderText("Add a weekly objective...")
        self._weekly_input.returnPressed.connect(self._add_weekly_goal)
        weekly_add = QPushButton("+")
        weekly_add.setObjectName("pill_btn")
        weekly_add.setFixedSize(32, 32)
        weekly_add.setToolTip("Add objective")
        weekly_add.clicked.connect(self._add_weekly_goal)
        weekly_input_row.addWidget(self._weekly_input, 1)
        weekly_input_row.addWidget(weekly_add)
        layout.addLayout(weekly_input_row)

        # Tasks are added here dynamically from the repository.
        task_card = QFrame()
        task_card.setObjectName("task_card")
        self._task_layout = QVBoxLayout(task_card)
        self._task_layout.setContentsMargins(8, 8, 8, 8)
        self._task_layout.setSpacing(4)
        layout.addWidget(task_card)

        # Input for creating a task.
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)
        self._task_input = QLineEdit()
        self._task_input.setPlaceholderText("Add a task for today...")
        self._task_input.returnPressed.connect(
            self._add_task_from_input
        )

        self._add_task_button = QPushButton("+")
        self._add_task_button.setObjectName("pill_btn")
        self._add_task_button.setFixedSize(32, 32)
        self._add_task_button.setToolTip("Add task")
        self._add_task_button.clicked.connect(
            self._add_task_from_input
        )

        input_layout.addWidget(self._task_input, 1)
        input_layout.addWidget(self._add_task_button)
        layout.addLayout(input_layout)

        # Daily scratchpad.
        scratchpad_title = QLabel("SCRATCHPAD")
        scratchpad_title.setObjectName("section_header")
        layout.addWidget(scratchpad_title)

        self._notes_input = QPlainTextEdit()
        self._notes_input.setPlaceholderText(
            "Jot down thoughts, reminders, or ideas..."
        )
        self._notes_input.setFixedHeight(95)
        self._notes_input.textChanged.connect(
            self._schedule_notes_save
        )
        layout.addWidget(self._notes_input)

        layout.addStretch()

        note = QLabel("Small steps. Steady progress.")
        note.setObjectName("muted")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(note)

        self._navigation = GlassNavigation(DEFAULT_ACCENT, root)
        self._navigation.page_selected.connect(self._switch_screen)
        navigation_row = QHBoxLayout()
        navigation_row.addStretch(1)
        navigation_row.addWidget(self._navigation)
        navigation_row.addStretch(1)
        layout_root = root.layout()
        layout_root.addLayout(navigation_row)

    def _build_focus_page(self) -> QWidget:
        """Create a dedicated screen for the focus countdown."""
        page = QWidget()
        page.setObjectName("focus_page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 22)
        layout.addStretch(2)

        eyebrow = QLabel("FOCUS SESSION")
        eyebrow.setObjectName("muted")
        eyebrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(eyebrow)

        self._focus_label = QLabel("25:00")
        self._focus_label.setObjectName("focus_timer")
        self._focus_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._focus_label)

        session_note = QLabel("A quiet 25 minutes for one thing.")
        session_note.setObjectName("muted")
        session_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(session_note)

        self._focus_progress = QProgressBar()
        self._focus_progress.setObjectName("focus_progress")
        self._focus_progress.setRange(0, 25 * 60)
        self._focus_progress.setValue(0)
        self._focus_progress.setTextVisible(False)
        layout.addWidget(self._focus_progress)

        controls = QHBoxLayout()
        self._focus_start_button = QPushButton("Start focus")
        self._focus_start_button.setObjectName("focus_primary")
        self._focus_start_button.clicked.connect(self._toggle_focus_timer)
        focus_reset = QPushButton("Reset")
        focus_reset.clicked.connect(self._reset_focus_timer)
        controls.addStretch()
        controls.addWidget(self._focus_start_button)
        controls.addWidget(focus_reset)
        controls.addStretch()
        layout.addLayout(controls)
        layout.addStretch(3)
        return page

    def _switch_screen(self, index: int) -> None:
        self._screen_stack.setCurrentIndex(index)
        self._navigation.set_active(index)
        QTimer.singleShot(0, self._adjust_window_height)


    def _load_notes(self) -> None:
        """Load today's saved scratchpad notes."""
        content = self._notes_repository.get_notes(self._today)

        # Avoid triggering an unnecessary save while loading.
        self._notes_input.blockSignals(True)
        self._notes_input.setPlainText(content)
        self._notes_input.blockSignals(False)

    def _schedule_notes_save(self) -> None:
        """Save notes after the user pauses typing."""
        self._notes_save_timer.start()

    def _schedule_item_notes_save(
            self,
            item_type: str,
            item_id: int,
    ) -> None:
        """Save task or subtask notes after typing pauses."""
        key = f"{item_type}:{item_id}"

        if key not in self._item_notes_timers:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.setInterval(800)
            timer.timeout.connect(
                lambda current_type=item_type, current_id=item_id:
                self._save_item_notes(current_type, current_id)
            )
            self._item_notes_timers[key] = timer

        self._item_notes_timers[key].start()

    def _save_item_notes(
            self,
            item_type: str,
            item_id: int,
    ) -> None:
        """Persist one task's or subtask's notes."""
        key = f"{item_type}:{item_id}"
        timer = self._item_notes_timers.get(key)

        if timer is not None:
            timer.stop()

        if item_type == "task":
            field = self._task_note_inputs.get(item_id)
            if field is not None:
                notes_content = field.toPlainText()
                self._task_repository.save_task_notes(
                    item_id,
                    notes_content,
                )
                task = self._task_repository.get_task_by_id(item_id)
                if hasattr(self, "_notion_sync"):
                    self._notion_sync.push_notes_async(
                        item_id,
                        task.get("notion_id") if task else None,
                        notes_content,
                        self._task_repository,
                    )
        elif item_type == "subtask":
            field = self._subtask_note_inputs.get(item_id)
            if field is not None:
                self._task_repository.save_subtask_notes(
                    item_id,
                    field.toPlainText(),
                )

    def _flush_item_notes(self) -> None:
        """Persist pending task/subtask notes before their widgets change."""
        for key in list(self._item_notes_timers):
            item_type, raw_id = key.split(":", 1)
            self._save_item_notes(item_type, int(raw_id))

    def _save_notes(self) -> None:
        """Persist the current scratchpad contents."""
        self._notes_repository.save_notes(
            self._today,
            self._notes_input.toPlainText(),
        )

    def _toggle_focus_timer(self) -> None:
        if self._focus_timer.isActive():
            remaining = max(0, round((self._focus_deadline or time.monotonic()) - time.monotonic()))
            self._focus_duration = remaining
            self._focus_deadline = None
            self._focus_timer.stop()
            self._focus_start_button.setText("Resume")
        else:
            self._focus_deadline = time.monotonic() + self._focus_duration
            self._focus_timer.start()
            self._focus_start_button.setText("Pause")
            self._update_focus_timer()

    def _update_focus_timer(self) -> None:
        if self._focus_deadline is None:
            return
        remaining = max(0, int(self._focus_deadline - time.monotonic() + 0.999))
        self._focus_label.setText(f"{remaining // 60:02d}:{remaining % 60:02d}")
        self._focus_progress.setValue(
            min(self._focus_session_total, self._focus_session_total - remaining)
        )
        if remaining == 0:
            self._focus_timer.stop()
            self._focus_duration = 25 * 60
            self._focus_deadline = None
            self._focus_start_button.setText("Start focus")

    def _reset_focus_timer(self) -> None:
        self._focus_timer.stop()
        self._focus_deadline = None
        self._focus_duration = 25 * 60
        self._focus_session_total = 25 * 60
        self._focus_progress.setRange(0, self._focus_session_total)
        self._focus_progress.setValue(0)
        self._focus_label.setText("25:00")
        self._focus_start_button.setText("Start focus")

    def _update_date_label(self) -> None:
        """Display the currently selected date."""
        selected_date = date.fromisoformat(self._today)
        self._date_label.setText(
            selected_date.strftime("%A, %d %B")
        )

    def _go_to_previous_day(self) -> None:
        """Navigate to the previous day."""
        selected_date = date.fromisoformat(self._today)
        self._change_selected_date(
            (selected_date - timedelta(days=1)).isoformat()
        )

    def _go_to_next_day(self) -> None:
        """Navigate to the next day."""
        selected_date = date.fromisoformat(self._today)
        self._change_selected_date(
            (selected_date + timedelta(days=1)).isoformat()
        )

    def _go_to_today(self) -> None:
        """Return to the current calendar day."""
        self._change_selected_date(
            datetime.now(ZoneInfo("Africa/Kampala")).date().isoformat()
        )

    def _change_selected_date(self, selected_date: str) -> None:
        """Switch the displayed tasks and notes to another date."""
        if selected_date == self._today:
            return

        self._notes_save_timer.stop()
        self._save_notes()
        self._today = selected_date
        self._update_date_label()
        self._load_tasks()
        self._load_notes()
        QTimer.singleShot(0, self._adjust_window_height)

    def _open_date_picker(self) -> None:
        """Open a calendar dialog to select a date."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Choose a date")
        dialog.setModal(True)

        dialog_layout = QVBoxLayout(dialog)

        calendar = QCalendarWidget()
        calendar.setSelectedDate(
            QDate.fromString(self._today, "yyyy-MM-dd")
        )
        dialog_layout.addWidget(calendar)

        button_layout = QHBoxLayout()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)

        select_button = QPushButton("Select date")
        select_button.clicked.connect(dialog.accept)

        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(select_button)

        dialog_layout.addLayout(button_layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_date = calendar.selectedDate().toString(
                "yyyy-MM-dd"
            )
            self._change_selected_date(selected_date)

    def _sync_from_notion(self) -> None:
        """Background pull and push sync with Notion for the currently viewed date."""
        if hasattr(self, "_notion_sync") and self._notion_sync.is_configured:
            target_date = self._today
            self._notion_sync.sync_all(
                self._task_repository,
                current_date=target_date,
                on_change=lambda: QTimer.singleShot(0, lambda: self._load_tasks_if_same_date(target_date)),
            )

    def _load_tasks_if_same_date(self, target_date: str) -> None:
        if self._today == target_date:
            self._load_tasks(trigger_sync=False)
            self._update_progress()

    def _load_tasks(self, trigger_sync: bool = True) -> None:
        """Load today's tasks and their expandable subtasks."""
        if trigger_sync:
            self._sync_from_notion()
        self._flush_item_notes()
        while self._task_layout.count():
            item = self._task_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._task_checkboxes.clear()
        self._task_ids.clear()
        self._subtask_containers.clear()
        self._subtask_layouts.clear()
        self._subtask_inputs.clear()
        self._subtask_buttons.clear()
        self._task_note_inputs.clear()
        self._subtask_note_inputs.clear()
        self._task_notes_panels.clear()
        self._task_notes_buttons.clear()

        tasks = self._task_repository.get_tasks_for_date(self._today)
        weekly_goals = self._weekly_repository.get_goals(self._week_start())
        weekly_goal_titles = {
            goal["id"]: goal["title"] for goal in weekly_goals
        }

        tomorrow = (
                date.fromisoformat(self._today) + timedelta(days=1)
        ).isoformat()

        tomorrow_tasks = self._task_repository.get_tasks_for_date(tomorrow)

        carried_task_ids = {
            task["carried_from_task_id"]
            for task in tomorrow_tasks
            if task["carried_from_task_id"] is not None
        }

        if not tasks:
            empty_label = QLabel("No tasks yet. Add one below.")
            empty_label.setObjectName("muted")
            self._task_layout.addWidget(empty_label)

        for task in tasks:
            task_id = task["id"]

            # Parent task row.
            task_row = QWidget()
            task_row.setObjectName("task_row")
            task_row_layout = QHBoxLayout(task_row)
            task_row_layout.setContentsMargins(8, 4, 8, 4)
            task_row_layout.setSpacing(6)

            checkbox = QCheckBox(task["title"])
            checkbox.setChecked(task["completed_at"] is not None)

            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(2)

            subtask_button = QPushButton("≡")
            subtask_button.setObjectName("action_btn")
            subtask_button.setToolTip("Show or hide subtasks")
            subtask_button.setFixedSize(26, 26)

            support_button = QPushButton("◎")
            support_button.setObjectName("action_btn")
            support_button.setFixedSize(26, 26)
            linked_goals = self._weekly_repository.goal_ids_for_task(task_id)
            linked_titles = [
                weekly_goal_titles[goal_id]
                for goal_id in linked_goals
                if goal_id in weekly_goal_titles
            ]
            if linked_titles:
                support_button.setText(f"◎{len(linked_titles)}")
                support_button.setProperty("has_content", "true")
            support_button.setToolTip(
                "Supports: " + ", ".join(linked_titles)
                if linked_titles
                else "Choose supporting weekly objectives"
            )

            task_notes_button = QPushButton("✎")
            task_notes_button.setObjectName("action_btn")
            task_notes_button.setToolTip("Show or hide task notes")
            task_notes_button.setFixedSize(26, 26)
            task_notes = self._task_repository.get_task_notes(task_id)
            if task_notes and task_notes.strip():
                task_notes_button.setProperty("has_content", "true")

            carry_button = QPushButton("↪")
            carry_button.setObjectName("action_btn")
            carry_button.setFixedSize(26, 26)

            already_carried_forward = task_id in carried_task_ids
            can_carry_forward = (
                    task["completed_at"] is None
                    and not already_carried_forward
            )

            carry_button.setEnabled(can_carry_forward)

            if already_carried_forward:
                carry_button.setToolTip(
                    f"Already carried forward to {tomorrow}"
                )
                carry_button.setVisible(False)
            elif task["completed_at"] is not None:
                carry_button.setToolTip("Completed tasks cannot be carried forward")
                carry_button.setVisible(False)
            else:
                carry_button.setToolTip("Carry unfinished task forward to tomorrow")

            delete_button = QPushButton("×")
            delete_button.setObjectName("delete_action_btn")
            delete_button.setToolTip("Delete task")
            delete_button.setFixedSize(26, 26)

            task_row_layout.addWidget(checkbox, 1)
            actions_layout.addWidget(task_notes_button)
            actions_layout.addWidget(subtask_button)
            actions_layout.addWidget(support_button)
            actions_layout.addWidget(carry_button)
            actions_layout.addWidget(delete_button)
            task_row_layout.addLayout(actions_layout)

            carry_button.clicked.connect(
                lambda _checked=False, current_id=task_id, button=carry_button:
                self._carry_task_forward(current_id, button)
            )

            delete_button.clicked.connect(
                lambda _checked=False, current_id=task_id:
                self._delete_task(current_id)
            )
            support_button.clicked.connect(
                lambda _checked=False, current_id=task_id:
                self._edit_task_support(current_id)
            )

            self._task_layout.addWidget(task_row)

            # Expandable notes panel for this task.
            task_notes_panel = QFrame()
            task_notes_panel.setObjectName("task_card")
            task_notes_layout = QVBoxLayout(task_notes_panel)
            task_notes_layout.setContentsMargins(16, 6, 8, 8)

            task_notes_input = QPlainTextEdit()
            task_notes_input.setPlaceholderText("Notes for this task...")
            task_notes_input.setFixedHeight(75)

            task_notes_layout.addWidget(task_notes_input)
            task_notes_panel.hide()

            self._task_notes_panels[task_id] = task_notes_panel

            self._task_note_inputs[task_id] = task_notes_input
            self._task_notes_buttons[task_id] = task_notes_button

            task_notes_input.textChanged.connect(
                lambda current_id=task_id:
                self._schedule_item_notes_save("task", current_id)
            )

            task_notes_button.clicked.connect(
                lambda _checked=False, panel=task_notes_panel,
                       button=task_notes_button, current_id=task_id:
                self._toggle_item_notes(panel, button, current_id)
            )

            self._task_layout.addWidget(task_notes_panel)

            # Load previously saved notes without triggering a save.
            task_notes_input.blockSignals(True)
            task_notes_input.setPlainText(
                self._task_repository.get_task_notes(task_id)
            )
            task_notes_input.blockSignals(False)

            self._task_checkboxes.append(checkbox)
            self._task_ids.append(task_id)

            checkbox.toggled.connect(
                lambda checked, current_id=task_id:
                self._on_task_toggled(current_id, checked)
            )

            # Expandable subtask panel.
            container = QFrame()
            container.setObjectName("task_card")
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(16, 6, 8, 8)
            container_layout.setSpacing(5)
            container.hide()

            self._subtask_containers[task_id] = container
            self._subtask_layouts[task_id] = container_layout
            self._subtask_buttons[task_id] = subtask_button

            input_row = QWidget()
            input_layout = QHBoxLayout(input_row)
            input_layout.setContentsMargins(0, 4, 0, 0)

            subtask_input = QLineEdit()
            subtask_input.setPlaceholderText("Add a subtask...")
            subtask_input.returnPressed.connect(
                lambda current_id=task_id:
                self._add_subtask_from_input(current_id)
            )

            add_subtask_button = QPushButton("+")
            add_subtask_button.setObjectName("pill_btn")
            add_subtask_button.setFixedSize(26, 26)
            add_subtask_button.setToolTip("Add subtask")
            add_subtask_button.clicked.connect(
                lambda _checked=False, current_id=task_id:
                self._add_subtask_from_input(current_id)
            )

            input_layout.addWidget(subtask_input)
            input_layout.addWidget(add_subtask_button)
            container_layout.addWidget(input_row)

            self._subtask_inputs[task_id] = subtask_input


            subtask_button.clicked.connect(
                lambda _checked=False, current_id=task_id:
                self._toggle_subtasks(current_id)
            )

            self._task_layout.addWidget(container)

            # Populate the panel from SQLite.
            self._load_subtasks(task_id)

        self._update_progress()
        self._load_weekly_goals()

    def _week_start(self) -> date:
        selected = date.fromisoformat(self._today)
        return selected - timedelta(days=(selected.weekday() + 1) % 7)

    def _load_weekly_goals(self) -> None:
        while self._weekly_layout.count():
            item = self._weekly_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        goals = self._weekly_repository.get_goals(self._week_start())
        if not goals:
            label = QLabel("No objectives for this week yet.")
            label.setObjectName("muted")
            self._weekly_layout.addWidget(label)
        for goal in goals:
            row = QHBoxLayout()
            check = QCheckBox(goal["title"])
            check.setChecked(goal["completed_at"] is not None)
            check.toggled.connect(lambda value, goal_id=goal["id"]: self._set_weekly_goal(goal_id, value))
            progress = QLabel(f'{goal["completed_tasks"] or 0}/{goal["task_count"]} actions' if goal["task_count"] else "No supporting actions")
            progress.setObjectName("muted")
            edit = QPushButton("✎")
            edit.setObjectName("action_btn")
            edit.setToolTip("Edit objective")
            edit.setFixedSize(24, 24)
            edit.clicked.connect(lambda _=False, goal_id=goal["id"], title=goal["title"]: self._edit_weekly_goal(goal_id, title))
            delete = QPushButton("×")
            delete.setObjectName("delete_action_btn")
            delete.setToolTip("Delete objective")
            delete.setFixedSize(24, 24)
            delete.clicked.connect(lambda _=False, goal_id=goal["id"]: self._delete_weekly_goal(goal_id))
            row.addWidget(check, 1)
            row.addWidget(progress)
            row.addWidget(edit)
            row.addWidget(delete)
            container = QWidget()
            container.setObjectName("weekly_goal_card")
            row.setContentsMargins(7, 3, 5, 3)
            row.setSpacing(5)
            container.setLayout(row)
            self._weekly_layout.addWidget(container)
        QTimer.singleShot(0, self._adjust_window_height)

    def _add_weekly_goal(self) -> None:
        title = self._weekly_input.text().strip()
        if title:
            self._weekly_repository.add_goal(self._week_start(), title)
            self._weekly_input.clear()
            self._load_weekly_goals()

    def _set_weekly_goal(self, goal_id: int, completed: bool) -> None:
        self._weekly_repository.set_completed(goal_id, completed)
        self._load_weekly_goals()

    def _edit_task_support(self, task_id: int) -> None:
        goals = self._weekly_repository.get_goals(self._week_start())
        if not goals:
            QMessageBox.information(self, "Weekly objectives", "Add a weekly objective first.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Supporting objectives")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("This daily task supports:"))
        selected = self._weekly_repository.goal_ids_for_task(task_id)
        boxes = {}
        for goal in goals:
            box = QCheckBox(goal["title"])
            box.setChecked(goal["id"] in selected)
            boxes[goal["id"]] = box
            layout.addWidget(box)
        buttons = QHBoxLayout()
        save = QPushButton("Save")
        cancel = QPushButton("Cancel")
        save.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            for goal_id, box in boxes.items():
                self._weekly_repository.set_task_support(goal_id, task_id, box.isChecked())
            self._load_weekly_goals()

    def _edit_weekly_goal(self, goal_id: int, title: str) -> None:
        edited, accepted = QInputDialog.getText(self, "Edit objective", "Objective", text=title)
        if accepted and edited.strip():
            self._weekly_repository.update_goal(goal_id, edited)
            self._load_weekly_goals()

    def _delete_weekly_goal(self, goal_id: int) -> None:
        if QMessageBox.question(self, "Delete objective", "Hide this objective from the plan? Its history and supporting links are retained; daily tasks remain.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self._weekly_repository.delete_goal(goal_id)
            self._load_weekly_goals()

    def _load_subtasks(self, task_id: int) -> None:
        """Rebuild one task's subtask list from SQLite."""
        panel_layout = self._subtask_layouts[task_id]

        # Preserve the final input row while replacing the list.
        while panel_layout.count() > 1:
            item = panel_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        subtasks = self._task_repository.get_subtasks_for_task(
            task_id
        )

        completed = sum(
            item["completed_at"] is not None
            for item in subtasks
        )
        total = len(subtasks)

        button = self._subtask_buttons[task_id]
        expanded = self._subtask_containers[task_id].isVisible()

        button.setText("≡")
        button.setToolTip(
            f"{'Hide' if expanded else 'Show'} subtasks "
            f"({completed}/{total} completed)"
        )

        for subtask in subtasks:
            subtask_id = subtask["id"]
            checkbox = QCheckBox(subtask["title"])
            checkbox.setChecked(subtask["completed_at"] is not None)

            panel_layout.insertWidget(
                panel_layout.count() - 1,
                checkbox,
            )

            checkbox.toggled.connect(
                lambda checked, current_id=subtask_id,
                parent_id=task_id:
                self._on_subtask_toggled(
                    parent_id, current_id, checked
                )
            )

    def _adjust_window_height(self) -> None:
        """Resize the window to fit its visible content."""
        window_layout = self.layout()
        if window_layout is None:
            return

        if window_layout.count() == 0:
            return

        root_widget = window_layout.itemAt(0).widget()
        if root_widget is None or root_widget.layout() is None:
            return

        content_layout = root_widget.layout()
        content_layout.activate()
        window_layout.activate()

        desired_height = window_layout.sizeHint().height()

        screen = self.screen()
        if screen is not None:
            available_height = screen.availableGeometry().height()
            max_height = available_height - 40
        else:
            max_height = 900

        desired_height = max(
            MIN_WINDOW_HEIGHT,
            min(desired_height, max_height),
        )

        if self.height() != desired_height:
            self.resize(self.width(), desired_height)

    def _toggle_item_notes(
            self,
            panel: QFrame,
            button: QPushButton,
            task_id: int,
    ) -> None:
        """Toggle task notes and close its subtask panel."""
        expanded = not panel.isVisible()

        if expanded:
            self._subtask_containers[task_id].hide()

            subtask_button = self._subtask_buttons[task_id]
            subtask_button.setProperty("expanded", False)
            subtask_button.style().unpolish(subtask_button)
            subtask_button.style().polish(subtask_button)

        panel.setVisible(expanded)
        button.setProperty("expanded", expanded)

        button.style().unpolish(button)
        button.style().polish(button)

        self._adjust_window_height()

    def _toggle_subtasks(self, task_id: int) -> None:
        """Toggle subtasks and close that task's notes panel."""
        container = self._subtask_containers[task_id]
        expanded = not container.isVisible()

        if expanded:
            notes_panel = self._task_notes_panels.get(task_id)
            if notes_panel is not None:
                notes_panel.hide()

            notes_button = self._task_notes_buttons.get(task_id)
            if notes_button is not None:
                notes_button.setProperty("expanded", False)
                notes_button.style().unpolish(notes_button)
                notes_button.style().polish(notes_button)

        container.setVisible(expanded)

        button = self._subtask_buttons[task_id]
        button.setProperty("expanded", expanded)
        button.style().unpolish(button)
        button.style().polish(button)

        self._load_subtasks(task_id)
        self._adjust_window_height()

    def _on_subtask_toggled(
        self,
        task_id: int,
        subtask_id: int,
        completed: bool,
    ) -> None:
        """Save a subtask's completion state."""
        self._task_repository.set_subtask_completed(
            subtask_id,
            completed,
        )
        self._load_subtasks(task_id)
        self._update_progress()
        self._load_weekly_goals()

    def _add_subtask_from_input(self, task_id: int) -> None:
        """Save a new subtask for the selected parent task."""
        field = self._subtask_inputs[task_id]
        title = field.text().strip()

        if not title:
            return

        self._task_repository.add_subtask(task_id, title)
        field.clear()
        self._load_subtasks(task_id)
        self._update_progress()
        QTimer.singleShot(0, self._adjust_window_height)

    def _delete_task(self, task_id: int) -> None:
        """Ask for confirmation before deleting a task."""
        reply = QMessageBox.question(
            self,
            "Delete task",
            "Are you sure you want to delete this task?\n\n"
            "Its subtasks and notes will also be deleted.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Stop pending autosaves for this task and its subtasks.
        timer_keys = [f"task:{task_id}"]

        subtasks = self._task_repository.get_subtasks_for_task(task_id)
        timer_keys.extend(
            f"subtask:{subtask['id']}" for subtask in subtasks
        )

        for key in timer_keys:
            timer = self._item_notes_timers.pop(key, None)
            if timer is not None:
                timer.stop()
                timer.deleteLater()

        task = self._task_repository.get_task_by_id(task_id)
        notion_id = task.get("notion_id") if task else None
        deleted = self._task_repository.delete_task(task_id)

        if deleted:
            if notion_id:
                if hasattr(self, "_notion_sync"):
                    self._notion_sync.push_delete_async(
                        task_id,
                        notion_id,
                        self._task_repository,
                    )
            else:
                self._task_repository.remove_sync_actions_for_task(task_id)
            self._load_tasks()
            self._update_progress()

    def _carry_task_forward(
            self,
            task_id: int,
            button: QPushButton,
    ) -> None:
        """Copy an unfinished task to the following day."""
        target_date = (
                date.fromisoformat(self._today) + timedelta(days=1)
        ).isoformat()

        old_task = self._task_repository.get_task_by_id(task_id)
        old_notion_id = old_task.get("notion_id") if old_task else None

        copied_task_id = self._task_repository.carry_task_forward(
            task_id,
            target_date,
        )

        if copied_task_id is None:
            button.setToolTip(
                "Task could not be carried forward. "
                "It may be completed or already copied."
            )
            return

        if old_task and hasattr(self, "_notion_sync"):
            self._notion_sync.push_carry_forward_async(
                old_notion_id,
                copied_task_id,
                old_task["title"],
                target_date,
                self._task_repository,
                notes=old_task.get("notes", ""),
            )

        button.setEnabled(False)
        button.setToolTip(f"Carried forward to {target_date}")

    def _add_task_from_input(self) -> None:
        """Save the text in the input field as a new daily task."""
        title = self._task_input.text().strip()
        if not title:
            return

        new_id = self._task_repository.add_task(title, self._today)
        if hasattr(self, "_notion_sync"):
            self._notion_sync.push_add_task_async(
                new_id, title, self._today, self._task_repository
            )
        self._task_input.clear()
        self._load_tasks()
        QTimer.singleShot(0, self._adjust_window_height)

    def _on_task_toggled(
        self,
        task_id: int,
        completed: bool,
    ) -> None:
        """Save task completion and synchronize all its subtasks."""
        self._task_repository.set_completed(task_id, completed)

        task = self._task_repository.get_task_by_id(task_id)
        if hasattr(self, "_notion_sync"):
            self._notion_sync.push_status_async(
                task_id,
                task.get("notion_id") if task else None,
                completed,
                self._task_repository,
            )

        # Completing or reopening a task also updates every subtask.
        subtasks = self._task_repository.get_subtasks_for_task(
            task_id
        )
        for subtask in subtasks:
            self._task_repository.set_subtask_completed(
                subtask["id"],
                completed,
            )

        # Refresh the subtask count and checkbox states.
        self._load_subtasks(task_id)
        self._update_progress()

    def _update_progress(self, *_args: object) -> None:
        """Refresh task and subtask completion counts."""
        total = len(self._task_checkboxes)
        completed = sum(
            checkbox.isChecked()
            for checkbox in self._task_checkboxes
        )
        percentage = round(completed / total * 100) if total else 0

        self.progress_label.setText(
            f"{completed} of {total} tasks completed · {percentage}%"
        )
        self.progress_bar.setValue(percentage)

        subtasks = [
            subtask
            for task_id in self._task_ids
            for subtask in self._task_repository.get_subtasks_for_task(
                task_id
            )
        ]

        completed_subtasks = sum(
            subtask["completed_at"] is not None
            for subtask in subtasks
        )
        total_subtasks = len(subtasks)

        self.subtask_progress_label.setText(
            f"{completed_subtasks} of {total_subtasks} subtasks completed"
        )

    def _apply_accent(self, color: str) -> None:
        """Apply the latest wallpaper-derived accent to the application."""
        self._navigation.set_accent(color)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet(color))

    def closeEvent(self, event) -> None:
        """Stop the all activity  when the window closes."""
        self._notes_save_timer.stop()
        self._focus_timer.stop()
        self._flush_item_notes()
        self._save_notes()
        if self._wallpaper_watcher is not None:
            self._wallpaper_watcher.stop()

        super().closeEvent(event)

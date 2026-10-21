
"""Main floating window for Dayglass."""

from datetime import date, timedelta

from PySide6.QtCore import QDate, QPoint, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
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
from dayglass.services.wallpaper_watcher import WallpaperWatcher
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


class MainWindow(QWidget):
    """A compact, draggable daily-planner window."""

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        watch_wallpaper: bool = True,
    ) -> None:
        super().__init__()

        self._task_repository = task_repository or TaskRepository()
        self._today = date.today().isoformat()

        self._notes_repository = NotesRepository()
        self._notes_save_timer = QTimer(self)
        self._notes_save_timer.setSingleShot(True)
        self._notes_save_timer.setInterval(800)
        self._notes_save_timer.timeout.connect(self._save_notes)

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

        date_navigation = QHBoxLayout()
        date_navigation.setSpacing(8)

        self._previous_day_button = QPushButton("‹")
        self._previous_day_button.setFixedSize(32, 30)
        self._previous_day_button.setToolTip("Previous day")
        self._previous_day_button.clicked.connect(
            self._go_to_previous_day
        )

        self._date_label = QLabel()
        self._date_label.setObjectName("muted")
        self._date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._calendar_button = QPushButton("▦")
        self._calendar_button.setFixedSize(32, 30)
        self._calendar_button.setToolTip("Choose a date")
        self._calendar_button.clicked.connect(
            self._open_date_picker
        )

        self._today_button = QPushButton("Today")
        self._today_button.setFixedHeight(30)
        self._today_button.clicked.connect(self._go_to_today)

        self._next_day_button = QPushButton("›")
        self._next_day_button.setFixedSize(32, 30)
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

        section_title = QLabel("Today's focus")
        section_title.setStyleSheet(
            "font-size: 16px; font-weight: 600;"
        )
        layout.addWidget(section_title)

        self.progress_label = QLabel()
        self.progress_label.setObjectName("muted")
        self.subtask_progress_label = QLabel()
        self.subtask_progress_label.setObjectName("muted")
        layout.addWidget(self.subtask_progress_label)
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # Tasks are added here dynamically from the repository.
        task_card = QFrame()
        task_card.setObjectName("task_card")
        self._task_layout = QVBoxLayout(task_card)
        self._task_layout.setContentsMargins(10, 8, 10, 8)
        self._task_layout.setSpacing(4)
        layout.addWidget(task_card)

        # Input for creating a task.
        input_layout = QHBoxLayout()
        self._task_input = QLineEdit()
        self._task_input.setPlaceholderText("Add a task for today...")
        self._task_input.returnPressed.connect(
            self._add_task_from_input
        )

        self._add_task_button = QPushButton("Add")
        self._add_task_button.clicked.connect(
            self._add_task_from_input
        )

        input_layout.addWidget(self._task_input)
        input_layout.addWidget(self._add_task_button)
        layout.addLayout(input_layout)

        # Daily scratchpad.
        scratchpad_title = QLabel("Scratchpad")
        scratchpad_title.setStyleSheet(
            "font-size: 16px; font-weight: 600;"
        )
        layout.addWidget(scratchpad_title)

        self._notes_input = QPlainTextEdit()
        self._notes_input.setPlaceholderText(
            "Jot down thoughts, reminders, or ideas..."
        )
        self._notes_input.setFixedHeight(100)
        self._notes_input.textChanged.connect(
            self._schedule_notes_save
        )
        layout.addWidget(self._notes_input)

        layout.addStretch()

        note = QLabel("Small steps. Steady progress.")

        note.setObjectName("muted")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(note)


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
                self._task_repository.save_task_notes(
                    item_id,
                    field.toPlainText(),
                )
        elif item_type == "subtask":
            field = self._subtask_note_inputs.get(item_id)
            if field is not None:
                self._task_repository.save_subtask_notes(
                    item_id,
                    field.toPlainText(),
                )

    def _save_notes(self) -> None:
        """Persist the current scratchpad contents."""
        self._notes_repository.save_notes(
            self._today,
            self._notes_input.toPlainText(),
        )

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
        self._change_selected_date(date.today().isoformat())

    def _change_selected_date(self, selected_date: str) -> None:
        """Switch the displayed tasks and notes to another date."""
        if selected_date == self._today:
            return

        self._today = selected_date
        self._update_date_label()
        self._load_tasks()
        self._load_notes()

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

    def _load_tasks(self) -> None:
        """Load today's tasks and their expandable subtasks."""
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
            task_row_layout = QHBoxLayout(task_row)
            task_row_layout.setContentsMargins(0, 0, 0, 0)

            checkbox = QCheckBox(task["title"])
            checkbox.setChecked(task["completed_at"] is not None)

            subtask_button = QPushButton("≡")
            subtask_button.setToolTip("Show or hide subtasks")
            subtask_button.setFixedSize(30, 28)

            task_notes_button = QPushButton("✎")
            task_notes_button.setToolTip("Show or hide task notes")
            task_notes_button.setFixedSize(30, 28)

            carry_button = QPushButton("↪")
            carry_button.setFixedSize(30, 28)

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
            elif task["completed_at"] is not None:
                carry_button.setToolTip("Completed tasks cannot be carried forward")
            else:
                carry_button.setToolTip("Carry unfinished task forward to tomorrow")

            delete_button = QPushButton("×")
            delete_button.setToolTip("Delete task")
            delete_button.setFixedSize(30, 28)

            task_row_layout.addWidget(checkbox, 1)
            task_row_layout.addWidget(task_notes_button)
            task_row_layout.addWidget(subtask_button)
            task_row_layout.addWidget(checkbox, 1)
            task_row_layout.addWidget(task_notes_button)
            task_row_layout.addWidget(subtask_button)
            task_row_layout.addWidget(carry_button)
            task_row_layout.addWidget(delete_button)

            carry_button.clicked.connect(
                lambda _checked=False, current_id=task_id, button=carry_button:
                self._carry_task_forward(current_id, button)
            )

            delete_button.clicked.connect(
                lambda _checked=False, current_id=task_id:
                self._delete_task(current_id)
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
            add_subtask_button.setFixedWidth(32)
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

        deleted = self._task_repository.delete_task(task_id)

        if deleted:
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

        button.setEnabled(False)
        button.setToolTip(f"Carried forward to {target_date}")

    def _add_task_from_input(self) -> None:
        """Save the text in the input field as a new daily task."""
        title = self._task_input.text().strip()
        if not title:
            return

        self._task_repository.add_task(title, self._today)
        self._task_input.clear()
        self._load_tasks()

    def _on_task_toggled(
        self,
        task_id: int,
        completed: bool,
    ) -> None:
        """Save task completion and synchronize all its subtasks."""
        self._task_repository.set_completed(task_id, completed)

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
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet(color))

    def closeEvent(self, event) -> None:
        """Stop the all activity  when the window closes."""
        self._notes_save_timer.stop()
        self._save_notes()
        if self._wallpaper_watcher is not None:
            self._wallpaper_watcher.stop()

        super().closeEvent(event)

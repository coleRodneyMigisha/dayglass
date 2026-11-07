
"""Tests for the Dayglass interface and database integration."""

import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QCheckBox
from PySide6.QtTest import QTest

from dayglass.database.task_repository import TaskRepository
from dayglass.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def app():
    """Create one Qt application for the test session."""
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def repository(tmp_path):
    """Give each test an isolated SQLite database."""
    return TaskRepository(tmp_path / "test_dayglass.sqlite3")


def test_main_window_initializes(app, repository):
    """A fresh database should produce an empty checklist."""
    window = MainWindow(
        task_repository=repository,
        watch_wallpaper=False,
    )

    assert window.windowTitle() == "Dayglass"
    assert len(window._task_checkboxes) == 0
    assert window.progress_bar.value() == 0
    assert "0 of 0 tasks completed" in window.progress_label.text()

    window.close()


def test_progress_updates_when_task_is_checked(app, repository):
    """Checking a task updates progress and saves its state."""
    today = date.today()
    first_id = repository.add_task("Practise Python", today)
    repository.add_task("Review notes", today)
    repository.add_task("Work on Dayglass", today)
    repository.add_task("Plan tomorrow", today)

    window = MainWindow(
        task_repository=repository,
        watch_wallpaper=False,
    )

    window._task_checkboxes[0].setChecked(True)

    assert window.progress_bar.value() == 25
    assert "1 of 4 tasks completed" in window.progress_label.text()

    saved_tasks = repository.get_tasks_for_date(today)
    saved_first_task = next(
        task for task in saved_tasks if task["id"] == first_id
    )
    assert saved_first_task["completed_at"] is not None

    window.close()


def test_added_task_survives_reopening(app, repository):
    """Tasks should remain in SQLite after a window is reopened."""
    window = MainWindow(
        task_repository=repository,
        watch_wallpaper=False,
    )

    window._task_input.setText("Finish the database integration")
    window._add_task_from_input()

    assert len(window._task_checkboxes) == 1
    assert window._task_checkboxes[0].text() == (
        "Finish the database integration"
    )
    window.close()

    reopened_window = MainWindow(
        task_repository=repository,
        watch_wallpaper=False,
    )

    assert len(reopened_window._task_checkboxes) == 1
    assert reopened_window._task_checkboxes[0].text() == (
        "Finish the database integration"
    )

    reopened_window.close()


def test_weekly_objective_is_visible_and_persists_with_injected_database(
    app, repository
):
    window = MainWindow(task_repository=repository, watch_wallpaper=False)
    window._weekly_input.setText("Finish the first model")
    window._add_weekly_goal()

    assert window._weekly_layout.count() == 1
    assert "Finish the first model" in window._weekly_layout.itemAt(0).widget().findChild(QCheckBox).text()
    window._notes_input.setPlainText("Keep this note")
    window.close()

    reopened = MainWindow(task_repository=repository, watch_wallpaper=False)
    assert reopened._weekly_layout.count() == 1
    assert reopened._notes_repository.get_notes(reopened._today) == "Keep this note"
    reopened.close()


def test_focus_countdown_stops_at_zero_and_can_reset(app, repository):
    import time

    window = MainWindow(task_repository=repository, watch_wallpaper=False)
    window._focus_deadline = time.monotonic() - 1
    window._update_focus_timer()
    assert window._focus_label.text() == "00:00"
    assert window._focus_start_button.text() == "Start focus"
    window._reset_focus_timer()
    assert window._focus_label.text() == "25:00"
    window.close()


def test_focus_is_a_separate_screen_with_bottom_pill_navigation(app, repository):
    window = MainWindow(task_repository=repository, watch_wallpaper=False)
    assert window._screen_stack.count() == 2
    assert window._screen_stack.currentIndex() == 0

    window._navigation._buttons[1].click()
    assert window._screen_stack.currentIndex() == 1
    assert window._navigation._buttons[1].isChecked()
    assert window._navigation._fill_animation is not None
    QTest.qWait(500)
    assert window._navigation._pill.geometry() == (
        window._navigation._buttons[1].geometry()
    )
    assert window._navigation._pill.get_fill_level() >= 0.99

    window._navigation._buttons[0].click()
    assert window._screen_stack.currentIndex() == 0
    QTest.qWait(500)
    assert window._navigation._pill.geometry() == (
        window._navigation._buttons[0].geometry()
    )
    window.close()


def test_date_navigation_flushes_scratchpad_before_loading_another_day(
    app, repository
):
    window = MainWindow(task_repository=repository, watch_wallpaper=False)
    first_day = window._today
    second_day = "2026-12-31" if first_day != "2026-12-31" else "2026-12-30"
    window._notes_input.setPlainText("First day's note")
    window._change_selected_date(second_day)
    assert window._notes_repository.get_notes(first_day) == "First day's note"
    assert window._notes_input.toPlainText() == ""
    window.close()


def test_close_flushes_task_note_autosave(app, repository):
    task_id = repository.add_task("Write a note", date.today())
    window = MainWindow(task_repository=repository, watch_wallpaper=False)
    window._task_note_inputs[task_id].setPlainText("Saved on close")

    window.close()

    assert repository.get_task_notes(task_id) == "Saved on close"


"""Tests for the Dayglass interface and database integration."""

import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

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

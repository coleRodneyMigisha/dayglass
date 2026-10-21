
"""Tests for notes attached to tasks and subtasks."""

from datetime import date

import pytest

from dayglass.database.task_repository import TaskRepository


@pytest.fixture
def repository(tmp_path):
    """Create an isolated database for each test."""
    return TaskRepository(tmp_path / "item_notes.sqlite3")


def test_new_task_has_empty_notes(repository):
    task_id = repository.add_task("Build the UI", date.today())

    assert repository.get_task_notes(task_id) == ""


def test_save_and_retrieve_task_notes(repository):
    task_id = repository.add_task("Build the UI", date.today())

    repository.save_task_notes(task_id, "Start with the layout.")

    assert repository.get_task_notes(task_id) == "Start with the layout."


def test_saving_task_notes_updates_existing_notes(repository):
    task_id = repository.add_task("Build the UI", date.today())

    repository.save_task_notes(task_id, "First idea")
    repository.save_task_notes(task_id, "Revised plan")

    assert repository.get_task_notes(task_id) == "Revised plan"


def test_new_subtask_has_empty_notes(repository):
    task_id = repository.add_task("Build the UI", date.today())
    subtask_id = repository.add_subtask(task_id, "Create the header")

    assert repository.get_subtask_notes(subtask_id) == ""


def test_save_and_retrieve_subtask_notes(repository):
    task_id = repository.add_task("Build the UI", date.today())
    subtask_id = repository.add_subtask(task_id, "Create the header")

    repository.save_subtask_notes(
        subtask_id,
        "Use a draggable title bar.",
    )

    assert repository.get_subtask_notes(subtask_id) == (
        "Use a draggable title bar."
    )


def test_task_and_subtask_notes_are_independent(repository):
    task_id = repository.add_task("Build the UI", date.today())
    subtask_id = repository.add_subtask(task_id, "Create the header")

    repository.save_task_notes(task_id, "Overall implementation plan")
    repository.save_subtask_notes(subtask_id, "Header-specific details")

    assert repository.get_task_notes(task_id) == (
        "Overall implementation plan"
    )
    assert repository.get_subtask_notes(subtask_id) == (
        "Header-specific details"
    )


def test_empty_notes_can_be_saved(repository):
    task_id = repository.add_task("Build the UI", date.today())
    repository.save_task_notes(task_id, "Temporary note")

    repository.save_task_notes(task_id, "")

    assert repository.get_task_notes(task_id) == ""

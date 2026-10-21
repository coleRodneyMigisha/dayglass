
"""Tests for Dayglass subtask storage."""

from datetime import date

import pytest

from dayglass.database.task_repository import TaskRepository


@pytest.fixture
def repository(tmp_path):
    """Create an isolated database for each test."""
    return TaskRepository(tmp_path / "subtasks.sqlite3")


@pytest.fixture
def parent_task(repository):
    """Create a task that can own subtasks."""
    return repository.add_task(
        "Build Dayglass",
        date.today(),
    )


def test_add_and_retrieve_subtasks(repository, parent_task):
    """Subtasks should be returned in their display order."""
    first_id = repository.add_subtask(
        parent_task,
        "Design the schema",
    )
    second_id = repository.add_subtask(
        parent_task,
        "Write the tests",
    )

    subtasks = repository.get_subtasks_for_task(parent_task)

    assert [item["id"] for item in subtasks] == [
        first_id,
        second_id,
    ]
    assert [item["title"] for item in subtasks] == [
        "Design the schema",
        "Write the tests",
    ]
    assert all(item["completed_at"] is None for item in subtasks)


def test_subtask_completion_can_be_changed(repository, parent_task):
    """Completing and uncompleting a subtask should persist."""
    subtask_id = repository.add_subtask(
        parent_task,
        "Write the tests",
    )

    assert repository.set_subtask_completed(subtask_id, True)

    subtask = repository.get_subtasks_for_task(parent_task)[0]
    assert subtask["completed_at"] is not None

    assert repository.set_subtask_completed(subtask_id, False)

    subtask = repository.get_subtasks_for_task(parent_task)[0]
    assert subtask["completed_at"] is None


def test_subtasks_are_isolated_by_parent(repository):
    """A task should only retrieve its own subtasks."""
    today = date.today()
    first_task = repository.add_task("First task", today)
    second_task = repository.add_task("Second task", today)

    repository.add_subtask(first_task, "First subtask")
    repository.add_subtask(second_task, "Second subtask")

    assert [
        item["title"]
        for item in repository.get_subtasks_for_task(first_task)
    ] == ["First subtask"]


def test_blank_subtask_title_is_rejected(repository, parent_task):
    """Subtask titles must contain non-whitespace characters."""
    with pytest.raises(ValueError):
        repository.add_subtask(parent_task, "   ")


def test_missing_subtask_returns_false(repository):
    """Updating a nonexistent subtask should report failure."""
    assert not repository.set_subtask_completed(999999, True)

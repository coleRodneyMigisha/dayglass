
"""Tests for the daily task repository."""

from datetime import date

import pytest

from dayglass.database.task_repository import TaskRepository


def test_tasks_are_saved_and_retrieved_in_order(tmp_path):
    """Tasks should persist and follow their assigned display order."""

    repository = TaskRepository(tmp_path / "tasks.sqlite3")
    today = date(2026, 10, 20)

    first_id = repository.add_task("Practise Python", today)
    second_id = repository.add_task("Review notes", today)

    tasks = repository.get_tasks_for_date(today)

    assert [task["title"] for task in tasks] == [
        "Practise Python",
        "Review notes",
    ]
    assert tasks[0]["id"] == first_id
    assert tasks[1]["id"] == second_id
    assert tasks[0]["position"] < tasks[1]["position"]


def test_completion_can_be_set_and_cleared(tmp_path):
    """Completing a task sets a timestamp; unchecking clears it."""

    repository = TaskRepository(tmp_path / "tasks.sqlite3")
    task_id = repository.add_task("Practise Python", "2026-10-20")

    assert repository.set_completed(task_id, True) is True

    task = repository.get_tasks_for_date("2026-10-20")[0]
    assert task["completed_at"] is not None
    assert task["completed_at"].endswith("+00:00")

    assert repository.set_completed(task_id, False) is True

    task = repository.get_tasks_for_date("2026-10-20")[0]
    assert task["completed_at"] is None


def test_empty_task_titles_are_rejected(tmp_path):
    """Tasks should not be created with blank titles."""

    repository = TaskRepository(tmp_path / "tasks.sqlite3")

    with pytest.raises(ValueError):
        repository.add_task("   ", "2026-10-20")


def test_tasks_are_separated_by_date(tmp_path):
    """Retrieving one day should not return another day's tasks."""

    repository = TaskRepository(tmp_path / "tasks.sqlite3")

    repository.add_task("Today's task", "2026-10-20")
    repository.add_task("Tomorrow's task", "2026-10-21")

    tasks = repository.get_tasks_for_date("2026-10-20")

    assert len(tasks) == 1
    assert tasks[0]["title"] == "Today's task"


def test_completing_missing_task_returns_false(tmp_path):
    """Updating an unknown task ID should report that nothing changed."""

    repository = TaskRepository(tmp_path / "tasks.sqlite3")

    assert repository.set_completed(99999, True) is False


def test_carry_task_forward_preserves_task_and_subtask_data(tmp_path):
    """Carrying a task forward copies its data without changing the original."""

    repository = TaskRepository(tmp_path / "tasks.sqlite3")
    original_date = "2026-10-20"
    target_date = "2026-10-21"

    task_id = repository.add_task("Practise Python", original_date)
    repository.save_task_notes(task_id, "Finish the recursion exercises.")

    completed_subtask_id = repository.add_subtask(
        task_id, "Review functions"
    )
    unfinished_subtask_id = repository.add_subtask(
        task_id, "Practise recursion"
    )

    repository.save_subtask_notes(
        completed_subtask_id, "Already reviewed."
    )
    repository.save_subtask_notes(
        unfinished_subtask_id, "Start with a simple example."
    )
    repository.set_subtask_completed(completed_subtask_id, True)

    copied_task_id = repository.carry_task_forward(task_id, target_date)

    assert copied_task_id is not None
    assert copied_task_id != task_id

    original_tasks = repository.get_tasks_for_date(original_date)
    copied_tasks = repository.get_tasks_for_date(target_date)

    assert len(original_tasks) == 1
    assert original_tasks[0]["id"] == task_id
    assert len(copied_tasks) == 1
    assert copied_tasks[0]["id"] == copied_task_id
    assert copied_tasks[0]["title"] == "Practise Python"
    assert copied_tasks[0]["carried_from_task_id"] == task_id

    assert repository.get_task_notes(task_id) == (
        "Finish the recursion exercises."
    )
    assert repository.get_task_notes(copied_task_id) == (
        "Finish the recursion exercises."
    )

    original_subtasks = repository.get_subtasks_for_task(task_id)
    copied_subtasks = repository.get_subtasks_for_task(copied_task_id)

    assert [item["title"] for item in copied_subtasks] == [
        "Review functions",
        "Practise recursion",
    ]
    assert copied_subtasks[0]["completed_at"] is not None
    assert copied_subtasks[1]["completed_at"] is None

    assert repository.get_subtask_notes(copied_subtasks[0]["id"]) == (
        "Already reviewed."
    )
    assert repository.get_subtask_notes(copied_subtasks[1]["id"]) == (
        "Start with a simple example."
    )

    # Carrying the task forward must not alter its original subtasks.
    assert original_subtasks[0]["completed_at"] is not None
    assert original_subtasks[1]["completed_at"] is None


def test_completed_task_cannot_be_carried_forward(tmp_path):
    """A completed parent task should not be copied to another day."""

    repository = TaskRepository(tmp_path / "tasks.sqlite3")
    task_id = repository.add_task("Finish assignment", "2026-10-20")
    repository.set_completed(task_id, True)

    result = repository.carry_task_forward(task_id, "2026-10-21")

    assert result is None
    assert repository.get_tasks_for_date("2026-10-21") == []


def test_task_cannot_be_carried_forward_twice_to_same_date(tmp_path):
    """The same original task should not be copied twice to one date."""

    repository = TaskRepository(tmp_path / "tasks.sqlite3")
    task_id = repository.add_task("Practise Python", "2026-10-20")

    first_copy_id = repository.carry_task_forward(
        task_id, "2026-10-21"
    )
    second_copy_id = repository.carry_task_forward(
        task_id, "2026-10-21"
    )

    assert first_copy_id is not None
    assert second_copy_id is None
    assert len(repository.get_tasks_for_date("2026-10-21")) == 1


def test_missing_task_cannot_be_carried_forward(tmp_path):
    """An unknown task ID should not create a copied task."""

    repository = TaskRepository(tmp_path / "tasks.sqlite3")

    result = repository.carry_task_forward(99999, "2026-10-21")

    assert result is None
    assert repository.get_tasks_for_date("2026-10-21") == []


def test_task_cannot_be_carried_forward_to_its_own_date(tmp_path):
    """A task should not be duplicated onto its existing date."""

    repository = TaskRepository(tmp_path / "tasks.sqlite3")
    task_id = repository.add_task("Practise Python", "2026-10-20")

    result = repository.carry_task_forward(task_id, "2026-10-20")

    assert result is None
    assert len(repository.get_tasks_for_date("2026-10-20")) == 1



def test_delete_task_removes_it_from_its_date(tmp_path):
    """Deleting an existing task removes it and reports success."""

    repository = TaskRepository(tmp_path / "tasks.sqlite3")
    task_id = repository.add_task("Practise Python", "2026-10-20")

    assert repository.delete_task(task_id) is True
    assert repository.get_tasks_for_date("2026-10-20") == []


def test_deleting_missing_task_returns_false(tmp_path):
    """Deleting an unknown task ID reports that nothing changed."""

    repository = TaskRepository(tmp_path / "tasks.sqlite3")

    assert repository.delete_task(99999) is False


def test_deleting_task_removes_its_subtasks_and_notes(tmp_path):
    """Deleting a task also deletes its subtasks and their notes."""

    repository = TaskRepository(tmp_path / "tasks.sqlite3")
    task_id = repository.add_task("Complete assignment", "2026-10-20")
    subtask_id = repository.add_subtask(task_id, "Write introduction")

    repository.save_task_notes(task_id, "Assignment notes")
    repository.save_subtask_notes(subtask_id, "Subtask notes")

    assert repository.delete_task(task_id) is True
    assert repository.get_subtasks_for_task(task_id) == []
    assert repository.get_task_notes(task_id) == ""
    assert repository.get_subtask_notes(subtask_id) == ""


def test_deleting_original_task_preserves_carried_forward_copy(tmp_path):
    """A copied task survives deletion of its original task."""

    repository = TaskRepository(tmp_path / "tasks.sqlite3")
    original_id = repository.add_task("Practise Python", "2026-10-20")
    copied_id = repository.carry_task_forward(
        original_id, "2026-10-21"
    )

    assert copied_id is not None
    assert repository.delete_task(original_id) is True

    remaining_tasks = repository.get_tasks_for_date("2026-10-21")
    assert len(remaining_tasks) == 1
    assert remaining_tasks[0]["id"] == copied_id
    assert remaining_tasks[0]["title"] == "Practise Python"
    assert remaining_tasks[0]["carried_from_task_id"] is None

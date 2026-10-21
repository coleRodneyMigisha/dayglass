
"""Database operations for daily tasks."""

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterator

from dayglass.database.connection import (
    get_connection,
    get_database_path,
)
from dayglass.database.schema import initialize_database


class TaskRepository:
    """Create, retrieve, and update daily tasks."""

    def __init__(
        self,
        database_path: str | Path | None = None,
    ) -> None:
        self._database_path = (
            Path(database_path)
            if database_path is not None
            else get_database_path()
        )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Open an initialized database connection for one operation."""

        connection = get_connection(self._database_path)

        try:
            initialize_database(connection)
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _normalize_date(task_date: date | str) -> str:
        """Validate a date and return its ISO representation."""

        if isinstance(task_date, datetime):
            raise TypeError("Use a date, not a datetime, for task_date.")

        if isinstance(task_date, date):
            return task_date.isoformat()

        return date.fromisoformat(task_date).isoformat()

    def add_task(
        self,
        title: str,
        task_date: date | str,
        position: int | None = None,
        carried_from_task_id: int | None = None,
    ) -> int:
        """Create a task and return its new database ID."""

        title = title.strip()

        if not title:
            raise ValueError("Task title cannot be empty.")

        normalized_date = self._normalize_date(task_date)

        with self._connection() as connection:
            if position is None:
                row = connection.execute(
                    """
                    SELECT COALESCE(MAX(position), -1) + 1
                    AS next_position
                    FROM tasks
                    WHERE task_date = ?
                    """,
                    (normalized_date,),
                ).fetchone()
                position = row["next_position"]

            cursor = connection.execute(
                """
                INSERT INTO tasks (
                    title,
                    task_date,
                    position,
                    carried_from_task_id
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    title,
                    normalized_date,
                    position,
                    carried_from_task_id,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def get_tasks_for_date(
        self,
        task_date: date | str,
    ) -> list[dict]:
        """Return all tasks for a date, in display order."""

        normalized_date = self._normalize_date(task_date)

        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    title,
                    task_date,
                    position,
                    completed_at,
                    carried_from_task_id,
                    created_at
                FROM tasks
                WHERE task_date = ?
                ORDER BY position, id
                """,
                (normalized_date,),
            ).fetchall()

            return [dict(row) for row in rows]

    def carry_task_forward(
            self,
            task_id: int,
            target_date: date | str,
    ) -> int | None:
        """Copy an unfinished task and its subtasks to another date.

        Return the new task ID, or None if the task is missing,
        already completed, or already carried to the target date.
        """
        normalized_date = self._normalize_date(target_date)

        with self._connection() as connection:
            try:
                connection.execute("BEGIN")

                original = connection.execute(
                    """
                    SELECT id, title, task_date, completed_at, notes
                    FROM tasks
                    WHERE id = ?
                    """,
                    (task_id,),
                ).fetchone()

                if original is None or original["completed_at"] is not None:
                    connection.rollback()
                    return None

                if original["task_date"] == normalized_date:
                    connection.rollback()
                    return None

                existing = connection.execute(
                    """
                    SELECT id
                    FROM tasks
                    WHERE task_date = ?
                      AND carried_from_task_id = ?
                    """,
                    (normalized_date, task_id),
                ).fetchone()

                if existing is not None:
                    connection.rollback()
                    return None

                position_row = connection.execute(
                    """
                    SELECT COALESCE(MAX(position), -1) + 1
                        AS next_position
                    FROM tasks
                    WHERE task_date = ?
                    """,
                    (normalized_date,),
                ).fetchone()

                cursor = connection.execute(
                    """
                    INSERT INTO tasks (
                        title,
                        task_date,
                        position,
                        carried_from_task_id,
                        notes
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        original["title"],
                        normalized_date,
                        position_row["next_position"],
                        task_id,
                        original["notes"],
                    ),
                )
                new_task_id = int(cursor.lastrowid)

                subtasks = connection.execute(
                    """
                    SELECT title, position, completed_at, notes
                    FROM subtasks
                    WHERE task_id = ?
                    ORDER BY position, id
                    """,
                    (task_id,),
                ).fetchall()

                for subtask in subtasks:
                    connection.execute(
                        """
                        INSERT INTO subtasks (
                            task_id,
                            title,
                            position,
                            completed_at,
                            notes
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            new_task_id,
                            subtask["title"],
                            subtask["position"],
                            subtask["completed_at"],
                            subtask["notes"],
                        ),
                    )

                connection.commit()
                return new_task_id

            except Exception:
                connection.rollback()
                raise

    def set_completed(self, task_id: int, completed: bool) -> bool:
        """Set a task's completion state.

        Return True if a task was found, otherwise False.
        """

        if not isinstance(completed, bool):
            raise TypeError("completed must be a bool.")

        completed_at = (
            datetime.now(timezone.utc).isoformat(timespec="seconds")
            if completed
            else None
        )

        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks
                SET completed_at = ?
                WHERE id = ?
                """,
                (completed_at, task_id),
            )
            connection.commit()
            return cursor.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        """Delete a task and its subtasks, returning whether it existed."""
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM tasks WHERE id = ?",
                (task_id,),
            )
            connection.commit()
            return cursor.rowcount > 0

    def add_subtask(self, task_id: int, title: str) -> int:
        """Create a subtask under a parent task and return its ID."""
        title = title.strip()

        if not title:
            raise ValueError("Subtask title cannot be empty.")

        with self._connection() as connection:
            # Determine the next display position for this parent.
            row = connection.execute(
                """
                SELECT COALESCE(MAX(position), -1) + 1 AS next_position
                FROM subtasks
                WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()

            position = row["next_position"]

            cursor = connection.execute(
                """
                INSERT INTO subtasks (task_id, title, position)
                VALUES (?, ?, ?)
                """,
                (task_id, title, position),
            )

            connection.commit()
            return int(cursor.lastrowid)

    def get_subtasks_for_task(self, task_id: int) -> list[dict]:
        """Return a parent's subtasks in display order."""
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    task_id,
                    title,
                    position,
                    completed_at,
                    created_at
                FROM subtasks
                WHERE task_id = ?
                ORDER BY position, id
                """,
                (task_id,),
            ).fetchall()

            return [dict(row) for row in rows]

    def set_subtask_completed(
        self,
        subtask_id: int,
        completed: bool,
    ) -> bool:
        """Update a subtask's completion state."""
        if not isinstance(completed, bool):
            raise TypeError("completed must be a bool.")

        completed_at = (
            datetime.now(timezone.utc).isoformat(timespec="seconds")
            if completed
            else None
        )

        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE subtasks
                SET completed_at = ?
                WHERE id = ?
                """,
                (completed_at, subtask_id),
            )

            connection.commit()
            return cursor.rowcount > 0


    def get_task_notes(self, task_id: int) -> str:
        """Return notes attached to a task."""
        with self._connection() as connection:
            row = connection.execute(
                "SELECT notes FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()

            if row is None:
                return ""

            return row["notes"]

    def save_task_notes(self, task_id: int, content: str) -> bool:
        """Save notes attached to a task."""
        return self._save_item_notes("tasks", task_id, content)

    def get_subtask_notes(self, subtask_id: int) -> str:
        """Return notes attached to a subtask."""
        with self._connection() as connection:
            row = connection.execute(
                "SELECT notes FROM subtasks WHERE id = ?",
                (subtask_id,),
            ).fetchone()

            if row is None:
                return ""

            return row["notes"]

    def save_subtask_notes(
        self,
        subtask_id: int,
        content: str,
    ) -> bool:
        """Save notes attached to a subtask."""
        return self._save_item_notes("subtasks", subtask_id, content)

    def _save_item_notes(
        self,
        table: str,
        item_id: int,
        content: str,
    ) -> bool:
        """Update notes for a task or subtask."""
        if not isinstance(content, str):
            raise TypeError("Notes content must be a string.")

        if table not in {"tasks", "subtasks"}:
            raise ValueError("Unsupported notes table.")

        with self._connection() as connection:
            cursor = connection.execute(
                f"UPDATE {table} SET notes = ? WHERE id = ?",
                (content, item_id),
            )
            connection.commit()
            return cursor.rowcount > 0

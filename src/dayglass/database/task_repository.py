
"""Database operations for daily tasks."""

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
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

    @property
    def database_path(self) -> Path:
        """Path shared with repositories that store related data."""
        return self._database_path

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

    @staticmethod
    def _week_start(task_date: str) -> str:
        """Return the Sunday date for the date's calendar week."""
        day = date.fromisoformat(task_date)
        return (day - timedelta(days=(day.weekday() + 1) % 7)).isoformat()

    def add_task(
        self,
        title: str,
        task_date: date | str,
        position: int | None = None,
        carried_from_task_id: int | None = None,
        notion_id: str | None = None,
        notes: str = "",
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
                    carried_from_task_id,
                    notion_id,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    normalized_date,
                    position,
                    carried_from_task_id,
                    notion_id,
                    notes,
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
                    created_at,
                    notes,
                    notion_id
                FROM tasks
                WHERE task_date = ?
                ORDER BY position, id
                """,
                (normalized_date,),
            ).fetchall()

            return [dict(row) for row in rows]

    def set_notion_id(self, task_id: int, notion_id: str) -> bool:
        """Record the Notion page ID associated with this task."""
        with self._connection() as connection:
            connection.execute(
                "UPDATE tasks SET notion_id = ? WHERE id = ?",
                (notion_id, task_id),
            )
            connection.commit()
            return True

    def get_task_by_id(self, task_id: int) -> dict | None:
        """Retrieve a task by its primary database ID."""
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_task_by_notion_id(self, notion_id: str) -> dict | None:
        """Find a task by its linked Notion page ID."""
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE notion_id = ?",
                (notion_id,),
            ).fetchone()
            return dict(row) if row else None

    def queue_sync_action(
        self,
        action_type: str,
        task_id: int | None,
        payload: dict,
    ) -> int:
        """Record an offline action to be synced with Notion when connected."""
        import json
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO pending_sync_actions (action_type, task_id, payload)
                VALUES (?, ?, ?)
                """,
                (action_type, task_id, json.dumps(payload)),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def get_pending_sync_actions(self) -> list[dict]:
        """Return all pending sync actions in order."""
        import json
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT id, action_type, task_id, payload, created_at, attempts, last_error
                FROM pending_sync_actions
                ORDER BY id ASC
                """
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["payload"] = json.loads(d["payload"]) if d["payload"] else {}
                out.append(d)
            return out

    def remove_sync_action(self, action_id: int) -> None:
        """Remove a successfully synced action from the queue."""
        with self._connection() as connection:
            connection.execute(
                "DELETE FROM pending_sync_actions WHERE id = ?",
                (action_id,),
            )
            connection.commit()

    def remove_sync_actions_for_task(self, task_id: int) -> None:
        """Remove all pending actions for a task (e.g. if deleted before sync)."""
        with self._connection() as connection:
            connection.execute(
                "DELETE FROM pending_sync_actions WHERE task_id = ?",
                (task_id,),
            )
            connection.commit()

    def record_sync_attempt(self, action_id: int, error: str) -> None:
        """Record failed sync attempt for debugging/retry."""
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE pending_sync_actions
                SET attempts = attempts + 1, last_error = ?
                WHERE id = ?
                """,
                (str(error)[:1000], action_id),
            )
            connection.commit()

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

                if self._week_start(original["task_date"]) == self._week_start(
                    normalized_date
                ):
                    connection.execute(
                        """INSERT OR IGNORE INTO weekly_goal_tasks(goal_id, task_id)
                           SELECT goal_id, ? FROM weekly_goal_tasks
                           WHERE task_id = ?""",
                        (new_task_id, task_id),
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

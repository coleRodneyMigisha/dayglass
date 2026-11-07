"""Persistence for week-specific objectives and supporting daily tasks."""

import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, TypeVar

from dayglass.database.connection import get_connection, get_database_path
from dayglass.database.schema import initialize_database

Result = TypeVar("Result")


class WeeklyGoalRepository:
    def __init__(self, database_path: str | Path | None = None) -> None:
        self._database_path = (
            Path(database_path)
            if database_path is not None
            else get_database_path()
        )

    def _run(self, callback: Callable[[sqlite3.Connection], Result]) -> Result:
        connection = get_connection(self._database_path)
        try:
            initialize_database(connection)
            result = callback(connection)
            connection.commit()
            return result
        finally:
            connection.close()

    @staticmethod
    def _week(value: date | str) -> str:
        if isinstance(value, datetime):
            raise TypeError("Use a date, not a datetime.")
        day = date.fromisoformat(value) if isinstance(value, str) else value
        return (day - timedelta(days=(day.weekday() + 1) % 7)).isoformat()

    def add_goal(self, week_start: date | str, title: str) -> int:
        title = title.strip()
        if not title:
            raise ValueError("Objective title cannot be empty.")

        def insert(db):
            cursor = db.execute(
                "INSERT INTO weekly_goals(week_start, title) VALUES (?, ?)",
                (self._week(week_start), title),
            )
            return int(cursor.lastrowid)

        return self._run(insert)

    def get_goals(self, week_start: date | str) -> list[dict]:
        week = self._week(week_start)

        def query(db):
            rows = db.execute(
                """
                SELECT g.id, g.week_start, g.title, g.completed_at,
                    COUNT(t.id) AS task_count,
                    SUM(CASE WHEN t.completed_at IS NOT NULL THEN 1 ELSE 0 END)
                        AS completed_tasks
                FROM weekly_goals g
                LEFT JOIN weekly_goal_tasks l ON l.goal_id = g.id
                LEFT JOIN tasks t ON t.id = l.task_id
                WHERE g.week_start = ? AND g.deleted_at IS NULL
                GROUP BY g.id
                ORDER BY g.id
                """,
                (week,),
            ).fetchall()
            return [dict(row) for row in rows]

        return self._run(query)

    def update_goal(self, goal_id: int, title: str) -> bool:
        title = title.strip()
        if not title:
            raise ValueError("Objective title cannot be empty.")
        return self._run(
            lambda db: db.execute(
                "UPDATE weekly_goals SET title = ? WHERE id = ?",
                (title, goal_id),
            ).rowcount
            > 0
        )

    def set_completed(self, goal_id: int, completed: bool) -> bool:
        if not isinstance(completed, bool):
            raise TypeError("completed must be a bool.")
        stamp = (
            datetime.now(timezone.utc).isoformat(timespec="seconds")
            if completed
            else None
        )
        return self._run(
            lambda db: db.execute(
                "UPDATE weekly_goals SET completed_at = ? WHERE id = ?",
                (stamp, goal_id),
            ).rowcount
            > 0
        )

    def delete_goal(self, goal_id: int) -> bool:
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return self._run(
            lambda db: db.execute(
                """UPDATE weekly_goals SET deleted_at = ?
                   WHERE id = ? AND deleted_at IS NULL""",
                (stamp, goal_id),
            ).rowcount
            > 0
        )

    def set_task_support(self, goal_id: int, task_id: int, supported: bool) -> None:
        if supported:
            self._run(
                lambda db: db.execute(
                    """INSERT OR IGNORE INTO weekly_goal_tasks(goal_id, task_id)
                       VALUES (?, ?)""",
                    (goal_id, task_id),
                )
            )
        else:
            self._run(
                lambda db: db.execute(
                    "DELETE FROM weekly_goal_tasks WHERE goal_id = ? AND task_id = ?",
                    (goal_id, task_id),
                )
            )

    def goal_ids_for_task(self, task_id: int) -> set[int]:
        return self._run(
            lambda db: {
                row[0]
                for row in db.execute(
                    "SELECT goal_id FROM weekly_goal_tasks WHERE task_id = ?",
                    (task_id,),
                )
            }
        )

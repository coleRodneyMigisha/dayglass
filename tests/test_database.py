
"""Tests for database setup and schema initialization."""

import sqlite3

from dayglass.database.connection import get_connection
from dayglass.database.schema import initialize_database


def test_database_creates_file_and_tables(tmp_path):
    """Initialization should create the database and its tables."""

    database_path = tmp_path / "dayglass.sqlite3"
    connection = get_connection(database_path)

    try:
        initialize_database(connection)

        tables = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }

        assert database_path.exists()
        assert {
            "tasks",
            "subtasks",
            "daily_notes",
            "weekly_goals",
            "focus_sessions",
        }.issubset(tables)
    finally:
        connection.close()


def test_schema_initialization_is_safe_to_repeat(tmp_path):
    """Running initialization twice should preserve existing records."""

    connection = get_connection(tmp_path / "dayglass.sqlite3")

    try:
        initialize_database(connection)

        connection.execute(
            """
            INSERT INTO tasks (title, task_date)
            VALUES (?, ?)
            """,
            ("Practise Python", "2026-10-20"),
        )
        connection.commit()

        initialize_database(connection)

        count = connection.execute(
            "SELECT COUNT(*) FROM tasks"
        ).fetchone()[0]

        assert count == 1
    finally:
        connection.close()


def test_foreign_keys_are_enforced(tmp_path):
    """A subtask must belong to an existing task."""

    connection = get_connection(tmp_path / "dayglass.sqlite3")

    try:
        initialize_database(connection)

        try:
            connection.execute(
                """
                INSERT INTO subtasks (task_id, title)
                VALUES (?, ?)
                """,
                (99999, "An orphaned subtask"),
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError(
                "SQLite allowed a subtask without a parent task"
            )
    finally:
        connection.close()

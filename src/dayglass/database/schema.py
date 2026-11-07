
"""Database schema creation and migrations for Dayglass."""

import sqlite3


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create tables and apply safe schema migrations."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL
                CHECK (length(trim(title)) > 0),
            task_date TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT,
            carried_from_task_id INTEGER,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (carried_from_task_id)
                REFERENCES tasks(id)
                ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_date_position
            ON tasks(task_date, position);

        CREATE TABLE IF NOT EXISTS subtasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            title TEXT NOT NULL
                CHECK (length(trim(title)) > 0),
            position INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id)
                REFERENCES tasks(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS daily_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_date TEXT NOT NULL UNIQUE,
            content TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS weekly_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start TEXT NOT NULL,
            title TEXT NOT NULL
                CHECK (length(trim(title)) > 0),
            completed_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_weekly_goals_week
            ON weekly_goals(week_start);

        CREATE TABLE IF NOT EXISTS weekly_goal_tasks (
            goal_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            PRIMARY KEY (goal_id, task_id),
            FOREIGN KEY (goal_id) REFERENCES weekly_goals(id)
                ON DELETE CASCADE,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS focus_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            duration_seconds INTEGER NOT NULL DEFAULT 0
                CHECK (duration_seconds >= 0),
            FOREIGN KEY (task_id)
                REFERENCES tasks(id)
                ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS pending_sync_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            task_id INTEGER,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT
        );
        """
    )

    # Add columns to databases created by earlier versions of Dayglass.
    _add_column_if_missing(
        connection,
        "tasks",
        "notes",
        "TEXT NOT NULL DEFAULT ''",
    )

    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_weekly_goal_tasks_task "
        "ON weekly_goal_tasks(task_id)"
    )
    _add_column_if_missing(
        connection,
        "subtasks",
        "notes",
        "TEXT NOT NULL DEFAULT ''",
    )
    _add_column_if_missing(
        connection,
        "weekly_goals",
        "deleted_at",
        "TEXT",
    )
    _add_column_if_missing(
        connection,
        "tasks",
        "notion_id",
        "TEXT",
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_notion_id "
        "ON tasks(notion_id)"
    )

    connection.commit()


def _add_column_if_missing(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    """Add a column only when it does not already exist."""
    existing_columns = {
        row["name"]
        for row in connection.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    }

    if column not in existing_columns:
        connection.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )

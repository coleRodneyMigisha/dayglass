
"""SQLite connection management for Dayglass."""

import os
import sqlite3
from pathlib import Path


def get_database_path() -> Path:
    """Return the user's local Dayglass database path."""

    data_home = Path(
        os.environ.get(
            "XDG_DATA_HOME",
            str(Path.home() / ".local" / "share"),
        )
    )
    return data_home / "dayglass" / "dayglass.sqlite3"


def get_connection(
    database_path: str | Path | None = None,
) -> sqlite3.Connection:
    """Open a SQLite connection and enable foreign keys."""

    path = (
        Path(database_path)
        if database_path is not None
        else get_database_path()
    )

    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection

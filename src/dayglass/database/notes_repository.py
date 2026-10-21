
"""Database operations for daily scratchpad notes."""

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from dayglass.database.connection import (
    get_connection,
    get_database_path,
)
from dayglass.database.schema import initialize_database


class NotesRepository:
    """Create, retrieve, and update notes for individual days."""

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
        """Open an initialized database connection."""
        connection = get_connection(self._database_path)
        try:
            initialize_database(connection)
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _normalize_date(note_date: date | str) -> str:
        """Validate a date and return its ISO representation."""
        if isinstance(note_date, datetime):
            raise TypeError("Use a date, not a datetime, for note_date.")

        if isinstance(note_date, date):
            return note_date.isoformat()

        return date.fromisoformat(note_date).isoformat()

    def get_notes(self, note_date: date | str) -> str:
        """Return the saved notes for a date, or an empty string."""
        normalized_date = self._normalize_date(note_date)

        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT content
                FROM daily_notes
                WHERE note_date = ?
                """,
                (normalized_date,),
            ).fetchone()

            return row["content"] if row is not None else ""

    def save_notes(
        self,
        note_date: date | str,
        content: str,
    ) -> None:
        """Save or update the notes for a particular date."""
        if not isinstance(content, str):
            raise TypeError("Notes content must be a string.")

        normalized_date = self._normalize_date(note_date)

        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO daily_notes (note_date, content, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(note_date)
                DO UPDATE SET
                    content = excluded.content,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (normalized_date, content),
            )
            connection.commit()

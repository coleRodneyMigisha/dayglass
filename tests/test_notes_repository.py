
"""Tests for Dayglass daily scratchpad notes."""

from datetime import date, timedelta

import pytest

from dayglass.database.notes_repository import NotesRepository


@pytest.fixture
def repository(tmp_path):
    """Create an isolated database for each test."""
    return NotesRepository(tmp_path / "notes.sqlite3")


def test_new_day_has_empty_notes(repository):
    """A date without saved notes should return an empty string."""
    assert repository.get_notes(date.today()) == ""


def test_save_and_retrieve_notes(repository):
    """Saved notes should be retrievable for the same date."""
    today = date.today()
    content = "Remember to review the database design."

    repository.save_notes(today, content)

    assert repository.get_notes(today) == content


def test_saving_notes_updates_existing_entry(repository):
    """Saving again should update rather than duplicate a day's notes."""
    today = date.today()

    repository.save_notes(today, "First draft")
    repository.save_notes(today, "Revised draft")

    assert repository.get_notes(today) == "Revised draft"


def test_notes_are_separate_for_each_day(repository):
    """Notes from one date must not overwrite another date."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    repository.save_notes(today, "Today's thoughts")
    repository.save_notes(yesterday, "Yesterday's thoughts")

    assert repository.get_notes(today) == "Today's thoughts"
    assert repository.get_notes(yesterday) == "Yesterday's thoughts"


def test_empty_notes_can_be_saved(repository):
    """The user should be able to clear their scratchpad."""
    today = date.today()

    repository.save_notes(today, "Temporary note")
    repository.save_notes(today, "")

    assert repository.get_notes(today) == ""

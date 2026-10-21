
"""Tests for wallpaper colour extraction."""

from PIL import Image
from unittest.mock import patch
from dayglass.services.wallpaper_watcher import get_wallpaper_path
from dayglass.services.wallpaper import (
    DEFAULT_ACCENT,
    extract_dominant_color,
)


def test_extracts_color_from_solid_wallpaper(tmp_path):
    """A solid-colour image should return its colour."""

    image_path = tmp_path / "wallpaper.png"
    Image.new("RGB", (40, 40), (30, 120, 200)).save(image_path)

    result = extract_dominant_color(image_path)

    assert result == "#1e78c8"


def test_missing_wallpaper_uses_fallback(tmp_path):
    """An unreadable wallpaper should not crash the application."""

    image_path = tmp_path / "missing.jpg"

    result = extract_dominant_color(image_path)

    assert result == DEFAULT_ACCENT


def test_get_wallpaper_path_reads_gnome_file_uri():
    """GNOME's file URI should become a normal local path."""

    completed = type(
        "CompletedProcess",
        (),
        {"stdout": "'file:///tmp/my%20wallpaper.jpg'\n"},
    )()

    with patch(
        "dayglass.services.wallpaper_watcher.subprocess.run",
        return_value=completed,
    ):
        result = get_wallpaper_path()

    assert result == __import__("pathlib").Path(
        "/tmp/my wallpaper.jpg"
    )


def test_get_wallpaper_path_handles_gsettings_failure():
    """A settings error should not crash Dayglass."""

    import subprocess

    with patch(
        "dayglass.services.wallpaper_watcher.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "gsettings"),
    ):
        assert get_wallpaper_path() is None

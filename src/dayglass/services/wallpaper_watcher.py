
"""Watch GNOME settings for desktop wallpaper changes."""

import ast
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse

from PySide6.QtCore import QObject, QProcess, Signal

from dayglass.services.wallpaper import (
    DEFAULT_ACCENT,
    extract_dominant_color,
)


def get_wallpaper_path() -> Path | None:
    """Return the local path of GNOME's current regular wallpaper."""

    try:
        result = subprocess.run(
            [
                "gsettings",
                "get",
                "org.gnome.desktop.background",
                "picture-uri",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=3,
        )

        uri = ast.literal_eval(result.stdout.strip())
        parsed = urlparse(uri)

        if parsed.scheme != "file":
            return None

        return Path(unquote(parsed.path))

    except (
        OSError,
        subprocess.SubprocessError,
        ValueError,
        SyntaxError,
    ):
        return None


class WallpaperWatcher(QObject):
    """Emit a new accent colour whenever the wallpaper changes."""

    accent_changed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._monitor = QProcess(self)

        self._monitor.readyReadStandardOutput.connect(
            self._on_settings_changed
        )

    def start(self) -> None:
        """Read the current wallpaper and begin monitoring GNOME."""

        self._refresh_accent()

        if self._monitor.state() != QProcess.ProcessState.NotRunning:
            return

        self._monitor.start(
            "gsettings",
            ["monitor", "org.gnome.desktop.background", "picture-uri"],
        )

    def stop(self) -> None:
        """Stop the background settings monitor."""

        if self._monitor.state() != QProcess.ProcessState.NotRunning:
            self._monitor.terminate()

            if not self._monitor.waitForFinished(1000):
                self._monitor.kill()

    def _on_settings_changed(self) -> None:
        """Recalculate the accent after a wallpaper setting changes."""

        self._monitor.readAllStandardOutput()
        self._refresh_accent()

    def _refresh_accent(self) -> None:
        """Extract and publish the current wallpaper's dominant colour."""

        wallpaper = get_wallpaper_path()

        accent = (
            extract_dominant_color(wallpaper)
            if wallpaper is not None
            else DEFAULT_ACCENT
        )

        self.accent_changed.emit(accent)

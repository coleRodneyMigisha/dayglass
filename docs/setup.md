# Development Setup

## Requirements

- Ubuntu or a compatible Linux desktop
- Python 3.14 or another version supported by the selected dependencies
- pip
- Git

## Create a virtual environment

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Run Dayglass with `python -m dayglass.main` and run tests with `pytest -q`.
Tests use temporary SQLite databases and Qt's offscreen platform where
needed.

## Ubuntu desktop installation

From the checkout, run `bash scripts/install_desktop.sh`. The installer
copies the application source into `~/.local/share/dayglass/app`, creates
a private virtual environment there, installs the declared dependencies,
and writes a launcher, icon, command, and login startup entry. The startup
entry is `~/.config/autostart/dayglass.desktop` (or under `$XDG_CONFIG_HOME`
if set); it starts Dayglass when you sign in to your desktop. It does not
start before login or while the computer is powered off. The installer
does not require sudo. This is a source-based per-user installation, not a
standalone binary; Python and pip/network access are needed during
installation. Launch from the application menu or run `dayglass` in a
terminal after installation.

To disable automatic startup but keep the app installed, remove only its
autostart entry:

```bash
rm ~/.config/autostart/dayglass.desktop
```

The app remains available from the application menu and `dayglass` command.

Uninstall with `bash scripts/uninstall_desktop.sh`. It removes the app
files, launcher, icon, command shim, and autostart entry, but leaves
`~/.local/share/dayglass` user data intact. The installation script refuses to replace an existing
installation; uninstall first (data is preserved), then install the update.

## Data, migrations, and backups

The default database is `~/.local/share/dayglass/dayglass.sqlite3`, or
`$XDG_DATA_HOME/dayglass/dayglass.sqlite3` when `XDG_DATA_HOME` is set.
Schema changes are additive and initialized idempotently. Weekly objectives
are keyed to the Sunday date in Africa/Kampala's calendar. A first launch
after Sunday 18:00 immediately shows the current week's plan; no timer or
resident background process is required. Notifications are not implemented.

To make a backup, close Dayglass and copy the database file to a safe
location. To restore, close the app and put the copy back at the same path.
Keep backups before replacing an installation. The uninstaller never
deletes the database. The first migration introducing weekly objectives
creates new tables and preserves existing task, note, and completion rows.

## Troubleshooting

- Run `dayglass` in a terminal to see Python or Qt startup errors.
- If the menu entry is missing, log out and in or refresh the desktop menu;
  confirm `~/.local/share/applications/dayglass.desktop` exists.
- On headless systems, set `QT_QPA_PLATFORM=offscreen` for automated checks;
  this does not provide interactive desktop use.
- GNOME wallpaper accent detection is optional and falls back to the
  built-in accent when `gsettings` or the image is unavailable.
- If Dayglass does not start at login, check that
  `~/.config/autostart/dayglass.desktop` exists and that its `Exec` path
  points to the installed virtual environment. Login startup occurs after
  the next sign-in; there is no need to enable a system service.

See [How Dayglass works](how_it_works.md) for the application flow,
weekly objective behavior, timer lifecycle, and storage overview.

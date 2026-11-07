# Dayglass

Dayglass is a minimalist floating daily planner for Ubuntu.

It is designed to help users plan their days, track progress, and
maintain a practical record of their work.

## Features

- Daily tasks with individually checkable subtasks
- Automatic carry-forward of unfinished tasks
- A persistent notes scratchpad
- Daily and task-specific notes with autosaving
- Wallpaper-derived accent color on GNOME
- Sunday-based weekly objectives with supporting daily tasks
- Daily completion and subtask progress
- Draggable, resizable floating window with date navigation
- 25-minute focus timer with pause, resume, and reset
- Daily completion state retained in task history
- Two-way live synchronization with Notion Personal HQ
- Weekly planning time: Sunday at 18:00 Africa/Kampala; first launch
  catches up automatically, but there is no background reminder
- Local SQLite storage
- Ubuntu per-user desktop launcher installer
- SQLite migrations and automated tests

## Technology

- Python
- PySide6
- SQLite
- pytest

## Development status

Dayglass is a local-first application under active development. Weekly
planning is selected by the Sunday-starting week of the displayed date;
the current week is available on first launch even if the application
was closed at Sunday 18:00 Africa/Kampala. No background reminder is
currently installed.

## Development setup

See [docs/setup.md](docs/setup.md) for environment setup instructions.
For a feature and data-flow overview, see
[How Dayglass works](docs/how_it_works.md).

## Install and launch (Ubuntu)

From a source checkout, install a per-user launcher and login startup entry
with:

```bash
bash scripts/install_desktop.sh
```

The launcher appears in the application menu. To remove the launcher and
installed application files while retaining user data:

```bash
bash scripts/uninstall_desktop.sh
```

The installer starts Dayglass automatically when you sign in to your
desktop. See [docs/setup.md](docs/setup.md) to disable autostart without
uninstalling the app.

The development launch command is `python -m dayglass.main` with `src`
on `PYTHONPATH`, or `PYTHONPATH=src python -m dayglass.main` from this
repository. See [docs/setup.md](docs/setup.md) for data and backup details.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the application structure
and [docs/decisions.md](docs/decisions.md) for the rationale behind
important technical choices.

## License

A license will be selected before the first public release.

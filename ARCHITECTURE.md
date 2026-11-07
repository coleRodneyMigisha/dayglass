# Dayglass Architecture

Dayglass is a local-first Python/PySide6 planner with a SQLite store.
The UI handles presentation and input, repositories own database access,
and small services handle optional wallpaper detection. The UI currently
coordinates daily and weekly actions; business rules for dates and
objective persistence reside in repositories.

## Modules

- `dayglass.ui`: floating window, task/subtask interaction, notes, weekly
  objectives, and a lightweight focus countdown.
- `dayglass.database`: SQLite path/connection handling, idempotent schema
  initialization, daily tasks, notes, and weekly objective repositories.
- `dayglass.services`: GNOME wallpaper lookup and color extraction.
- `dayglass.main`: QApplication startup and event loop.

SQLite connections enable foreign keys. Daily task carry-forward creates a
new record with copied subtasks and notes, preserving the original day's
record. Supporting-objective links are copied in the same transaction when
the carry-forward stays inside that objective's week. Deleting a task
cascades to subtasks and objective links;
deleting an objective hides it while preserving its title, final state,
and supporting links for historical accuracy.

Weekly membership uses Sundays in `Africa/Kampala`. The week containing
the selected date is shown; the 18:00 Sunday planning time is a convention,
not a background reminder. First launch after that time catches up by
showing the current week's records. The focus timer uses a monotonic clock,
works while minimized, and resets on app restart; focus sessions are not
recorded.

Tests use pytest, temporary SQLite files, and Qt offscreen mode. The
per-user Ubuntu installation uses a private virtual environment and
`.desktop` file without changing system Python or requiring sudo.

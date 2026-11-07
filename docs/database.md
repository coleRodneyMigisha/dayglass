# SQLite storage

The default file is `$XDG_DATA_HOME/dayglass/dayglass.sqlite3`, falling
back to `~/.local/share/dayglass/dayglass.sqlite3`. Connections enable
foreign keys. Repositories initialize the schema idempotently before use.

## Tables

- `tasks` stores one dated daily action, completion timestamp, notes, and
  an optional carry-forward source. Carry-forward copies the task and its
  subtasks while leaving the source intact.
- `subtasks` belong to a task and cascade when that task is deleted.
- `daily_notes` stores one scratchpad per calendar date.
- `weekly_goals` stores distinct objective records keyed to the Sunday
  date that starts the week. Editing/deleting a goal affects only that
  record; prior weeks are retained. Deleting hides an objective by setting
  `deleted_at`, preserving its title, final state, and links for history.
- `weekly_goal_tasks` associates objectives with daily task records.
  It permits multiple objectives per task and multiple tasks per objective.
  Deleting a task removes its association; deleting an objective preserves
  its associations for historical accuracy but hides it from the plan.
- `focus_sessions` is reserved in the schema; the countdown does not yet
  record focus sessions.

## Migration and recovery

Schema setup uses `CREATE TABLE IF NOT EXISTS` and additive column checks.
The weekly feature adds its association table and index without rewriting
existing records. Initialization can be repeated safely. There is no
destructive migration. Back up the database with Dayglass closed before
upgrading; restore by replacing the file while the app is closed. The
per-user uninstaller removes application files only, never the data folder.

Repository tests use temporary files. They cover an older task schema,
confirming existing task IDs and rows remain available after initialization.

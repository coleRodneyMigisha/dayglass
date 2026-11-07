# How Dayglass works

Dayglass is a local desktop planner. The graphical window is built with
PySide6, and its tasks, notes, and weekly objectives are stored in one
SQLite database on your computer. It does not send this information to an
online service.

## Starting the application

The `dayglass` command enters through `dayglass.main`. It creates a Qt
application, applies the shared stylesheet, creates the main window, and
starts Qt's event loop. The event loop handles drawing, clicks, keyboard
input, timers, and window events. The window contains two screens: Plan for
daily work and weekly objectives, and Focus for a 25-minute countdown.

The Ubuntu installer creates a private Python environment under
`~/.local/share/dayglass/app`, a menu launcher, an icon, and a command at
`~/.local/bin/dayglass`. It also installs a per-user login startup entry
at `~/.config/autostart/dayglass.desktop`. The entry starts Dayglass after
you sign in to the desktop; it does not run before login or while the
computer is powered off. Remove that entry to disable automatic startup,
or use the uninstaller to remove all Dayglass integration files.

## What happens when you use Plan

The window selects the current date using `Africa/Kampala`. The date
controls can move to earlier or later dates or open the calendar. For the
selected day, the UI asks the task repository for daily tasks, subtasks,
and completion state. The repository reads and writes SQLite; the UI does
not issue its own SQL.

Checking a task or subtask saves its completion timestamp. Progress labels
are recalculated from those saved states. An unfinished task can be carried
to the next day. Carry-forward creates a new task record and copies its
subtasks and notes; the original record remains in that day's history. A
task can support one or more objectives from its current week. Those links
are copied when a task is carried within the same week.

The scratchpad is saved for the selected date after a short pause in typing
and when the window closes or the date changes. Task and subtask notes use
the same delayed-save approach. Opening a task's notes closes its subtask
panel, and opening the subtask panel closes its notes panel.

## Weekly objectives

An objective is a separate record for one Sunday-starting week. Week dates
are derived consistently in `Africa/Kampala`; changing the selected day
shows objectives belonging to that date's week. A new week has its own
records, so earlier weeks remain available when navigating to their dates.
Sunday at 18:00 is the intended weekly planning time. There is no
background reminder: if Dayglass was closed then, the current week's plan
is available the next time it opens.

Daily tasks linked to an objective give a completed-actions count. That
count is informational and does not complete the objective. The objective
has its own checkbox, which is a deliberate user action. An objective with
no linked tasks says “No supporting actions.” Deleting an objective hides
it from the active plan while retaining its record and links for history;
deleting a task removes its task notes, subtasks, and objective links.

## Focus screen

The Focus screen uses a monotonic clock to count down 25 minutes. Start,
pause, resume, and reset are handled in the running application. The timer
continues while the window is minimized, but the session is not saved. If
Dayglass closes or restarts, the timer begins again at 25 minutes. There is
currently no completion sound, notification, or focus-session history.

## Storage and recovery

The default database path is
`~/.local/share/dayglass/dayglass.sqlite3`, or
`$XDG_DATA_HOME/dayglass/dayglass.sqlite3` when `XDG_DATA_HOME` is set.
Repositories initialize the SQLite schema before database operations and
enable foreign-key checks. Schema setup is repeatable and adds new columns
or tables without replacing existing task and note records.

Close Dayglass before backing up the database. Copy the `.sqlite3` file to
a safe location; to restore it, close the app and replace the current file
with the backup. The desktop uninstaller removes the app and its launch
integration but deliberately keeps the database and user data.

## Theme and window appearance

The window is translucent and uses the shared Qt stylesheet for its glass
surfaces, controls, and navigation animation. Where available, GNOME
wallpaper colors provide an accent. If wallpaper lookup fails, Dayglass
uses its built-in accent. The operating-system compositor controls how
transparency appears; Qt styles do not blur arbitrary desktop content.

## Development and checks

UI code is in `src/dayglass/ui`, SQLite repositories and schema setup are
in `src/dayglass/database`, and optional wallpaper integration is in
`src/dayglass/services`. Run the test suite with `pytest -q` from the
project environment. Tests use temporary databases and Qt's offscreen
platform so they do not use the normal user database.

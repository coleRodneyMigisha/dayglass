# Architecture Decision Records

This document records important technical decisions and their rationale.

## ADR-001: Use Python and PySide6

**Decision:** Build the desktop application with Python and PySide6.

**Reason:** Python fits the project's learning goals. PySide6 provides
native desktop widgets, signals, timers, and control over window behavior.

**Trade-off:** A polished translucent interface may behave differently
between desktop environments and display servers.

## ADR-002: Use SQLite

**Decision:** Store application data in a local SQLite database.

**Reason:** Tasks and subtasks have relationships, while daily history,
weekly goals, and focus sessions benefit from structured persistence.

**Trade-off:** Database schema changes must be handled carefully as the
application evolves.

## ADR-003: Separate UI, services, and storage

**Decision:** Keep graphical components, business logic, and persistence
in separate modules.

**Reason:** This makes individual features easier to test, repair, and
extend without rewriting unrelated functionality.

**Trade-off:** The initial project contains more files than a single-script
application.

## ADR-004: Use pytest

**Decision:** Use pytest for automated tests.

**Reason:** Tests help catch regressions as features are added.

## ADR-005: Keep personal data local

**Decision:** Store personal tasks, notes, and history locally.

**Reason:** Dayglass should work offline and should not accidentally
publish personal information when the source code is pushed to GitHub.

## ADR-006: Sunday-starting weekly objectives

**Decision:** Store each week's objectives separately using the Sunday
calendar date in `Africa/Kampala`, with explicit links to daily tasks.

**Reason:** Week membership is stable across machine timezone settings and
application restarts. Tasks can support multiple outcomes. Objective
completion remains a manual decision; task progress is informative only.

**Trade-off:** There is no scheduled reminder or background daemon. On
first launch, Dayglass immediately displays the week containing the current
Kampala date. Sunday 18:00 is the intended planning time, not an alarm.

## ADR-007: Per-user source installation

**Decision:** Install the Python app into a private virtual environment
under the user's XDG data directory and register a local `.desktop` file.

**Reason:** This avoids system Python modifications and does not require
sudo. The application has a dedicated subdirectory, separate from its data.

**Trade-off:** Installation needs Python 3.14+, pip, and dependency access;
it is not a self-contained binary bundle.

## ADR-008: Start the app at desktop sign-in

**Decision:** The per-user installer adds a freedesktop autostart entry
under `$XDG_CONFIG_HOME/autostart` (default `~/.config/autostart`).

**Reason:** Dayglass should be ready as a normal desktop app after the user
signs in, without a system service, sudo, or a terminal window.

**Trade-off:** This only runs after desktop login. It does not run while
the user is logged out or the computer is off. The uninstaller removes
this app-specific entry and preserves the database.

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

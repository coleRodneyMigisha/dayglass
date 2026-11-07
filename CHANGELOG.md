# Changelog

This file records verified features, fixes, and notable changes to Dayglass.

## Unreleased

### Added

- A translucent floating glass surface, dedicated Plan and Focus screens,
  and a bottom-centered animated liquid-glass navigation pill.
- A consistent frosted-glass treatment for task and objective rows, panels,
  editors, buttons, progress tracks, and scrollbars, guided by
  `glass_morphism.png`.
- Sunday-based weekly objectives with per-week persistence, manual
  completion, multiple supporting task links, and action counts.
- A monotonic 25-minute focus countdown with pause, resume, and reset.
- Per-user Ubuntu launcher installation and app-only uninstall scripts.
- A `docs/how_it_works.md` guide covering application flow, persistence,
  objectives, timer behavior, and recovery.
- Per-user desktop login startup, managed by the installer and uninstaller.

### Fixed

- Injected task repositories share their database path with notes and
  weekly objective persistence.
- Task rows no longer add duplicate controls.
- Carried tasks copy same-week objective links in the same transaction;
  carrying across Sunday keeps the previous week's links historical.
- Current-day selection and week grouping use Africa/Kampala.

## 2026-10-21

### Improved

- Subtask completion counts update immediately after a subtask is checked
  or unchecked.
- The floating window adjusts its height after a subtask is added.
- Task notes and subtasks are mutually exclusive: opening one closes
  the other.
- Carry-forward button state reflects whether a task has already been
  carried forward.
- Task deletion asks for confirmation and removes associated subtasks
  and notes.
- Pending autosave timers for deleted tasks and subtasks are stopped.

### Fixed

- **Window height after adding subtasks:** Qt layout size hints may not
  be updated immediately. Scheduling `_adjust_window_height` with
  `QTimer.singleShot(0, ...)` allows the event loop to process layout
  updates first.
- **Notes remaining open when subtasks were opened:** Task notes panels
  were not registered in `_task_notes_panels`. Registering each panel
  by its task ID allows the subtask toggle to find and hide it.
- **Subtask button visual state:** Refresh the button stylesheet after
  changing its `expanded` property when notes are opened.

### Verification

- Automated test suite: 41 tests passed.
- Manual verification: subtask progress updates, immediate window
  resizing, and notes/subtasks mutual exclusion were confirmed.
- Local Git repository initialized on `main`.
- Initial project checkpoint: `17d958a`.


# Changelog

This file records verified features, fixes, and notable changes to Dayglass.

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


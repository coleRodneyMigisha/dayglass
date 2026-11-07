from datetime import date

from dayglass.database.task_repository import TaskRepository
from dayglass.database.weekly_goal_repository import WeeklyGoalRepository


def test_week_starts_sunday_across_year_boundary():
    assert WeeklyGoalRepository._week(date(2021, 1, 1)) == "2020-12-27"
    assert WeeklyGoalRepository._week(date(2021, 1, 3)) == "2021-01-03"


def test_goals_are_isolated_by_week_and_survive_repository_restart(tmp_path):
    path = tmp_path / "weekly.sqlite3"
    first = WeeklyGoalRepository(path)
    goal_id = first.add_goal("2026-10-18", "Ship a first version")
    first.set_completed(goal_id, True)

    reopened = WeeklyGoalRepository(path)
    assert reopened.get_goals("2026-10-19")[0]["title"] == "Ship a first version"
    assert reopened.get_goals("2026-10-25") == []
    assert reopened.get_goals("2026-10-18")[0]["completed_at"] is not None


def test_task_progress_is_many_to_many_and_never_completes_goal(tmp_path):
    path = tmp_path / "weekly.sqlite3"
    goals = WeeklyGoalRepository(path)
    tasks = TaskRepository(path)
    first = goals.add_goal("2026-10-18", "Build model")
    second = goals.add_goal("2026-10-18", "Write report")
    task_id = tasks.add_task("Prepare dataset", "2026-10-20")
    goals.set_task_support(first, task_id, True)
    goals.set_task_support(second, task_id, True)

    task_copy = tasks.carry_task_forward(task_id, "2026-10-21")
    assert task_copy
    tasks.set_completed(task_id, True)

    rows = goals.get_goals("2026-10-20")
    assert [row["completed_tasks"] for row in rows] == [1, 1]
    assert all(row["completed_at"] is None for row in rows)
    assert goals.goal_ids_for_task(task_copy) == {first, second}

    tasks.set_completed(task_id, False)
    assert goals.get_goals("2026-10-18")[0]["completed_tasks"] == 0


def test_carrying_task_across_sunday_does_not_copy_old_week_link(tmp_path):
    path = tmp_path / "weekly.sqlite3"
    goals = WeeklyGoalRepository(path)
    tasks = TaskRepository(path)
    goal = goals.add_goal("2026-10-18", "Finish this week")
    task = tasks.add_task("Review results", "2026-10-24")
    goals.set_task_support(goal, task, True)

    carried = tasks.carry_task_forward(task, "2026-10-25")

    assert carried is not None
    assert goals.goal_ids_for_task(carried) == set()
    assert goals.get_goals("2026-10-24")[0]["task_count"] == 1


def test_objective_completion_reopens_and_deletion_keeps_tasks(tmp_path):
    path = tmp_path / "weekly.sqlite3"
    goals = WeeklyGoalRepository(path)
    tasks = TaskRepository(path)
    goal = goals.add_goal("2026-10-18", "Write documentation")
    task = tasks.add_task("Draft setup", "2026-10-19")
    goals.set_task_support(goal, task, True)
    goals.set_completed(goal, True)
    assert goals.set_completed(goal, False)
    assert goals.get_goals("2026-10-19")[0]["completed_at"] is None
    assert goals.delete_goal(goal)
    assert goals.get_goals("2026-10-19") == []
    assert tasks.get_tasks_for_date("2026-10-19")[0]["id"] == task
    import sqlite3
    with sqlite3.connect(path) as db:
        row = db.execute("SELECT deleted_at, title FROM weekly_goals WHERE id=?", (goal,)).fetchone()
    assert row[0] is not None and row[1] == "Write documentation"


def test_migration_preserves_existing_tasks_and_notes(tmp_path):
    import sqlite3

    path = tmp_path / "old.sqlite3"
    db = sqlite3.connect(path)
    db.executescript("""CREATE TABLE tasks(id INTEGER PRIMARY KEY, title TEXT NOT NULL,
        task_date TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0,
        completed_at TEXT, carried_from_task_id INTEGER, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE subtasks(id INTEGER PRIMARY KEY, task_id INTEGER NOT NULL, title TEXT NOT NULL,
        position INTEGER NOT NULL DEFAULT 0, completed_at TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE daily_notes(id INTEGER PRIMARY KEY, note_date TEXT NOT NULL UNIQUE,
        content TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE weekly_goals(id INTEGER PRIMARY KEY, week_start TEXT NOT NULL,
        title TEXT NOT NULL, completed_at TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE focus_sessions(id INTEGER PRIMARY KEY, task_id INTEGER, started_at TEXT NOT NULL,
        ended_at TEXT, duration_seconds INTEGER NOT NULL DEFAULT 0);
        INSERT INTO tasks(id,title,task_date,position) VALUES(7,'Legacy','2020-01-02',0);
        INSERT INTO subtasks(id,task_id,title) VALUES(8,7,'Legacy subtask');
        INSERT INTO daily_notes(id,note_date,content) VALUES(9,'2020-01-02','Legacy note');
        INSERT INTO weekly_goals(id,week_start,title,completed_at)
            VALUES(10,'2019-12-29','Legacy objective','2020-01-03T12:00:00+00:00');""")
    db.commit()
    db.close()
    repo = TaskRepository(path)
    assert repo.get_tasks_for_date("2020-01-02")[0]["title"] == "Legacy"
    assert repo.get_task_notes(7) == ""
    assert WeeklyGoalRepository(path).add_goal("2020-01-02", "Legacy week")
    assert WeeklyGoalRepository(path).get_goals("2020-01-02")[0]["id"] == 10
    from dayglass.database.notes_repository import NotesRepository
    assert NotesRepository(path).get_notes("2020-01-02") == "Legacy note"
    assert repo.get_subtasks_for_task(7)[0]["title"] == "Legacy subtask"
    assert repo.get_tasks_for_date("2020-01-02")[0]["id"] == 7

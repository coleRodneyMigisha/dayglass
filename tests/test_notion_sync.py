"""Unit tests for Dayglass Notion sync service."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dayglass.database.task_repository import TaskRepository
from dayglass.services.notion_sync import NotionSyncService, load_notion_config


def test_load_notion_config():
    cfg = load_notion_config()
    assert isinstance(cfg, dict)
    assert "token" in cfg
    assert "tasks_data_source_id" in cfg


def test_notion_sync_service_configuration():
    service = NotionSyncService({"token": "ntn_test", "tasks_data_source_id": "ds_123"})
    assert service.is_configured is True

    unconfigured = NotionSyncService({"token": "", "tasks_data_source_id": ""})
    assert unconfigured.is_configured is False


def test_pull_tasks_for_date_syncs_to_repo(tmp_path):
    repo = TaskRepository(tmp_path / "test.sqlite3")
    service = NotionSyncService({"token": "ntn_test", "tasks_data_source_id": "ds_123"})

    mock_results = {
        "results": [
            {
                "id": "notion-p1",
                "properties": {
                    "Task": {"title": [{"text": {"content": "Notion Task 1"}, "plain_text": "Notion Task 1"}]},
                    "Status": {"select": {"name": "To do"}},
                    "Notes": {"rich_text": [{"text": {"content": "Important note"}, "plain_text": "Important note"}]},
                    "Completed on": {"date": None},
                },
            },
            {
                "id": "notion-p2",
                "properties": {
                    "Task": {"title": [{"text": {"content": "Completed Notion Task"}, "plain_text": "Completed Notion Task"}]},
                    "Status": {"select": {"name": "Done"}},
                    "Notes": {"rich_text": []},
                    "Completed on": {"date": {"start": "2026-11-07"}},
                },
            },
        ]
    }
    service._api_request = MagicMock(return_value=mock_results)

    changed = service.pull_tasks_for_date("2026-11-07", repo)
    assert changed is True

    tasks = repo.get_tasks_for_date("2026-11-07")
    assert len(tasks) == 2

    t1 = next(t for t in tasks if t["notion_id"] == "notion-p1")
    assert t1["title"] == "Notion Task 1"
    assert t1["notes"] == "Important note"
    assert t1["completed_at"] is None

    t2 = next(t for t in tasks if t["notion_id"] == "notion-p2")
    assert t2["title"] == "Completed Notion Task"
    assert t2["completed_at"] is not None


def test_push_add_task_calls_notion(tmp_path):
    repo = TaskRepository(tmp_path / "test.sqlite3")
    local_id = repo.add_task("Local Dayglass Task", "2026-11-07")

    service = NotionSyncService({"token": "ntn_test", "tasks_data_source_id": "ds_123"})
    service._api_request = MagicMock(return_value={"id": "created-notion-page-id"})

    notion_id = service.push_add_task(local_id, "Local Dayglass Task", "2026-11-07", repo)
    assert notion_id == "created-notion-page-id"

    task = repo.get_task_by_id(local_id)
    assert task["notion_id"] == "created-notion-page-id"


def test_offline_queue_and_flush(tmp_path):
    repo = TaskRepository(tmp_path / "test.sqlite3")
    service = NotionSyncService({"token": "ntn_test", "tasks_data_source_id": "ds_123"})

    # 1. Add task offline
    t1_id = repo.add_task("Offline task 1", "2026-11-07")
    a1 = repo.queue_sync_action("add_task", t1_id, {
        "task_id": t1_id,
        "title": "Offline task 1",
        "task_date": "2026-11-07",
        "notes": "offline notes",
        "completed": False,
    })

    # 2. Toggle status offline
    a2 = repo.queue_sync_action("set_status", t1_id, {
        "task_id": t1_id,
        "notion_id": None,
        "completed": True,
    })

    # 3. Add notes offline
    a3 = repo.queue_sync_action("save_notes", t1_id, {
        "task_id": t1_id,
        "notion_id": None,
        "notes": "updated offline note",
    })

    # 4. Delete an existing task offline
    t2_id = repo.add_task("Existing task", "2026-11-07", notion_id="existing-notion-id")
    a4 = repo.queue_sync_action("delete_task", t2_id, {
        "notion_id": "existing-notion-id",
    })

    pending = repo.get_pending_sync_actions()
    assert len(pending) == 4

    # When offline, flush should abort immediately
    service.is_online = MagicMock(return_value=False)
    assert service.flush_pending_actions(repo) == 0
    assert len(repo.get_pending_sync_actions()) == 4

    # When online connects, flush should process all actions
    service.is_online = MagicMock(return_value=True)
    service._api_request = MagicMock(side_effect=[
        {"id": "notion-t1-id"},  # add_task response
        {"id": "notion-t1-id"},  # set_status response
        {"id": "notion-t1-id"},  # save_notes response
        {"id": "existing-notion-id"},  # delete response
    ])

    flushed = service.flush_pending_actions(repo)
    assert flushed == 4
    assert len(repo.get_pending_sync_actions()) == 0

    # Ensure task 1 received its notion_id in SQLite
    task1 = repo.get_task_by_id(t1_id)
    assert task1["notion_id"] == "notion-t1-id"


def test_remove_sync_actions_for_task(tmp_path):
    repo = TaskRepository(tmp_path / "test.sqlite3")
    t1_id = repo.add_task("Cancelled task", "2026-11-07")
    repo.queue_sync_action("add_task", t1_id, {"task_id": t1_id, "title": "Cancelled task"})
    repo.queue_sync_action("save_notes", t1_id, {"task_id": t1_id, "notes": "some notes"})

    assert len(repo.get_pending_sync_actions()) == 2

    # Remove all actions for this task before reconnecting
    repo.remove_sync_actions_for_task(t1_id)
    assert len(repo.get_pending_sync_actions()) == 0

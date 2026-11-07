"""Bidirectional synchronization between Dayglass and Notion Personal HQ with offline queueing."""
from __future__ import annotations

import json
import logging
import os
import socket
import threading
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("dayglass.notion_sync")


def _plain_text(prop_value: list[dict] | None) -> str:
    if not prop_value:
        return ""
    return "".join(part.get("plain_text", part.get("text", {}).get("content", "")) for part in prop_value)


def check_network_connectivity(timeout: float = 1.5) -> bool:
    """Quick check if internet is reachable."""
    try:
        with socket.create_connection(("1.1.1.1", 53), timeout=timeout):
            return True
    except OSError:
        pass
    try:
        with socket.create_connection(("api.notion.com", 443), timeout=timeout):
            return True
    except OSError:
        return False


def load_notion_config() -> dict[str, str]:
    """Find Notion configuration from ~/.config/dayglass/notion.env, environment, or notion-personal-hq."""
    token = os.environ.get("NOTION_TOKEN", "")
    tasks_ds = os.environ.get("NOTION_TASKS_DATA_SOURCE_ID", "")
    tasks_db = os.environ.get("NOTION_TASKS_DATABASE_ID", "")
    version = os.environ.get("NOTION_VERSION", "2026-03-11")

    # 1. Check ~/.config/dayglass/notion.env
    config_file = Path.home() / ".config" / "dayglass" / "notion.env"
    if config_file.exists():
        for line in config_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip("'\"")
                if k == "NOTION_TOKEN" and not token:
                    token = v
                elif k == "NOTION_TASKS_DATA_SOURCE_ID" and not tasks_ds:
                    tasks_ds = v
                elif k == "NOTION_TASKS_DATABASE_ID" and not tasks_db:
                    tasks_db = v
                elif k == "NOTION_VERSION" and version == "2026-03-11":
                    version = v

    # 2. Check /home/kingcole/Code/notion-personal-hq/.env
    notion_hq_env = Path.home() / "Code" / "notion-personal-hq" / ".env"
    if not token and notion_hq_env.exists():
        for line in notion_hq_env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip("'\"")
                if k == "NOTION_TOKEN":
                    token = v

    # 3. Check /home/kingcole/Code/notion-personal-hq/data/state/notion_state.json
    state_path = Path.home() / "Code" / "notion-personal-hq" / "data" / "state" / "notion_state.json"
    if (not tasks_ds or not tasks_db) and state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            tasks_info = state.get("databases", {}).get("tasks", {})
            if not tasks_ds:
                tasks_ds = tasks_info.get("data_source_id", "")
            if not tasks_db:
                tasks_db = tasks_info.get("database_id", "")
        except Exception:
            pass

    return {
        "token": token,
        "tasks_data_source_id": tasks_ds,
        "tasks_database_id": tasks_db,
        "notion_version": version,
    }


class NotionSyncService:
    """Handles synchronization between Dayglass SQLite and Notion Tasks with offline support."""

    def __init__(self, config: dict[str, str] | None = None):
        self.config = config or load_notion_config()
        self.token = self.config.get("token", "")
        self.tasks_ds = self.config.get("tasks_data_source_id", "")
        self.tasks_db = self.config.get("tasks_database_id", "")
        self.notion_version = self.config.get("notion_version", "2026-03-11")
        self._lock = threading.Lock()
        self._monitor_running = False

    @property
    def is_configured(self) -> bool:
        return bool(self.token and (self.tasks_ds or self.tasks_db))

    def is_online(self) -> bool:
        return check_network_connectivity()

    def _api_request(self, method: str, path: str, payload: dict | None = None) -> dict:
        url = f"https://api.notion.com/v1/{path.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": self.notion_version,
            "Content-Type": "application/json",
        }
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # ------------------------------------------------------------------ PULL
    def pull_tasks_for_date(self, task_date: str, task_repo: Any) -> bool:
        """Fetch tasks from Notion for a specific date and sync them to Dayglass SQLite."""
        if not self.is_configured:
            return False

        filter_body = {
            "filter": {
                "and": [
                    {"property": "Planned", "date": {"equals": task_date}},
                    {"property": "Status", "select": {"does_not_equal": "Dropped"}},
                ]
            }
        }

        try:
            if self.tasks_ds:
                res = self._api_request("POST", f"data_sources/{self.tasks_ds}/query", filter_body)
            else:
                res = self._api_request("POST", f"databases/{self.tasks_db}/query", filter_body)
        except Exception as exc:
            log.debug(f"Notion pull query failed (offline?): {exc}")
            return False

        pages = res.get("results", [])
        changed = False

        existing_tasks = task_repo.get_tasks_for_date(task_date)
        by_notion_id = {t["notion_id"]: t for t in existing_tasks if t.get("notion_id")}
        by_title = {t["title"].strip().lower(): t for t in existing_tasks}

        for page in pages:
            pid = page["id"]
            props = page.get("properties", {})
            t_title = _plain_text(props.get("Task", {}).get("title") or []).strip()
            if not t_title:
                continue

            status = (props.get("Status", {}).get("select") or {}).get("name")
            is_done = status == "Done"
            notes = _plain_text(props.get("Notes", {}).get("rich_text") or [])

            if pid in by_notion_id:
                local = by_notion_id[pid]
                local_done = local["completed_at"] is not None
                if is_done != local_done:
                    task_repo.set_completed(local["id"], is_done)
                    changed = True
                if notes and notes != local.get("notes"):
                    task_repo.save_task_notes(local["id"], notes)
                    changed = True
            elif t_title.lower() in by_title and not by_title[t_title.lower()].get("notion_id"):
                matched = by_title[t_title.lower()]
                task_repo.set_notion_id(matched["id"], pid)
                if is_done != (matched["completed_at"] is not None):
                    task_repo.set_completed(matched["id"], is_done)
                    changed = True
                if notes and notes != matched.get("notes"):
                    task_repo.save_task_notes(matched["id"], notes)
                    changed = True
            else:
                new_id = task_repo.add_task(
                    title=t_title,
                    task_date=task_date,
                    notion_id=pid,
                    notes=notes,
                )
                if is_done:
                    task_repo.set_completed(new_id, True)
                changed = True

        return changed

    def pull_tasks_for_date_async(
        self,
        task_date: str,
        task_repo: Any,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        def worker():
            with self._lock:
                changed = self.pull_tasks_for_date(task_date, task_repo)
                if changed and on_change:
                    try:
                        on_change()
                    except Exception as exc:
                        log.debug(f"Callback error: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------ PUSH & QUEUE
    def push_add_task(
        self,
        task_id: int,
        title: str,
        task_date: str,
        task_repo: Any,
        notes: str = "",
        completed: bool = False,
    ) -> str | None:
        if not self.is_configured:
            return None

        props = {
            "Task": {"title": [{"type": "text", "text": {"content": title[:2000]}}]},
            "Planned": {"date": {"start": task_date}},
            "Status": {"select": {"name": "Done" if completed else "To do"}},
        }
        if notes:
            props["Notes"] = {"rich_text": [{"type": "text", "text": {"content": notes[:2000]}}]}
        if completed:
            props["Completed on"] = {"date": {"start": date.today().isoformat()}}

        parent = {"data_source_id": self.tasks_ds, "type": "data_source_id"} if self.tasks_ds else {
            "database_id": self.tasks_db, "type": "database_id"
        }
        body = {"parent": parent, "properties": props}

        try:
            res = self._api_request("POST", "pages", body)
            pid = res.get("id")
            if pid:
                task_repo.set_notion_id(task_id, pid)
                return pid
        except Exception as exc:
            if self.tasks_db and "data_source" in str(parent):
                try:
                    body["parent"] = {"database_id": self.tasks_db, "type": "database_id"}
                    res = self._api_request("POST", "pages", body)
                    pid = res.get("id")
                    if pid:
                        task_repo.set_notion_id(task_id, pid)
                        return pid
                except Exception as inner:
                    log.warning(f"Could not push task to Notion: {inner}")
            else:
                log.warning(f"Could not push task to Notion: {exc}")
        return None

    def push_add_task_async(
        self,
        task_id: int,
        title: str,
        task_date: str,
        task_repo: Any,
        notes: str = "",
        completed: bool = False,
    ) -> None:
        # First queue offline action
        action_id = task_repo.queue_sync_action("add_task", task_id, {
            "task_id": task_id,
            "title": title,
            "task_date": task_date,
            "notes": notes,
            "completed": completed,
        })

        def worker():
            pid = self.push_add_task(task_id, title, task_date, task_repo, notes, completed)
            if pid:
                task_repo.remove_sync_action(action_id)

        threading.Thread(target=worker, daemon=True).start()

    def push_status(self, notion_id: str, completed: bool) -> None:
        if not self.is_configured or not notion_id:
            return
        status_name = "Done" if completed else "To do"
        completed_on = {"date": {"start": date.today().isoformat()}} if completed else {"date": None}
        body = {
            "properties": {
                "Status": {"select": {"name": status_name}},
                "Completed on": completed_on,
            }
        }
        self._api_request("PATCH", f"pages/{notion_id}", body)

    def push_status_async(
        self,
        task_id: int,
        notion_id: str | None,
        completed: bool,
        task_repo: Any,
    ) -> None:
        action_id = task_repo.queue_sync_action("set_status", task_id, {
            "task_id": task_id,
            "notion_id": notion_id,
            "completed": completed,
        })

        def worker():
            nid = notion_id
            if not nid:
                task = task_repo.get_task_by_id(task_id)
                nid = task.get("notion_id") if task else None
            if nid:
                try:
                    self.push_status(nid, completed)
                    task_repo.remove_sync_action(action_id)
                except Exception as exc:
                    task_repo.record_sync_attempt(action_id, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def push_notes(self, notion_id: str, notes: str) -> None:
        if not self.is_configured or not notion_id:
            return
        body = {
            "properties": {
                "Notes": {"rich_text": [{"type": "text", "text": {"content": notes[:2000]}}]} if notes else {"rich_text": []}
            }
        }
        self._api_request("PATCH", f"pages/{notion_id}", body)

    def push_notes_async(
        self,
        task_id: int,
        notion_id: str | None,
        notes: str,
        task_repo: Any,
    ) -> None:
        action_id = task_repo.queue_sync_action("save_notes", task_id, {
            "task_id": task_id,
            "notion_id": notion_id,
            "notes": notes,
        })

        def worker():
            nid = notion_id
            if not nid:
                task = task_repo.get_task_by_id(task_id)
                nid = task.get("notion_id") if task else None
            if nid:
                try:
                    self.push_notes(nid, notes)
                    task_repo.remove_sync_action(action_id)
                except Exception as exc:
                    task_repo.record_sync_attempt(action_id, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def push_delete(self, notion_id: str) -> None:
        if not self.is_configured or not notion_id:
            return
        body = {"properties": {"Status": {"select": {"name": "Dropped"}}}}
        self._api_request("PATCH", f"pages/{notion_id}", body)

    def push_delete_async(
        self,
        task_id: int,
        notion_id: str | None,
        task_repo: Any,
    ) -> None:
        if not notion_id:
            return
        action_id = task_repo.queue_sync_action("delete_task", task_id, {
            "notion_id": notion_id,
        })

        def worker():
            try:
                self.push_delete(notion_id)
                task_repo.remove_sync_action(action_id)
            except Exception as exc:
                task_repo.record_sync_attempt(action_id, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def push_carry_forward(
        self,
        old_notion_id: str | None,
        new_task_id: int,
        title: str,
        target_date: str,
        task_repo: Any,
        notes: str = "",
    ) -> None:
        if not self.is_configured:
            return

        if old_notion_id:
            try:
                self._api_request("PATCH", f"pages/{old_notion_id}", {
                    "properties": {"Status": {"select": {"name": "Not done"}}}
                })
            except Exception as exc:
                log.warning(f"Could not mark carried task Not done in Notion: {exc}")

        props = {
            "Task": {"title": [{"type": "text", "text": {"content": title[:2000]}}]},
            "Planned": {"date": {"start": target_date}},
            "Status": {"select": {"name": "To do"}},
            "Carried over": {"checkbox": True},
        }
        if notes:
            props["Notes"] = {"rich_text": [{"type": "text", "text": {"content": notes[:2000]}}]}

        parent = {"data_source_id": self.tasks_ds, "type": "data_source_id"} if self.tasks_ds else {
            "database_id": self.tasks_db, "type": "database_id"
        }
        res = self._api_request("POST", "pages", {"parent": parent, "properties": props})
        pid = res.get("id")
        if pid:
            task_repo.set_notion_id(new_task_id, pid)

    def push_carry_forward_async(
        self,
        old_notion_id: str | None,
        new_task_id: int,
        title: str,
        target_date: str,
        task_repo: Any,
        notes: str = "",
    ) -> None:
        action_id = task_repo.queue_sync_action("carry_forward", new_task_id, {
            "old_notion_id": old_notion_id,
            "new_task_id": new_task_id,
            "title": title,
            "target_date": target_date,
            "notes": notes,
        })

        def worker():
            try:
                self.push_carry_forward(old_notion_id, new_task_id, title, target_date, task_repo, notes)
                task_repo.remove_sync_action(action_id)
            except Exception as exc:
                task_repo.record_sync_attempt(action_id, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------ OFFLINE FLUSH & RECONNECT
    def flush_pending_actions(self, task_repo: Any) -> int:
        """Process and push all queued offline changes to Notion."""
        if not self.is_configured:
            return 0
        if not self.is_online():
            return 0

        pending = task_repo.get_pending_sync_actions()
        if not pending:
            return 0

        synced = 0
        for item in pending:
            action_id = item["id"]
            action_type = item["action_type"]
            payload = item.get("payload", {})
            try:
                if action_type == "add_task":
                    pid = self.push_add_task(
                        task_id=payload["task_id"],
                        title=payload["title"],
                        task_date=payload["task_date"],
                        task_repo=task_repo,
                        notes=payload.get("notes", ""),
                        completed=payload.get("completed", False),
                    )
                    if pid:
                        task_repo.remove_sync_action(action_id)
                        synced += 1
                elif action_type == "set_status":
                    notion_id = payload.get("notion_id")
                    if not notion_id and payload.get("task_id"):
                        task = task_repo.get_task_by_id(payload["task_id"])
                        notion_id = task.get("notion_id") if task else None
                    if notion_id:
                        self.push_status(notion_id, payload["completed"])
                    task_repo.remove_sync_action(action_id)
                    synced += 1
                elif action_type == "save_notes":
                    notion_id = payload.get("notion_id")
                    if not notion_id and payload.get("task_id"):
                        task = task_repo.get_task_by_id(payload["task_id"])
                        notion_id = task.get("notion_id") if task else None
                    if notion_id:
                        self.push_notes(notion_id, payload["notes"])
                    task_repo.remove_sync_action(action_id)
                    synced += 1
                elif action_type == "delete_task":
                    notion_id = payload.get("notion_id")
                    if notion_id:
                        self.push_delete(notion_id)
                    task_repo.remove_sync_action(action_id)
                    synced += 1
                elif action_type == "carry_forward":
                    self.push_carry_forward(
                        old_notion_id=payload.get("old_notion_id"),
                        new_task_id=payload["new_task_id"],
                        title=payload["title"],
                        target_date=payload["target_date"],
                        task_repo=task_repo,
                        notes=payload.get("notes", ""),
                    )
                    task_repo.remove_sync_action(action_id)
                    synced += 1
            except Exception as exc:
                task_repo.record_sync_attempt(action_id, str(exc))
                log.warning(f"Failed to flush pending sync action #{action_id}: {exc}")
                break

        return synced

    def sync_all(
        self,
        task_repo: Any,
        current_date: str | None = None,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        """Full bidirectional sync: push offline changes, then pull fresh Notion tasks."""
        def worker():
            with self._lock:
                flushed = self.flush_pending_actions(task_repo)

                dates_to_pull = [current_date or date.today().isoformat()]
                today = date.today()
                for d in (today, today + timedelta(days=1), today - timedelta(days=1)):
                    d_str = d.isoformat()
                    if d_str not in dates_to_pull:
                        dates_to_pull.append(d_str)

                changed = flushed > 0
                for d_str in dates_to_pull:
                    if self.pull_tasks_for_date(d_str, task_repo):
                        changed = True

                if changed and on_change:
                    try:
                        on_change()
                    except Exception as exc:
                        log.debug(f"Sync callback error: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def start_network_monitor(
        self,
        task_repo: Any,
        get_current_date: Callable[[], str],
        on_change: Callable[[], None],
        check_interval: float = 4.0,
    ) -> None:
        """Monitor internet connectivity and automatically sync upon connecting."""
        if self._monitor_running:
            return
        self._monitor_running = True

        def monitor_loop():
            was_online = check_network_connectivity()
            while self._monitor_running:
                time.sleep(check_interval)
                now_online = check_network_connectivity()
                if not was_online and now_online:
                    log.info("Internet connection detected! Automatically syncing with Notion...")
                    current_d = get_current_date() if get_current_date else date.today().isoformat()
                    self.sync_all(task_repo, current_d, on_change)
                elif now_online:
                    # Flush any offline pending actions
                    try:
                        pending = task_repo.get_pending_sync_actions()
                        if pending:
                            with self._lock:
                                self.flush_pending_actions(task_repo)
                    except Exception:
                        pass
                was_online = now_online

        threading.Thread(target=monitor_loop, daemon=True).start()

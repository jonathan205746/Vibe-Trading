"""Task system: persistent tasks + dependency graph stored as JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.agent.tools import BaseTool

TASKS_DIR = Path(__file__).resolve().parents[2] / ".tasks"


class TaskManager:
    """Task CRUD + dependency graph; one JSON file per task."""

    def __init__(self) -> None:
        self.dir = TASKS_DIR
        self.dir.mkdir(exist_ok=True)
        self._next_id = self._max_id() + 1

    def _max_id(self) -> int:
        ids = [int(f.stem.split("_")[1]) for f in self.dir.glob("task_*.json")]
        return max(ids) if ids else 0

    def _load(self, task_id: int) -> dict:
        path = self.dir / f"task_{task_id}.json"
        if not path.exists():
            raise ValueError(f"Task {task_id} not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, task: dict) -> None:
        path = self.dir / f"task_{task['id']}.json"
        path.write_text(json.dumps(task, indent=2, ensure_ascii=False), encoding="utf-8")

    def create(self, subject: str, description: str = "") -> str:
        task = {"id": self._next_id, "subject": subject, "description": description,
                "status": "pending", "blockedBy": [], "blocks": []}
        self._save(task)
        self._next_id += 1
        return json.dumps(task, indent=2, ensure_ascii=False)

    def get(self, task_id: int) -> str:
        return json.dumps(self._load(task_id), indent=2, ensure_ascii=False)

    def update(self, task_id: int, status: str = None,
               addBlockedBy: list = None, addBlocks: list = None) -> str:
        task = self._load(task_id)
        if status:
            task["status"] = status
            if status == "completed":
                self._clear_dep(task_id)
        if addBlockedBy:
            task["blockedBy"] = list(set(task["blockedBy"] + addBlockedBy))
        if addBlocks:
            task["blocks"] = list(set(task["blocks"] + addBlocks))
            for bid in addBlocks:
                try:
                    blocked = self._load(bid)
                    if task_id not in blocked["blockedBy"]:
                        blocked["blockedBy"].append(task_id)
                        self._save(blocked)
                except ValueError:
                    pass
        self._save(task)
        return json.dumps(task, indent=2, ensure_ascii=False)

    def _clear_dep(self, completed_id: int) -> None:
        for f in self.dir.glob("task_*.json"):
            task = json.loads(f.read_text(encoding="utf-8"))
            if completed_id in task.get("blockedBy", []):
                task["blockedBy"].remove(completed_id)
                self._save(task)

    def list_all(self) -> str:
        tasks = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(self.dir.glob("task_*.json"))]
        if not tasks:
            return "No tasks."
        lines = []
        for t in tasks:
            m = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}.get(t["status"], "[?]")
            b = f" (blocked by: {t['blockedBy']})" if t.get("blockedBy") else ""
            lines.append(f"{m} #{t['id']}: {t['subject']}{b}")
        return "\n".join(lines)


TASKS = TaskManager()


class TaskCreateTool(BaseTool):
    name = "task_create"
    description = "Create a new task."
    parameters = {"type": "object", "properties": {
        "subject": {"type": "string"}, "description": {"type": "string"}
    }, "required": ["subject"]}

    def execute(self, **kw: Any) -> str:
        return TASKS.create(kw["subject"], kw.get("description", ""))


class TaskUpdateTool(BaseTool):
    name = "task_update"
    description = "Update a task's status or dependencies."
    parameters = {"type": "object", "properties": {
        "task_id": {"type": "integer"},
        "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
        "addBlockedBy": {"type": "array", "items": {"type": "integer"}},
        "addBlocks": {"type": "array", "items": {"type": "integer"}},
    }, "required": ["task_id"]}
    repeatable = True

    def execute(self, **kw: Any) -> str:
        return TASKS.update(kw["task_id"], kw.get("status"), kw.get("addBlockedBy"), kw.get("addBlocks"))


class TaskListTool(BaseTool):
    name = "task_list"
    description = "List all tasks with status summary."
    parameters = {"type": "object", "properties": {}, "required": []}
    repeatable = True

    def execute(self, **kw: Any) -> str:
        return TASKS.list_all()


class TaskGetTool(BaseTool):
    name = "task_get"
    description = "Get full details of a task by ID."
    parameters = {"type": "object", "properties": {
        "task_id": {"type": "integer"},
    }, "required": ["task_id"]}
    repeatable = True

    def execute(self, **kw: Any) -> str:
        return TASKS.get(kw["task_id"])

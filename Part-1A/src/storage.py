"""Atomic JSON persistence for tasks."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from threading import RLock

from src.models import PRIORITY_RANK, Priority, Status, Task


class TaskStorage:
    def __init__(self, path: str | Path = "tasks.json") -> None:
        self.path = Path(path)
        self._lock = RLock()

    def load_all(self) -> list[Task]:
        with self._lock:
            if not self.path.exists():
                return []
            try:
                records = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError("could not read task data") from exc
            if not isinstance(records, list):
                raise ValueError("task data must be a JSON list")
            return [Task.from_dict(record) for record in records]

    def save_all(self, tasks: list[Task]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            [task.to_dict() for task in tasks], indent=2, ensure_ascii=False
        )
        with self._lock:
            temporary_path: str | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=self.path.parent,
                    delete=False,
                ) as temporary_file:
                    temporary_path = temporary_file.name
                    temporary_file.write(payload)
                    temporary_file.flush()
                    os.fsync(temporary_file.fileno())
                os.replace(temporary_path, self.path)
            except OSError as exc:
                if temporary_path and os.path.exists(temporary_path):
                    os.unlink(temporary_path)
                raise ValueError("could not save task data") from exc

    def list_tasks(
        self,
        status: Status | str | None = None,
        tag: str | None = None,
        sort_by: str = "id",
    ) -> list[Task]:
        tasks = self.load_all()
        if status is not None:
            selected_status = Status(status)
            tasks = [task for task in tasks if task.status == selected_status]
        if tag is not None:
            tasks = [task for task in tasks if tag in task.tags]
        if sort_by == "priority":
            tasks.sort(key=lambda task: (PRIORITY_RANK[task.priority], task.id))
        elif sort_by == "id":
            tasks.sort(key=lambda task: task.id)
        else:
            raise ValueError("sort must be 'id' or 'priority'")
        return tasks

    def add_task(
        self,
        title: str,
        tags: list[str] | None = None,
        priority: Priority | str = Priority.MED,
    ) -> Task:
        with self._lock:
            tasks = self.load_all()
            task = Task(
                id=max((existing.id for existing in tasks), default=0) + 1,
                title=title,
                tags=tags or [],
                priority=priority,
            )
            tasks.append(task)
            self.save_all(tasks)
            return task

    def update_task(
        self,
        task_id: int,
        status: Status | str | None = None,
        priority: Priority | str | None = None,
    ) -> Task:
        with self._lock:
            tasks = self.load_all()
            for task in tasks:
                if task.id == task_id:
                    if status is not None:
                        task.status = Status(status)
                    if priority is not None:
                        task.priority = Priority(priority)
                    self.save_all(tasks)
                    return task
        raise KeyError(f"task ID {task_id} does not exist")

    def delete_task(self, task_id: int) -> None:
        with self._lock:
            tasks = self.load_all()
            remaining = [task for task in tasks if task.id != task_id]
            if len(remaining) == len(tasks):
                raise KeyError(f"task ID {task_id} does not exist")
            self.save_all(remaining)

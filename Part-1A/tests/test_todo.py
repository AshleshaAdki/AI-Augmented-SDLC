"""Behavioral tests for the task model, storage, and CLI."""

import json

import pytest
from src.cli import main
from src.models import Priority, Task
from src.storage import TaskStorage


def test_task_rejects_empty_title() -> None:
    with pytest.raises(ValueError, match="title"):
        Task(id=1, title="   ")


def test_missing_store_starts_empty_and_first_add_persists(tmp_path) -> None:
    data_file = tmp_path / "tasks.json"
    storage = TaskStorage(data_file)

    assert storage.load_all() == []
    task = storage.add_task("  Prepare report  ", ["work"], Priority.HIGH)

    assert task.id == 1
    assert task.title == "Prepare report"
    assert json.loads(data_file.read_text(encoding="utf-8"))[0]["status"] == "pending"


def test_status_and_tag_filters_are_combined(tmp_path) -> None:
    storage = TaskStorage(tmp_path / "tasks.json")
    first = storage.add_task("Open", ["work"])
    second = storage.add_task("Closed", ["work"])
    storage.update_task(second.id, status="done")
    storage.add_task("Personal", ["home"])

    assert [task.id for task in storage.list_tasks(tag="work", status="done")] == [
        second.id
    ]
    assert [task.id for task in storage.list_tasks(tag="work", status="pending")] == [
        first.id
    ]


def test_priority_order_is_high_to_low(tmp_path) -> None:
    storage = TaskStorage(tmp_path / "tasks.json")
    storage.add_task("Low", priority="low")
    storage.add_task("High", priority="high")
    storage.add_task("Medium", priority="med")

    result = storage.list_tasks(sort_by="priority")

    assert [task.priority for task in result] == [
        Priority.HIGH,
        Priority.MED,
        Priority.LOW,
    ]


def test_update_missing_task_returns_error_code(tmp_path, capsys) -> None:
    result = main(["update", "999", "--status", "done", "--db", str(tmp_path / "x")])

    assert result == 1
    assert "does not exist" in capsys.readouterr().err


def test_invalid_cli_argument_returns_error_code(capsys) -> None:
    result = main(["add", "Task", "--priority", "urgent"])

    assert result == 1
    assert "invalid choice" in capsys.readouterr().err


def test_cli_add_list_update_delete(tmp_path, capsys) -> None:
    data_file = str(tmp_path / "cli-tasks.json")

    assert main(["add", "Review PR", "--tags", "work,urgent", "--db", data_file]) == 0
    assert "Added task 1" in capsys.readouterr().out
    assert main(["list", "--tag", "urgent", "--db", data_file]) == 0
    assert "Review PR" in capsys.readouterr().out
    assert main(["update", "1", "--status", "done", "--db", data_file]) == 0
    assert "Updated task 1" in capsys.readouterr().out
    assert main(["delete", "1", "--db", data_file]) == 0
    assert "Deleted task 1" in capsys.readouterr().out
    assert TaskStorage(data_file).load_all() == []


def test_delete_and_invalid_json(tmp_path) -> None:
    storage = TaskStorage(tmp_path / "tasks.json")
    task = storage.add_task("Temporary")
    storage.delete_task(task.id)
    assert storage.load_all() == []

    storage.path.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="read"):
        storage.load_all()

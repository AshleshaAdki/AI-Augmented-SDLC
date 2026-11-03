"""Command-line entry point for task management."""

import argparse
import sys
from collections.abc import Sequence

from src.models import Priority, Status
from src.storage import TaskStorage


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage tasks in a JSON file.")
    commands = parser.add_subparsers(dest="command", required=True)

    add_parser = commands.add_parser("add", help="create a task")
    add_parser.add_argument("title")
    add_parser.add_argument("--tags", default="")
    add_parser.add_argument("--priority", choices=[item.value for item in Priority])
    add_parser.add_argument("--db", default="tasks.json")

    list_parser = commands.add_parser("list", help="show tasks")
    list_parser.add_argument("--status", choices=[item.value for item in Status])
    list_parser.add_argument("--tag")
    list_parser.add_argument("--sort", choices=["priority", "id"], default="id")
    list_parser.add_argument("--db", default="tasks.json")

    update_parser = commands.add_parser("update", help="change a task")
    update_parser.add_argument("id", type=int)
    update_parser.add_argument("--status", choices=[item.value for item in Status])
    update_parser.add_argument("--priority", choices=[item.value for item in Priority])
    update_parser.add_argument("--db", default="tasks.json")

    delete_parser = commands.add_parser("delete", help="remove a task")
    delete_parser.add_argument("id", type=int)
    delete_parser.add_argument("--db", default="tasks.json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    storage = TaskStorage(args.db)

    try:
        if args.command == "add":
            tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]
            task = storage.add_task(args.title, tags, args.priority or Priority.MED)
            print("Added task {}: {}".format(task.id, task.title))
        elif args.command == "list":
            tasks = storage.list_tasks(args.status, args.tag, args.sort)
            for task in tasks:
                print(
                    "{} [{}] {} ({}; tags: {})".format(
                        task.id,
                        task.status.value,
                        task.title,
                        task.priority.value,
                        ", ".join(task.tags) or "-",
                    )
                )
        elif args.command == "update":
            if args.status is None and args.priority is None:
                raise ValueError("update requires --status or --priority")
            task = storage.update_task(args.id, args.status, args.priority)
            print("Updated task {}".format(task.id))
        elif args.command == "delete":
            storage.delete_task(args.id)
            print("Deleted task {}".format(args.id))
    except (ValueError, KeyError) as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

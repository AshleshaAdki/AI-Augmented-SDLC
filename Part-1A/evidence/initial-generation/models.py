"""Validated task records and priority ordering."""

from dataclasses import dataclass, field
from enum import Enum


class Priority(str, Enum):
    LOW = "low"
    MED = "med"
    HIGH = "high"


class Status(str, Enum):
    PENDING = "pending"
    DONE = "done"


PRIORITY_RANK = {
    Priority.HIGH: 0,
    Priority.MED: 1,
    Priority.LOW: 2,
}


@dataclass
class Task:
    id: int
    title: str
    tags: list[str] = field(default_factory=list)
    priority: Priority = Priority.MED
    status: Status = Status.PENDING

    def __post_init__(self) -> None:
        if isinstance(self.id, bool) or self.id < 1:
            raise ValueError("task ID must be a positive integer")
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("task title must not be empty")
        self.title = self.title.strip()
        if not isinstance(self.tags, list) or any(
            not isinstance(tag, str) or not tag.strip() for tag in self.tags
        ):
            raise ValueError("tags must be a list of non-empty strings")
        self.tags = list(dict.fromkeys(tag.strip() for tag in self.tags))
        try:
            self.priority = Priority(self.priority)
            self.status = Status(self.status)
        except ValueError as exc:
            raise ValueError("invalid task priority or status") from exc

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "tags": self.tags,
            "priority": self.priority.value,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Task":
        try:
            return cls(
                id=data["id"],  # type: ignore[arg-type]
                title=data["title"],  # type: ignore[arg-type]
                tags=data.get("tags", []),  # type: ignore[arg-type]
                priority=data.get("priority", Priority.MED),  # type: ignore[arg-type]
                status=data.get("status", Status.PENDING),  # type: ignore[arg-type]
            )
        except (KeyError, TypeError) as exc:
            raise ValueError("invalid task record in JSON data") from exc

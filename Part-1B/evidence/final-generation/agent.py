"""Offline reminder parsing with explicit ambiguity handling."""

import re
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Recurrence(str, Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReminderOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = None
    due_date: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    priority: Priority = Priority.MEDIUM
    recurrence: Recurrence = Recurrence.NONE
    needs_clarification: bool = False
    clarification_question: Optional[str] = None

    @field_validator("due_date")
    @classmethod
    def validate_iso_due_date(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                try:
                    date.fromisoformat(value)
                except ValueError as exc:
                    raise ValueError(
                        "due_date must be an ISO-8601 date or datetime"
                    ) from exc
        return value


class ReminderAgent:
    backend = "offline-rule-based-stub"

    def __init__(self, reference: Optional[datetime] = None) -> None:
        current = reference or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        self.reference = current.astimezone(timezone.utc)

    def parse_intent(self, user_input: str) -> ReminderOutput:
        text = user_input.strip()
        if not text:
            return self._clarify(None, "What should I remind you about, and when?")

        lowered = text.casefold()
        if self.is_unsafe_request(lowered):
            return self._clarify(
                None,
                "I can only parse safe reminder requests. "
                "What reminder would you like?",
            )

        recurrence = self._recurrence(lowered)
        if lowered in {"remind me later", "set an alert"}:
            return self._clarify(None, "What should the reminder be about, and when?")

        tags = re.findall(r"(?<!\w)#([A-Za-z0-9_-]+)", text)
        priority = self._priority(lowered)
        title = self._extract_title(text)
        if not title:
            return self._clarify(None, "What task should I remind you about?")

        due_date, time_was_found, invalid_date = self._extract_due_date(text, lowered)
        if invalid_date:
            return self._clarify(title, "Which date did you mean?")
        if due_date is None and recurrence == Recurrence.NONE:
            question = (
                "What date should I use for that time?"
                if time_was_found
                else "When should I remind you?"
            )
            return self._clarify(title, question)

        return ReminderOutput(
            title=title,
            due_date=due_date,
            tags=tags,
            priority=priority,
            recurrence=recurrence,
        )

    @staticmethod
    def _clarify(title: Optional[str], question: str) -> ReminderOutput:
        return ReminderOutput(
            title=title,
            needs_clarification=True,
            clarification_question=question,
        )

    @staticmethod
    def _recurrence(text: str) -> Recurrence:
        if re.search(r"\b(daily|every day)\b", text):
            return Recurrence.DAILY
        if re.search(r"\b(weekly|every week|every monday)\b", text):
            return Recurrence.WEEKLY
        if re.search(r"\b(monthly|every month)\b", text):
            return Recurrence.MONTHLY
        return Recurrence.NONE

    @staticmethod
    def _priority(text: str) -> Priority:
        match = re.search(r"\bpriority\s*[:=]?\s*(low|medium|high)\b", text)
        if match:
            return Priority(match.group(1))
        return Priority.MEDIUM

    @staticmethod
    def is_unsafe_request(text: str) -> bool:
        instruction_override = re.search(
            r"\b(ignore|disregard|override)\b.{0,50}\b(instructions?|rules?|"
            r"previous|system|safety)\b",
            text,
        )
        instruction_disclosure = re.search(
            r"\b(reveal|show|print|disclose)\b.{0,50}\b("
            r"hidden|system|prompt|instructions?)\b",
            text,
        )
        destructive_request = re.search(
            r"\b(delete|erase|remove|wipe)\b.{0,40}\b(all|everything|"
            r"reminders?|data|tasks?)\b",
            text,
        )
        external_action = re.search(
            r"\b(send|transfer|purchase|execute)\b.{0,40}\b("
            r"money|payment|message|email|command|file)\b",
            text,
        )
        return bool(
            instruction_override
            or instruction_disclosure
            or destructive_request
            or external_action
        )

    @staticmethod
    def _extract_title(text: str) -> Optional[str]:
        title = re.sub(r"(?i)^\s*remind me to\s+", "", text)
        title = re.sub(r"(?i)^\s*(?:please\s+)?remind me\s+", "", title)
        title = re.sub(
            r"(?i)^\s*(?:please\s+)?(?:schedule|set a reminder to)\s+", "", title
        )
        title = re.sub(r"(?i)^\s*set an alert\s*", "", title)
        title = re.sub(r"(?i)\b(?:on|by)\s+\d{4}-\d{2}-\d{2}\b", "", title)
        title = re.sub(r"(?i)\b(?:tomorrow|today|tonight)\b", "", title)
        title = re.sub(
            r"(?i)\bnext\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            "",
            title,
        )
        title = re.sub(r"(?i)\b(?:sometime\s+)?next\s+month\b", "", title)
        title = re.sub(r"(?i)\bevery\s+(?:day|week|month|monday|morning)\b", "", title)
        title = re.sub(r"(?i)\b(?:daily|weekly|monthly)\b", "", title)
        title = re.sub(r"(?i)\b(?:at|by)\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)\b", "", title)
        title = re.sub(r"(?i)\b(?:morning|afternoon|evening|night)\b", "", title)
        title = re.sub(r"(?i)\bpriority\s*[:=]?\s*(?:low|medium|high)\b", "", title)
        title = re.sub(r"(?<!\w)#[A-Za-z0-9_-]+", "", title)
        title = re.sub(r"\s+", " ", title).strip(" \t,.;:-")
        if not title:
            return None
        return title[0].upper() + title[1:]

    def _extract_due_date(
        self, text: str, lowered: str
    ) -> tuple[Optional[str], bool, bool]:
        time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", lowered)
        parsed_time: Optional[time] = None
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            meridiem = time_match.group(3)
            if not 1 <= hour <= 12 or minute > 59:
                return None, True, True
            hour = hour % 12 + (12 if meridiem == "pm" else 0)
            parsed_time = time(hour, minute, tzinfo=timezone.utc)

        date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        selected_date: Optional[date] = None
        if date_match:
            try:
                selected_date = date.fromisoformat(date_match.group(1))
            except ValueError:
                return None, parsed_time is not None, True
        elif re.search(r"\btomorrow\b", lowered):
            selected_date = self.reference.date() + timedelta(days=1)
        elif re.search(r"\btoday\b", lowered):
            selected_date = self.reference.date()
        else:
            weekday = re.search(
                r"\b(?:next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
                lowered,
            )
            if weekday:
                weekdays = {
                    "monday": 0,
                    "tuesday": 1,
                    "wednesday": 2,
                    "thursday": 3,
                    "friday": 4,
                    "saturday": 5,
                    "sunday": 6,
                }
                target = weekdays[weekday.group(1)]
                days_ahead = (target - self.reference.weekday()) % 7
                if days_ahead == 0 or weekday.group(0).startswith("next "):
                    days_ahead += 7
                selected_date = self.reference.date() + timedelta(days=days_ahead)
            elif parsed_time is not None and re.search(r"\b(at|by)\b", lowered):
                selected_date = self.reference.date()

        if selected_date is None:
            return None, parsed_time is not None, False
        if parsed_time is None:
            return selected_date.isoformat(), False, False
        due = datetime.combine(selected_date, parsed_time).replace(tzinfo=timezone.utc)
        return due.isoformat().replace("+00:00", "Z"), True, False

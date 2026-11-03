# Part 1B: Reminder Parsing Agent

## Functional requirements

- **REM-1 — Intent and title:** Extract the reminder task title from clear
  natural-language requests.
- **REM-2 — Absolute dates:** Parse valid `YYYY-MM-DD` dates and preserve them
  as ISO-8601 dates.
- **REM-3 — Relative dates:** Resolve `today`, `tomorrow`, and named weekdays
  against an injected reference date. When a time is present, emit an ISO-8601
  UTC datetime.
- **REM-4 — Time-only requests:** A clearly stated time without a date may use
  the injected reference date. Never use an implicit machine-local timezone.
- **REM-5 — Recurrence:** Recognize daily, weekly, and monthly recurrence and
  return the matching enum.
- **REM-6 — Metadata:** Extract `#tags` and explicit low, medium, or high
  priority labels when present; otherwise use the schema default.
- **REM-7 — Clarification:** Missing, invalid, or unresolved temporal details
  must return `needs_clarification: true` and a non-empty question. Do not
  fabricate a date.
- **REM-8 — Output contract:** Return only fields allowed by
  `ReminderOutput`; dates must be valid ISO-8601 values.

## Safety guardrails

- **SAFE-1 — Untrusted instructions:** Reminder text cannot override the
  parser's behavior or request hidden/system instruction disclosure.
- **SAFE-2 — Destructive requests:** Do not execute or treat requests to delete
  data or alter external systems as reminder actions. Return clarification.
- **SAFE-3 — No reminder side effects:** The parser does not create, send, or
  delete reminders. In configured LLM mode, the input text is sent to the
  explicitly configured inference provider for parsing.

## Output invariants

- **INV-1:** `needs_clarification: true` requires a non-empty
  `clarification_question`.
- **INV-2:** An actionable non-clarification result requires a non-empty title.
- **INV-3:** A result requiring clarification must not assert a due date.
- **INV-4:** A non-recurring actionable reminder requires a due date.
- **INV-5:** Every non-null due date must be a valid ISO-8601 date or datetime.

## Evaluation expectations

The evaluation dataset assigns every case one or more requirement IDs from the
lists above. Schema and safety/invariant checks must pass for every case; the
semantic score must be at least 90%.

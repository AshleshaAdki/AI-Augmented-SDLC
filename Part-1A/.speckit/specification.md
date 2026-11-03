# Part 1A: Task CLI Requirements

Implement a deterministic command-line task manager with add, list, update, and
delete operations. Tasks have sequential positive IDs, a non-empty title,
optional tags, pending/done status, and low/med/high priority.

Store records in a local JSON file. Listing combines status and exact-tag
filters and supports ID order or high-to-low priority order. Invalid arguments
and references to missing task IDs return exit code 1 with a useful error.

## Acceptance checks

- New tasks are persisted immediately as pending.
- Status and tag filters can be combined.
- Priority sorting is high, then med, then low.
- Updating an unknown ID fails clearly with exit code 1.

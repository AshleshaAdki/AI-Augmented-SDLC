# Part 1A Constitution: Deterministic Task CLI

## Scope and determinism

- Implement task management with add, list, update, and delete operations.
- Identical inputs and stored data must produce identical output and exit codes.
- Persist tasks in a local JSON file; do not require a database service.

## Engineering constraints

- Support Python 3.9 and newer with a modular implementation.
- Validate task data and command-line arguments.
- Return 0 on success and 1 for invalid arguments, validation errors, or
  missing task IDs.

## Verification gates

- Ruff lint must pass with no findings.
- Bandit must report no Medium or High severity security issues.
- All pytest tests must pass.

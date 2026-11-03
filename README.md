# AI-Augmented SDLC Assignment

## Project Overview

This repository contains two Python applications developed using the Spec-Driven Development (SDD) approach with GitHub Spec Kit.

- Part 1A – Smart Todo & Task CLI: A deterministic task-management application with CRUD operations, JSON persistence, filtering and priority sorting.
- Part 1B – AI Reminder Parser: A non-deterministic, AI-assisted application that converts natural-language reminder requests into structured reminder data with validation, clarification and safety guardrails.

Both applications include independent harness validation to verify implementation quality and expected behaviour.

## Project Workflow

Both applications follow the Spec Kit workflow:

1. Problem statement
2. Constitution
3. Specification
4. Clarification
5. Technical plan
6. Task breakdown
7. Implementation
8. Harness validation
9. Feedback and repair
10. Final human review

## Technology Stack

- Python 3.9+
- GitHub Spec Kit
- Pytest
- Ruff
- Bandit
- Pydantic
- OpenAI-compatible LLM API

## Setup Instructions

Run these commands from the repository root using PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Part 1A – Deterministic Application

Smart Todo & Task CLI supports:

- Creating, viewing, updating and deleting tasks.
- JSON-based data persistence.
- Tag filtering.
- Priority-based sorting.
- Task status management.

### Run Validation

```powershell
ruff check Part-1A\src
bandit -r Part-1A\src
$env:PYTHONPATH = "Part-1A"
pytest Part-1A\tests
```

### Run Application

```powershell
$env:PYTHONPATH = "Part-1A"
python -m src.cli add "Prepare report" --priority high
python -m src.cli list --sort priority
```

Harness execution details and validation evidence:

[Part 1A Harness Log](Part-1A/evidence/harness-log.md)

## Part 1B – AI Reminder Parser

The AI Reminder Parser processes natural-language reminder requests and produces structured outputs.

Key features:

- Natural-language reminder parsing.
- Structured JSON output validation.
- Date and time interpretation.
- Reminder and reschedule intent handling.
- Clarification for incomplete requests.
- Safety guardrails for unsafe inputs.
- Offline evaluation and live LLM evaluation.

### Run Validation

```powershell
$env:PYTHONPATH = "Part-1B"
pytest Part-1B\tests
python Part-1B\.harness\run_eval.py
```

### LLM Configuration

The application supports an OpenAI-compatible chat-completions endpoint.

Configure credentials through environment variables:

```powershell
$env:REMINDER_LLM_API_KEY = "<your-api-key>"
$env:REMINDER_LLM_MODEL = "openai/gpt-oss-120b"
$env:REMINDER_LLM_BASE_URL = "https://api.groq.com/openai/v1"
```

Run the evaluation:

```powershell
python Part-1B\.harness\run_eval.py
```

Never commit API keys or credentials to the repository.

### Evaluation Results

The latest recorded evaluation results are:

- Offline evaluation: 21/21 passed.
- Live LLM evaluation: 21/21 passed.
- Acceptance threshold: 90%.

The evaluation report is available at:

`Part-1B/evidence/eval-results.json`

[Part 1B Harness Log](Part-1B/evidence/harness-log.md)

## Harness Validation Approach

The project uses independent validation controls:

**Part 1A**
- Static code analysis using Ruff.
- Security scanning using Bandit.
- Functional and contract testing using Pytest.

**Part 1B**
- Layer 1: Structural/schema validation.
- Layer 2: Property and invariant validation.
- Layer 3: Semantic and quality evaluation.
- Aggregate evaluation against the specified acceptance threshold.

## Evidence and Documentation

Each application maintains its own evidence directory containing initial and final implementation snapshots, harness results and execution logs.

The harness logs document validation outcomes, development failures, corrective actions and final human review.

## Security Notes

- API credentials are supplied through environment variables.
- No API keys should be committed to GitHub.
- Live LLM evaluation sends reminder text to the configured provider.
- Offline evaluation can be performed without external API credentials.

## Final Note

Both applications demonstrate how specification-driven development and independent harness validation can improve the reliability of AI-assisted software development.
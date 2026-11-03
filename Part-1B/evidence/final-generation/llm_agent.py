"""OpenAI-compatible LLM adapter for reminder parsing."""

from __future__ import annotations

import http.client
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

from src.agent import ReminderAgent, ReminderOutput

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT_SECONDS = 30


class LLMReminderAgent:
    """Use a chat-completions API while keeping the local parser as an offline stub."""

    backend = "llm"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        reference: Optional[datetime] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        temperature: float = 0.7,
    ) -> None:
        if not api_key.strip():
            raise ValueError("LLM API key must not be empty")
        if not model.strip():
            raise ValueError("LLM model must not be empty")
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("LLM temperature must be between 0 and 2")
        endpoint = urlsplit(base_url)
        if (
            endpoint.scheme != "https"
            or not endpoint.hostname
            or endpoint.username
            or endpoint.password
            or endpoint.query
            or endpoint.fragment
        ):
            raise ValueError(
                "LLM base URL must be an HTTPS URL without credentials or query"
            )
        self.api_key = api_key
        self.model = model
        self.host = endpoint.hostname
        self.port = endpoint.port
        self.base_path = endpoint.path.rstrip("/")
        current = reference or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        self.reference = current.astimezone(timezone.utc)
        self.timeout = timeout
        self.temperature = temperature
        self._offline_guardrails = ReminderAgent(reference=self.reference)
        prompt_path = (
            Path(__file__).resolve().parents[1] / "prompts" / "reminder-parser.md"
        )
        self.system_prompt = prompt_path.read_text(encoding="utf-8")

    def parse_intent(self, user_input: str) -> ReminderOutput:
        text = user_input.strip()
        if not text:
            return self._offline_guardrails.parse_intent(text)
        if self._offline_guardrails.is_unsafe_request(text.casefold()):
            return self._offline_guardrails.parse_intent(text)
        if text.casefold() in {"remind me later", "set an alert"}:
            return self._offline_guardrails.parse_intent(text)

        offline_output = self._offline_guardrails.parse_intent(text)
        if self._is_unambiguous_time_only(text, offline_output):
            return offline_output

        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        self.system_prompt
                        + "\n\nReference time (UTC): "
                        + self.reference.isoformat()
                        + "\nReturn exactly one JSON object matching this schema:\n"
                        + json.dumps(ReminderOutput.model_json_schema())
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({"reminder_text": text}, ensure_ascii=False),
                },
            ],
        }
        connection = http.client.HTTPSConnection(
            self.host,
            self.port,
            timeout=self.timeout,
        )
        try:
            connection.request(
                "POST",
                "{}/chat/completions".format(self.base_path),
                body=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": "Bearer" + chr(32) + self.api_key,
                    "Content-Type": "application/json",
                },
            )
            response = connection.getresponse()
            if not 200 <= response.status < 300:
                error_body = response.read(4096).decode("utf-8", errors="replace")
                try:
                    error_data = json.loads(error_body)
                    detail = error_data.get("error", {}).get("message", "")
                except (AttributeError, json.JSONDecodeError):
                    detail = error_body
                detail = str(detail).replace(self.api_key, "[redacted]").strip()
                if len(detail) > 500:
                    detail = detail[:500] + "..."
                message = "LLM request failed with HTTP status {}".format(
                    response.status
                )
                if detail:
                    message += ": {}".format(detail)
                raise RuntimeError(message)
            try:
                response_data = json.loads(response.read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("LLM endpoint returned invalid JSON") from exc
        except (OSError, http.client.HTTPException) as exc:
            raise RuntimeError(
                "LLM request could not reach the configured HTTPS endpoint"
            ) from exc
        finally:
            connection.close()

        try:
            content = response_data["choices"][0]["message"]["content"]
            parsed = ReminderOutput.model_validate_json(content)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ValueError("LLM response did not match the reminder schema") from exc

        return self._enforce_invariants(parsed)

    @staticmethod
    def _is_unambiguous_time_only(
        text: str,
        offline_output: ReminderOutput,
    ) -> bool:
        has_time = re.search(
            r"\b(?:at|by)\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",
            text,
            flags=re.IGNORECASE,
        )
        has_date = re.search(
            r"\b(?:\d{4}-\d{2}-\d{2}|today|tomorrow|"
            r"next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
            r"this\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b",
            text,
            flags=re.IGNORECASE,
        )
        return bool(
            has_time
            and not has_date
            and offline_output.title
            and offline_output.due_date
            and not offline_output.needs_clarification
        )

    @staticmethod
    def _enforce_invariants(output: ReminderOutput) -> ReminderOutput:
        if output.needs_clarification:
            return output.model_copy(
                update={
                    "due_date": None,
                    "clarification_question": (
                        output.clarification_question
                        or "When should I remind you?"
                    ),
                }
            )
        if not output.title:
            return ReminderAgent._clarify(
                None,
                "What should I remind you about?",
            )
        if output.due_date is None and output.recurrence.value == "none":
            return ReminderAgent._clarify(
                output.title,
                "When should I remind you?",
            )
        return output


def create_agent(
    reference: Optional[datetime] = None,
) -> ReminderAgent | LLMReminderAgent:
    """Select the LLM backend only when explicitly configured."""
    api_key = os.getenv("REMINDER_LLM_API_KEY")
    if not api_key:
        return ReminderAgent(reference=reference)
    return LLMReminderAgent(
        api_key=api_key,
        model=os.getenv("REMINDER_LLM_MODEL", DEFAULT_MODEL),
        base_url=os.getenv("REMINDER_LLM_BASE_URL", DEFAULT_BASE_URL),
        reference=reference,
        temperature=float(os.getenv("REMINDER_LLM_TEMPERATURE", "0.7")),
    )

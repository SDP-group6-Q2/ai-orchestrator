"""Intent classification node.

Primary router: an LLM call to a local Ollama model, constrained to return
one of the known intents via a JSON schema. Falls back to keyword matching
if Ollama is unreachable or returns something unusable, so orchestration
keeps working without a local model running.
"""

import json
import logging

import ollama

from app.config import settings
from app.state import OrchestratorState

logger = logging.getLogger(__name__)

# Ordered so the first matching intent wins when a message could match more
# than one category (e.g. "manual" appears in "manual reset procedure").
_KEYWORDS: list[tuple[str, str]] = [
    ("troubleshooting", "error|fault|broken|stopped|jam|not working|alarm|troubleshoot|fix"),
    ("iot", "temperature|sensor|telemetry|pressure|speed|vibration|reading|status of the machine"),
    ("orders", "order|quote|invoice|contract|shipment|delivery|purchase"),
    ("service", "ticket|support request|schedule a visit|technician|complaint"),
    ("manuals", "manual|documentation|how do i|how to|instructions|datasheet|spec"),
]

_INTENT_TO_AGENT = {
    "troubleshooting": "troubleshooting_agent",
    "iot": "iot_agent",
    "orders": "orders_agent",
    "service": "service_agent",
    "manuals": "manuals_agent",
    "general": "general_agent",
}

_DEFAULT_INTENT = "general"

_INTENTS = list(_INTENT_TO_AGENT)

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {"intent": {"type": "string", "enum": _INTENTS}},
    "required": ["intent"],
}

_SYSTEM_PROMPT = (
    "You are an intent router for an industrial machine support platform. "
    f"Classify the user's message into exactly one of: {', '.join(_INTENTS)}.\n"
    "- troubleshooting: errors, faults, breakdowns, alarms, something not working\n"
    "- iot: live/historical telemetry — temperature, pressure, speed, vibration, sensor readings\n"
    "- orders: quotes, invoices, contracts, shipments, purchases\n"
    "- service: support tickets, technician visits, complaints\n"
    "- manuals: documentation, instructions, specs, how-to questions\n"
    "- general: greetings, small talk, or questions about what the platform can do\n"
    "Respond with only the JSON object matching the schema."
)


def _classify_by_keywords(message: str) -> str:
    message = message.lower()
    for intent, pattern in _KEYWORDS:
        keywords = pattern.split("|")
        if any(keyword in message for keyword in keywords):
            return intent
    return _DEFAULT_INTENT


def _classify_by_llm(message: str) -> str:
    client = ollama.Client(host=settings.ollama_base_url)
    response = client.chat(
        model=settings.ollama_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        format=_RESPONSE_SCHEMA,
        options={"temperature": 0},
    )
    content = response["message"]["content"]
    parsed = json.loads(content)
    # Some models (e.g. gpt-oss) don't reliably honor the schema's field name
    # and use a synonym like "category" instead of "intent", so match by value.
    intent = parsed.get("intent") or next(
        (value for value in parsed.values() if value in _INTENT_TO_AGENT), None
    )
    if intent not in _INTENT_TO_AGENT:
        raise ValueError(f"model returned unknown intent: {intent!r}")
    return intent


def classify_intent(state: OrchestratorState) -> OrchestratorState:
    message = state.get("message", "")

    try:
        matched_intent = _classify_by_llm(message)
    except Exception:  # noqa: BLE001 - any Ollama/parsing failure falls back to keywords
        logger.warning("LLM intent classification failed, falling back to keywords", exc_info=True)
        matched_intent = _classify_by_keywords(message)

    return {
        "intent": matched_intent,
        "selected_agent": _INTENT_TO_AGENT[matched_intent],
    }

"""Intent classification node.

First-pass router: keyword matching over the user message. Each intent maps
1:1 to an agent for now; swap the body of `classify_intent` for an LLM call
later without touching the graph wiring.
"""

from app.state import OrchestratorState

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
}

_DEFAULT_INTENT = "manuals"


def classify_intent(state: OrchestratorState) -> OrchestratorState:
    message = state.get("message", "").lower()

    matched_intent = _DEFAULT_INTENT
    for intent, pattern in _KEYWORDS:
        keywords = pattern.split("|")
        if any(keyword in message for keyword in keywords):
            matched_intent = intent
            break

    return {
        "intent": matched_intent,
        "selected_agent": _INTENT_TO_AGENT[matched_intent],
    }

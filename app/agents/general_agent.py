"""General Agent — handles greetings and basic questions about the platform itself."""

import ollama

from app.config import settings
from app.state import OrchestratorState

_SYSTEM_PROMPT = (
    "You are the assistant for the AROL Customer Platform, an industrial machine "
    "support system. Greet the user or answer general questions about what the "
    "platform can help with: manuals & documentation, live machine telemetry (IoT), "
    "orders/quotes/invoices, troubleshooting machine issues, and service tickets. "
    "Keep answers short and friendly. If the user has a specific request in one of "
    "those areas, tell them to ask it directly so it can be routed appropriately."
)


def run(state: OrchestratorState) -> OrchestratorState:
    message = state.get("message", "")

    try:
        client = ollama.Client(host=settings.ollama_base_url)
        response = client.chat(
            model=settings.ollama_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
        )
        answer = response["message"]["content"]
    except Exception:  # noqa: BLE001 - Ollama unreachable, fall back to a static reply
        answer = (
            "Hi! I can help with manuals, machine telemetry, orders, "
            "troubleshooting, and service requests — what do you need?"
        )

    return {
        "answer": answer,
        "citations": [],
    }

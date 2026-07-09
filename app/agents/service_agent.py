"""Service Agent placeholder — will handle support tickets and service requests."""

from app.state import OrchestratorState


def run(state: OrchestratorState) -> OrchestratorState:
    return {
        "answer": "[Service Agent placeholder] This will create or check the status of a support ticket.",
        "citations": [
            {"source": "service_agent:stub", "snippet": "Placeholder citation from the service ticketing system."}
        ],
    }

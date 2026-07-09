"""Troubleshooting Agent placeholder — will run guided diagnostics on real machine scenarios."""

from app.state import OrchestratorState


def run(state: OrchestratorState) -> OrchestratorState:
    return {
        "answer": "[Troubleshooting Agent placeholder] This will guide the user through diagnostics for the reported issue.",
        "citations": [
            {"source": "troubleshooting_agent:stub", "snippet": "Placeholder citation from diagnostic guides."}
        ],
    }

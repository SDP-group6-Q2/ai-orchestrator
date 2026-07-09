"""IoT Agent placeholder — will query real-time/historical machine telemetry via MCP."""

from app.state import OrchestratorState


def run(state: OrchestratorState) -> OrchestratorState:
    return {
        "answer": "[IoT Agent placeholder] This will answer using live and historical telemetry for the machine.",
        "citations": [
            {"source": "iot_agent:stub", "snippet": "Placeholder citation from the IoT telemetry platform."}
        ],
    }

"""Manuals Agent placeholder — will perform RAG over PDFs & manuals via MCP."""

from app.state import OrchestratorState


def run(state: OrchestratorState) -> OrchestratorState:
    return {
        "answer": "[Manuals Agent placeholder] This will answer using RAG over the machine's use & maintenance manuals.",
        "citations": [
            {"source": "manuals_agent:stub", "snippet": "Placeholder citation from the manuals corpus."}
        ],
    }
